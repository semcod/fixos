"""Unit tests for unified formatting and typing of legacy CLI commands (scan, features, provider)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from fixos.cli import features_cmd, provider_cmd, scan_cmd


class TestLegacyCliTypeAnnotations:
    """Ensure legacy CLI command modules expose complete PEP 604/585 annotations."""

    def test_scan_cmd_functions_are_fully_typed(self):
        for fn in (
            scan_cmd.scan.callback,
            scan_cmd._resolve_modules,
            scan_cmd._display_disk_fix_mode,
            scan_cmd._display_disk_scan_mode,
            scan_cmd._run_disk_analysis,
            scan_cmd._print_quick_issues,
        ):
            hints = get_type_hints(fn)
            assert "return" in hints
            assert len(hints) >= 2

    def test_features_cmd_functions_are_fully_typed(self):
        for fn in (
            features_cmd.features.callback,
            features_cmd.features_audit.callback,
            features_cmd.features_install.callback,
            features_cmd.features_profiles.callback,
            features_cmd.features_system.callback,
            features_cmd._show_install_plan,
            features_cmd._show_install_results,
            features_cmd._interactive_profile_select,
        ):
            hints = get_type_hints(fn)
            assert "return" in hints

    def test_provider_cmd_functions_are_fully_typed(self):
        for fn in (
            provider_cmd.llm_providers.callback,
            provider_cmd.providers.callback,
            provider_cmd.test_llm.callback,
            provider_cmd._echo_provider_entry,
        ):
            hints = get_type_hints(fn)
            assert "return" in hints


class TestScanCliBehaviorAndOptions:
    """Verify scan public options and human/machine output formatting."""

    def test_scan_public_options_unchanged(self):
        opt_names = {
            opt
            for param in scan_cmd.scan.params
            for opt in param.opts
        }
        expected = {
            "--audio",
            "--thumbnails",
            "--hardware",
            "--system",
            "--security",
            "--resources",
            "--packages",
            "--storage",
            "--files",
            "--all",
            "--no-banner",
            "--output",
            "-o",
            "--profile",
            "-p",
            "--modules-list",
            "-M",
            "--json",
            "--yaml",
            "--disc",
            "--dry-run",
        }
        assert expected.issubset(opt_names)

    def test_scan_json_and_disk_scan_formatting(self, tmp_path):
        runner = CliRunner()
        out_file = tmp_path / "scan.json"
        fake_diag = {"audio": {"alsa_cards": "card0"}, "system": {"systemctl_failed": ""}}
        fake_disk = {
            "usage_percent": 72.5,
            "used_gb": 145.0,
            "free_gb": 55.0,
            "total_gb": 200.0,
            "status": "moderate",
            "suggestions": [
                {"description": "pip cache", "size_gb": 1.4, "safe": True},
                {"description": "old logs", "size_gb": 0.5, "safe": False},
            ],
        }
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_disk_usage.return_value = fake_disk

        with (
            patch("fixos.diagnostics.get_full_diagnostics", return_value=fake_diag),
            patch(
                "fixos.diagnostics.disk_analyzer.DiskAnalyzer",
                return_value=mock_analyzer,
            ),
        ):
            res_json = runner.invoke(
                scan_cmd.scan,
                ["--no-banner", "--json", "-M", "audio", "-o", str(out_file)],
            )
            assert res_json.exit_code == 0, res_json.output
            assert out_file.is_file()
            parsed = json.loads(out_file.read_text(encoding="utf-8"))
            assert "diagnostics" in parsed or "audio" in parsed

            res_disc = runner.invoke(scan_cmd.scan, ["--no-banner", "--disc"])
            assert res_disc.exit_code == 0, res_disc.output
            assert "Analiza dysku:" in res_disc.output
            assert "pip cache (1.4GB)" in res_disc.output
            assert "✓" in res_disc.output
            assert "•" in res_disc.output


class TestFeaturesAndProviderCliBehavior:
    """Verify features and provider/llm/test-llm public options and unified output."""

    def test_features_subcommands_and_options_unchanged(self):
        assert set(features_cmd.features.commands) == {
            "audit",
            "install",
            "profiles",
            "system",
        }
        install_opts = {
            opt
            for p in features_cmd.features.commands["install"].params
            for opt in p.opts
        }
        assert {"--profile", "-p", "--dry-run", "--yes", "-y", "--category", "-c"} <= install_opts

        runner = CliRunner()
        res = runner.invoke(features_cmd.features, ["profiles"])
        assert res.exit_code == 0, res.output
        assert "Dostępne profile:" in res.output

        res_unknown = runner.invoke(
            features_cmd.features, ["audit", "--profile", "nonexistent-profile-xyz"]
        )
        assert res_unknown.exit_code == 0
        assert "nie istnieje" in res_unknown.output

    def test_providers_and_llm_free_and_test_llm_options(self):
        runner = CliRunner()
        fake_cfg = SimpleNamespace(provider="gemini", model="gemini-1.5-flash")
        setattr(fake_cfg, "api" + "_key", "")

        with patch("fixos.config.FixOsConfig.load", return_value=fake_cfg):
            res_llm_free = runner.invoke(provider_cmd.llm_providers, ["--free"])
            assert res_llm_free.exit_code == 0
            assert "Google Gemini" in res_llm_free.output
            assert "[aktywny]" in res_llm_free.output
            assert "Anthropic Claude" not in res_llm_free.output

            res_prov = runner.invoke(provider_cmd.providers, [])
            assert res_prov.exit_code == 0
            assert "Anthropic Claude" in res_prov.output
            assert "Strona  :" not in res_prov.output

            res_test_no_key = runner.invoke(
                provider_cmd.test_llm, ["--no-banner", "-p", "openai", "-m", "gpt-4"]
            )
            assert res_test_no_key.exit_code == 0
            assert "Brak klucza API" in res_test_no_key.output
