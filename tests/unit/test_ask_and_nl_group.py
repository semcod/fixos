"""
Unit tests for NaturalLanguageGroup typo detection and ask_cmd heuristic matching and safety.
"""

from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner, _NamedTextIOWrapper

from fixos.agent.session_core import package_cleanup_guard
from fixos.cli.ask_cmd import (
    _execute_with_llm,
    _match_heuristic_command,
)
from fixos.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestNaturalLanguageGroupTypoDetection:
    """Test typo detection and intercept in NaturalLanguageGroup."""

    def test_cleanuo_suggests_cleanup(self, runner):
        """cleanuo is a typo for cleanup and must be caught as a typo."""
        result = runner.invoke(cli, ["cleanuo"])
        assert result.exit_code == 2
        assert "No such command 'cleanuo'" in result.output
        assert "Did you mean 'cleanup'?" in result.output

    def test_quik_suggests_quick(self, runner):
        result = runner.invoke(cli, ["quik"])
        assert result.exit_code == 2
        assert "No such command 'quik'" in result.output
        assert "'quick'" in result.output

    def test_scna_suggests_scan(self, runner):
        result = runner.invoke(cli, ["scna"])
        assert result.exit_code == 2
        assert "No such command 'scna'" in result.output
        assert "Did you mean 'scan'?" in result.output

    def test_gibberish_is_not_sent_to_ask(self, runner):
        """Single unknown word without close match should not route to ask."""
        result = runner.invoke(cli, ["xyzabc123"])
        assert result.exit_code == 2
        assert "No such command 'xyzabc123'" in result.output

    def test_multiword_nl_routes_to_ask(self, runner):
        """Natural language phrases with spaces should route to ask."""
        result = runner.invoke(cli, ["wylacz wszystkie kontenery docker", "--dry-run"])
        assert result.exit_code == 0
        assert "dry_run" in result.output

    def test_interactive_typo_confirmation(self, runner):
        """In interactive mode, confirming prompt executes the intended command."""
        with patch.object(_NamedTextIOWrapper, "isatty", return_value=True), patch(
            "click.confirm", return_value=True
        ):
            result = runner.invoke(cli, ["cleanuo", "--help"])
            assert result.exit_code == 0
            assert "cleanup" in result.output.lower() or "skanuj" in result.output.lower()


class TestAskHeuristics:
    """Test heuristic command matching in ask_cmd."""

    def test_package_cleanup_is_json_dry_run(self):
        """Package intent must expose inventory without selecting removals."""
        cmd = _match_heuristic_command("usun pakiety")

        assert cmd == ("fixos", ["cleanup", "--full", "--dry-run", "--json"])
        assert "autoremove" not in " ".join(cmd[1])

    def test_ambiguous_package_docker_request_stays_in_package_triage(self):
        cmd = _match_heuristic_command("usun pakiety docker")

        assert cmd == ("fixos", ["cleanup", "--full", "--dry-run", "--json"])

    def test_docker_stop_requires_docker_context(self):
        """zatrzymaj bluetooth must NOT stop docker containers."""
        assert _match_heuristic_command("zatrzymaj bluetooth") is None
        assert _match_heuristic_command("zatrzymaj docker") == "docker ps -aq | xargs -r docker stop"

    def test_docker_remove_requires_docker_context(self):
        """usun pliki must NOT delete docker containers."""
        assert _match_heuristic_command("usun temp") is None
        assert _match_heuristic_command("usun kontenery docker") == "docker ps -aq | xargs -r docker rm -f"

    def test_audio_module_routing(self):
        cmd = _match_heuristic_command("napraw audio")
        assert cmd == ("fixos", ["fix", "--modules", "audio"])

        cmd_scan = _match_heuristic_command("sprawdz dzwiek")
        assert cmd_scan == ("fixos", ["scan", "--modules", "audio"])

    def test_system_diagnostics_routing(self):
        assert _match_heuristic_command("diagnostyka") == ("fixos", ["scan"])
        assert _match_heuristic_command("zlap bledy") == ("fixos", ["scan"])
        assert _match_heuristic_command("naprawa") == ("fixos", ["fix"])

    @pytest.mark.parametrize("prompt", [
        "wyczysc /tmp", "wyczyść /tmp", "clean /tmp/", "posprzątaj katalog /tmp",
    ])
    def test_tmp_cleanup_dry_run_never_loads_api_config(self, runner, prompt):
        with patch("fixos.config.FixOsConfig.load") as config, patch(
            "fixos.providers.llm.LLMClient"
        ) as llm, patch("fixos.cli.ask_cmd.subprocess.run") as run:
            result = runner.invoke(cli, ["ask", prompt, "--dry-run"])

        assert result.exit_code == 0, result.output
        data = yaml.safe_load(result.output)
        assert data["status"] == "dry_run"
        assert data["command"] == "fixos cleanup --tmp --retention 24h"
        assert data["prompt"] == prompt
        config.assert_not_called()
        llm.assert_not_called()
        run.assert_not_called()

    @pytest.mark.parametrize("prompt", [
        "wyczysc /tmp2", "wyczysc /tmp/project", "nie wyczysc /tmp",
        "wyczysc /tmp i docker", "wyczysc /var/tmp",
    ])
    def test_tmp_cleanup_does_not_claim_other_targets(self, prompt):
        assert _match_heuristic_command(prompt) != (
            "fixos", ["cleanup", "--tmp", "--retention", "24h"]
        )

    @pytest.mark.parametrize("answer,removed", [("n", False), ("y", True)])
    def test_tmp_request_retains_interactive_selection_and_confirmation(
        self, runner, tmp_path, answer, removed,
    ):
        candidate = tmp_path / "stale.tmp"
        candidate.write_text("old temporary content")
        item = {"path": candidate, "description": "stale.tmp", "size_bytes": 21,
                "note": "older than 24h"}
        with patch("fixos.cli._cleanup_space._scan_tmp", return_value=[item]) as scan, patch(
            "fixos.config.FixOsConfig.load"
        ) as config, patch("fixos.providers.llm.LLMClient") as llm:
            result = runner.invoke(cli, ["ask", "wyczysc /tmp"], input=f"1\n{answer}\n")

        assert result.exit_code == 0, result.output
        scan.assert_called_once_with(days=1.0, tmp_dir=None)
        assert "Numery pozycji" in result.output
        assert "Wykonać usunięcie wybranych pozycji?" in result.output
        assert candidate.exists() is not removed
        config.assert_not_called()
        llm.assert_not_called()

    def test_api_failure_hint_preserves_request_without_docker_mapping(self, runner):
        with patch("fixos.config.FixOsConfig.load", return_value=MagicMock(api_key="test")), patch(
            "fixos.providers.llm.LLMClient"
        ) as llm:
            llm.return_value.chat.side_effect = RuntimeError("Error code: 402 Insufficient credits")
            result = runner.invoke(cli, ["ask", "sprawdz temperature"])
        data = yaml.safe_load(result.output)
        assert data["reason"] == "llm_error"
        assert data["prompt"] == "sprawdz temperature"
        assert data["hint"] == "fixos --help"
        assert "docker" not in result.output.lower()


class TestAskSafety:
    """Test safety checks for LLM-generated commands."""

    def test_dangerous_command_blocked(self):
        mock_cfg = MagicMock()
        mock_cfg.provider = "openrouter"
        mock_cfg.model = "test-model"

        with patch("fixos.providers.llm.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.chat.return_value = "rm -rf /"

            with patch("click.echo") as mock_echo:
                _execute_with_llm("wyczysc system", dry_run=False, cfg=mock_cfg)
                calls = [str(call) for call in mock_echo.call_args_list]
                combined = " ".join(calls)
                assert "blocked" in combined
                assert "dangerous_command" in combined

    def test_interactive_blocker_command_blocked(self):
        mock_cfg = MagicMock()
        mock_cfg.provider = "openrouter"
        mock_cfg.model = "test-model"

        with patch("fixos.providers.llm.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.chat.return_value = "nano /etc/hosts"

            with patch("click.echo") as mock_echo:
                _execute_with_llm("edytuj hosts", dry_run=False, cfg=mock_cfg)
                calls = [str(call) for call in mock_echo.call_args_list]
                combined = " ".join(calls)
                assert "blocked" in combined
                assert "interactive_blocker" in combined

    def test_modifying_command_prompts_and_can_be_cancelled(self):
        mock_cfg = MagicMock()
        mock_cfg.provider = "openrouter"
        mock_cfg.model = "test-model"

        with patch("fixos.providers.llm.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.chat.return_value = "sudo apt remove -y curl"

            with patch("sys.stdin.isatty", return_value=True), patch(
                "click.confirm", return_value=False
            ), patch("click.echo") as mock_echo:
                _execute_with_llm("usun curl", dry_run=False, cfg=mock_cfg)
                calls = [str(call) for call in mock_echo.call_args_list]
                combined = " ".join(calls)
                assert "cancelled" in combined

    def test_modifying_command_blocked_in_non_interactive(self):
        mock_cfg = MagicMock()
        mock_cfg.provider = "openrouter"
        mock_cfg.model = "test-model"

        with patch("fixos.providers.llm.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.chat.return_value = "sudo apt remove -y curl"

            with patch("sys.stdin.isatty", return_value=False), patch(
                "click.echo"
            ) as mock_echo:
                _execute_with_llm("usun curl", dry_run=False, cfg=mock_cfg)
                calls = [str(call) for call in mock_echo.call_args_list]
                combined = " ".join(calls)
                assert "blocked" in combined
                assert "requires_confirmation" in combined

    def test_broad_package_cleanup_is_blocked_before_confirmation(self):
        mock_cfg = MagicMock()
        mock_cfg.provider = "openrouter"
        mock_cfg.model = "test-model"

        with patch("fixos.providers.llm.LLMClient") as mock_llm_cls:
            mock_llm_cls.return_value.chat.return_value = "sudo apt autoremove -y"
            with patch("click.echo") as mock_echo, patch(
                "fixos.cli.ask_cmd.subprocess.run"
            ) as mock_run:
                _execute_with_llm("usun pakiety", dry_run=False, cfg=mock_cfg)

        combined = " ".join(str(call) for call in mock_echo.call_args_list)
        assert "blocked" in combined
        assert "package_cleanup_requires_exact_inventory" in combined
        mock_run.assert_not_called()

    def test_broad_package_cleanup_dry_run_is_preview_only(self):
        mock_cfg = MagicMock()
        mock_cfg.provider = "openrouter"
        mock_cfg.model = "test-model"

        with patch("fixos.providers.llm.LLMClient") as mock_llm_cls:
            mock_llm_cls.return_value.chat.return_value = "sudo dnf autoremove -y"
            with patch("click.echo") as mock_echo, patch(
                "fixos.cli.ask_cmd.subprocess.run"
            ) as mock_run:
                _execute_with_llm("wyczysc pakiety", dry_run=True, cfg=mock_cfg)

        combined = " ".join(str(call) for call in mock_echo.call_args_list)
        assert "dry_run" in combined
        assert "package_cleanup_requires_exact_inventory" in combined
        mock_run.assert_not_called()

    @pytest.mark.parametrize(
        "command",
        [
            "sudo dnf autoremove -y",
            "sudo dnf remove '*debuginfo*'",
            "sudo dnf remove $(package-cleanup --leaves)",
            "flatpak uninstall --unused",
        ],
    )
    def test_package_guard_rejects_unbounded_cleanup(self, command):
        assert package_cleanup_guard(command) is not None

    def test_package_guard_allows_exact_target(self):
        assert package_cleanup_guard("sudo dnf remove -y -- curl") is None


class TestInteractiveShell:
    """Test interactive shell (REPL) and quick menu."""

    def test_shell_help(self, runner):
        result = runner.invoke(cli, ["shell", "--help"])
        assert result.exit_code == 0
        assert "shell" in result.output.lower()

    def test_command_completer_has_key_commands(self):
        from fixos.cli.shell_cmd import get_command_completer

        completer = get_command_completer()
        words = list(completer.options.keys())
        assert "quick" in words
        assert "cleanup" in words
        assert "fix" in words
        assert "scan" in words
        assert "jetbrains" in words
        assert "ask" in words
        assert "config" in words

    def test_print_interactive_menu_shows_options(self):
        from fixos.cli.shell_cmd import print_interactive_menu

        with patch("click.echo") as mock_echo:
            print_interactive_menu()
            output = " ".join(str(call) for call in mock_echo.call_args_list)
            assert "FIXOS INTERACTIVE SHELL" in output
            assert "quick" in output
            assert "cleanup" in output
            assert "fix" in output

    def test_shell_loop_exit_on_q(self):
        from fixos.cli.shell_cmd import run_interactive_shell

        with patch("prompt_toolkit.PromptSession.prompt", side_effect=["q"]), patch(
            "click.echo"
        ) as mock_echo:
            run_interactive_shell(None)
            output = " ".join(str(call) for call in mock_echo.call_args_list)
            assert "Do widzenia" in output

    def test_shell_shortcut_runs_command(self):
        from fixos.cli.main import cli
        from fixos.cli.shell_cmd import run_interactive_shell

        # User chooses "33" (config show), then "q"
        with patch("prompt_toolkit.PromptSession.prompt", side_effect=["33", "q"]), patch.object(
            cli, "main"
        ) as mock_cli_main:
            run_interactive_shell(None)
            assert mock_cli_main.called
            called_args = mock_cli_main.call_args_list[0][0][0]
            assert called_args == ["config", "show"]
