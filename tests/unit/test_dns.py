"""Unit tests for non-interactive DNS CLI and sudo -n safety in fixos dns."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

from click.testing import CliRunner

from fixos.cli import dns_cmd
from fixos.plugins.builtin import dns as dns_plugin


def test_apply_dns_repair_uses_sudo_n_in_non_interactive_mode(monkeypatch):
    seen_cmds: list[list[str]] = []

    def _fake_run_text(cmd: list[str], timeout: int = 10):
        seen_cmds.append(list(cmd))
        return True, "ok", ""

    def _fake_subprocess_run(cmd, **_kwargs):
        seen_cmds.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(dns_plugin, "_run_text_command", _fake_run_text)
    monkeypatch.setattr(dns_plugin.subprocess, "run", _fake_subprocess_run)

    plan = [
        {
            "step": "write_resolved_dropin",
            "description": "Write drop-in",
            "command": ["sudo", "mkdir", "-p", "/etc/systemd/resolved.conf.d"],
            "path": "/etc/systemd/resolved.conf.d/90-fixos.conf",
            "content": "[Resolve]\nDNS=1.1.1.1\n",
        },
        {
            "step": "restart_resolved",
            "description": "Restart systemd-resolved",
            "command": ["sudo", "systemctl", "restart", "systemd-resolved"],
        },
    ]

    results = dns_plugin.apply_dns_repair(plan, dry_run=False, non_interactive=True)
    assert len(results) == 2
    assert all(r["ok"] for r in results)
    assert seen_cmds[0][:2] == ["sudo", "-n"]
    assert seen_cmds[1][:3] == ["sudo", "-n", "tee"]
    assert seen_cmds[2][:2] == ["sudo", "-n"]


def test_dns_cli_non_tty_without_yes_does_not_prompt_or_apply(monkeypatch):
    called_apply = []

    class _FakePlugin:
        def __init__(self, **_kwargs):
            pass

        def diagnose(self):
            from fixos.plugins.base import DiagnosticResult, Severity

            return DiagnosticResult(
                plugin_name="dns",
                status=Severity.WARNING,
                findings=[],
                raw_data={"status": {}, "nm_connections": {}},
                duration_ms=1.0,
            )

    monkeypatch.setattr(dns_plugin, "Plugin", _FakePlugin)
    monkeypatch.setattr(
        dns_plugin,
        "build_repair_plan",
        lambda **_k: [{"step": "restart", "description": "Restart", "command": ["sudo", "true"]}],
    )
    monkeypatch.setattr(
        dns_plugin,
        "apply_dns_repair",
        lambda *a, **k: called_apply.append((a, k)) or [],
    )
    monkeypatch.setattr(
        dns_cmd.click,
        "confirm",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not prompt in non-TTY")),
    )
    monkeypatch.setattr(dns_cmd, "sys", SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: False)))

    res = CliRunner().invoke(dns_cmd.dns, ["--fix"])
    assert res.exit_code == 0, res.output
    assert "wymaga flagi --yes" in res.output
    assert called_apply == []
