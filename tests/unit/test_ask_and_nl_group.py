"""
Unit tests for NaturalLanguageGroup typo detection and ask_cmd heuristic matching and safety.
"""

from unittest.mock import MagicMock, patch
import pytest
from click.testing import CliRunner, _NamedTextIOWrapper

from fixos.cli.main import cli
from fixos.cli.ask_cmd import (
    _execute_with_llm,
    _match_heuristic_command,
)


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
            mock_llm.chat.return_value = "sudo apt autoremove"

            with patch("sys.stdin.isatty", return_value=True), patch(
                "click.confirm", return_value=False
            ), patch("click.echo") as mock_echo:
                _execute_with_llm("usun pakiety", dry_run=False, cfg=mock_cfg)
                calls = [str(call) for call in mock_echo.call_args_list]
                combined = " ".join(calls)
                assert "cancelled" in combined

    def test_modifying_command_blocked_in_non_interactive(self):
        mock_cfg = MagicMock()
        mock_cfg.provider = "openrouter"
        mock_cfg.model = "test-model"

        with patch("fixos.providers.llm.LLMClient") as mock_llm_cls:
            mock_llm = mock_llm_cls.return_value
            mock_llm.chat.return_value = "sudo apt autoremove"

            with patch("sys.stdin.isatty", return_value=False), patch(
                "click.echo"
            ) as mock_echo:
                _execute_with_llm("usun pakiety", dry_run=False, cfg=mock_cfg)
                calls = [str(call) for call in mock_echo.call_args_list]
                combined = " ".join(calls)
                assert "blocked" in combined
                assert "requires_confirmation" in combined
