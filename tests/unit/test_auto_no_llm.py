"""Unit tests for LLM-free `fixos auto`, `fix --mode autonomous`, `AutonomousSession`, and `FixOrchestrator`."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from fixos.agent.autonomous_session import AutonomousSession, run_autonomous_session
from fixos.cli import _cleanup_space as space
from fixos.cli.main import cli
from fixos.config import FixOsConfig
from fixos.orchestrator.orchestrator import FixOrchestrator


def _no_llm_config() -> FixOsConfig:
    return FixOsConfig(
        provider="gemini",
        api_key="",
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        agent_mode="autonomous",
        session_timeout=30,
        show_anonymized_data=False,
        enable_web_search=False,
    )


class TestAutonomousSessionNoLLM:
    def test_autonomous_session_executes_heuristic_findings_without_llm(self, monkeypatch):
        cfg = _no_llm_config()
        diagnostics = {
            "_run_plugins": False,
            "audio": {
                "findings": [
                    {
                        "title": "PipeWire restart",
                        "description": "PipeWire needs restart",
                        "severity": "warning",
                        "command": "echo restart_pipewire_ok",
                    },
                    {
                        "title": "Dangerous command ignored",
                        "description": "Must be blocked",
                        "severity": "critical",
                        "command": "rm -rf /",
                    },
                    {
                        "title": "Bulk package removal ignored",
                        "description": "Must be blocked by package guard",
                        "severity": "warning",
                        "command": "sudo apt autoremove -y",
                    },
                ]
            },
        }
        with patch("fixos.providers.llm.LLMClient.chat", create=True) as mock_chat:
            report = run_autonomous_session(
                diagnostics=diagnostics,
                config=cfg,
                show_data=False,
                max_fixes=5,
                auto_confirm=True,
                use_llm=False,
            )

        mock_chat.assert_not_called()
        assert len(report.fixes_applied) == 1
        assert report.fixes_applied[0].command == "echo restart_pipewire_ok"
        assert report.fixes_applied[0].success is True

    def test_autonomous_session_dry_run_records_without_executing(self):
        cfg = _no_llm_config()
        diagnostics = {
            "_run_plugins": False,
            "system": {
                "findings": [
                    {
                        "title": "Vacuum journal",
                        "severity": "warning",
                        "command": "journalctl --vacuum-size=500M",
                    }
                ]
            },
        }
        session = AutonomousSession(
            diagnostics=diagnostics,
            config=cfg,
            show_data=False,
            max_fixes=3,
            auto_confirm=True,
            use_llm=False,
            dry_run=True,
        )
        with patch.object(session, "_execute_command") as mock_exec:
            report = session.run()

        mock_exec.assert_not_called()
        assert len(report.fixes_applied) == 1
        assert report.fixes_applied[0].result == "[DRY-RUN]"


class TestFixosAutoCommand:
    def test_fixos_auto_help_is_registered(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["auto", "--help"])
        assert result.exit_code == 0
        assert "Autonomiczna diagnostyka, naprawa i zwalnianie miejsca" in result.output

    def test_fixos_auto_json_runs_without_llm_key(self, monkeypatch):
        runner = CliRunner()
        monkeypatch.setattr(
            "fixos.config.FixOsConfig.load",
            classmethod(lambda cls, **kwargs: _no_llm_config()),
        )
        monkeypatch.setattr(
            "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
            lambda: {"cpu_percent": 5.0, "memory_percent": 30.0},
        )
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_tmp", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_user_cache", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_jetbrains", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_build_caches", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_snap_old", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_journal", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_trash", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._cleanup_space._cleanup_thumbnails", lambda *a, **k: None)
        monkeypatch.setattr("fixos.cli._auto_cleanup.cleanup_additional_caches", lambda **k: None)
        monkeypatch.setattr("fixos.cli._auto_cleanup.cleanup_docker_builder", lambda **k: None)
        monkeypatch.setattr(
            "fixos.cli.fix_cmd.run_autonomous_session",
            lambda **kwargs: SimpleNamespace(fixes_applied=[1], problems_found=["p1"]),
        )

        result = runner.invoke(cli, ["auto", "--dry-run", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["status"] == "dry_run"
        assert payload["mode"] == "heuristic_no_llm"
        assert "tmp" in payload["steps_executed"]
        assert "user-cache" in payload["steps_executed"]
        assert payload["fixes_applied"] == 1

    def test_fix_autonomous_falls_back_to_no_llm_when_key_missing(self, monkeypatch):
        runner = CliRunner()
        monkeypatch.setattr(
            "fixos.config.FixOsConfig.load",
            classmethod(lambda cls, **kwargs: _no_llm_config()),
        )
        monkeypatch.setattr(
            "fixos.cli.fix_cmd._collect_diagnostics",
            lambda modules, disc, fmt, output: {"_run_plugins": False},
        )
        called = {}

        def fake_run_autonomous(**kwargs):
            called.update(kwargs)
            return SimpleNamespace(fixes_applied=[], problems_found=[])

        monkeypatch.setattr("fixos.cli.fix_cmd.run_autonomous_session", fake_run_autonomous)

        result = runner.invoke(
            cli, ["fix", "--mode", "autonomous", "--yes", "--dry-run", "--no-banner"]
        )
        assert result.exit_code == 0, result.output
        assert called.get("use_llm") is False
        assert called.get("auto_confirm") is True
        assert called.get("dry_run") is True


class TestFixOrchestratorNoLLM:
    def test_orchestrator_builds_and_runs_without_llm(self):
        cfg = _no_llm_config()
        orch = FixOrchestrator(config=cfg, dry_run=True, max_iterations=5, use_llm=False)
        diagnostics = {
            "system": {
                "findings": [
                    {
                        "id": "p_sys_1",
                        "title": "Trim journal",
                        "severity": "warning",
                        "command": "echo trim_journal",
                    }
                ]
            }
        }
        problems = orch.build_from_diagnostics(diagnostics)
        assert len(problems) == 1
        assert problems[0].name == "Trim journal"
        assert orch.graph.edges == []
        assert orch.get_execution_order() == ["p_sys_1"]

        result = orch.run_autonomous()
        assert result["executed"] == 1
        assert result["failed"] == 0
        assert "session_id" in result


class TestCleanupSpaceOptimizations:
    def test_display_and_remove_large_candidate_list_summarizes(self, tmp_path):
        candidates = []
        for idx in range(60):
            p = tmp_path / f"f_{idx}.tmp"
            p.write_text("abc")
            candidates.append(
                {
                    "description": f"f_{idx}.tmp",
                    "path": p,
                    "size_bytes": 3,
                    "note": "1.0 dni",
                }
            )

        runner = CliRunner()

        import click

        @click.command()
        def cmd():
            space._display_candidates("TEST", candidates)
            space._remove_selected(candidates, list(range(len(candidates))))

        res = runner.invoke(cmd)
        assert res.exit_code == 0
        assert "pozostałych pozycji" in res.output
        assert "Usunięto 60/60 pozycji" in res.output

    def test_discover_gitive_rootfs_dirs_does_not_descend_into_rootfs(self, tmp_path):
        ws = tmp_path / "github/proj-123/rootfs"
        nested = ws / "usr/share/rootfs"
        nested.mkdir(parents=True)
        found = space._discover_gitive_rootfs_dirs(tmp_path)
        assert found == [ws]
