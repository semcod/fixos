"""Tests for ticket-033 AC-05 (LLM auth failures stop sessions, no retry)
and AC-06 (`fixos help`)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from fixos.providers.llm import LLMAuthError, LLMClient, LLMError
from fixos.utils.web_search import SearchResult


def _fake_openai_error(name: str, message: str) -> Exception:
    cls = type(name, (Exception,), {})
    cls.__module__ = "openai"
    return cls(message)


class TestLLMAuthErrorIsTyped:
    def test_authentication_error_raises_llm_auth_error(self, monkeypatch):
        monkeypatch.setattr("fixos.providers.llm._HAS_OPENAI", True)
        monkeypatch.setattr("fixos.providers.llm.openai.OpenAI", lambda **k: Mock())
        cfg = SimpleNamespace(
            provider="openrouter",
            model="openrouter/qwen/qwen3.7-plus",
            model_fallbacks=None,
            api_key="sk-test",
            base_url="https://openrouter.ai/api/v1",
        )
        client = LLMClient(cfg)
        error = _fake_openai_error("AuthenticationError", "invalid api key")

        with pytest.raises(LLMAuthError):
            client._handle_api_error(error, attempt=0)

    def test_llm_auth_error_is_an_llm_error(self):
        assert issubclass(LLMAuthError, LLMError)


class TestAutonomousSessionStopsOnAuthError:
    def _session(self, chat_side_effect):
        from fixos.agent.autonomous_session import AutonomousSession

        session = AutonomousSession.__new__(AutonomousSession)
        session.config = SimpleNamespace(enable_web_search=True, serpapi_key="x")
        session.llm = SimpleNamespace(chat=Mock(side_effect=chat_side_effect))
        session.messages = [{"role": "system", "content": "test"}]
        session.fix_count = 0
        session.max_fixes = 10
        session.search_count = 0
        session._check_timeout = Mock()
        session._get_remaining_time = Mock(return_value=100)
        return session

    def test_query_llm_marks_auth_failure_and_returns_none(self):
        session = self._session(LLMAuthError("bad key"))

        reply = session._query_llm()

        assert reply is None
        assert session.llm_auth_failed is True

    def test_process_turn_ends_session_without_web_search_retry(self):
        from fixos.agent import autonomous_session

        session = self._session(LLMAuthError("bad key"))

        with patch.object(
            autonomous_session, "search_all", Mock()
        ) as fake_search:
            result = session._process_turn()

        assert result is False
        fake_search.assert_not_called()
        assert session.llm.chat.call_count == 1

    def test_generic_llm_error_still_tries_web_search(self):
        from fixos.agent import autonomous_session

        session = self._session(LLMError("timeout"))

        with patch.object(
            autonomous_session,
            "search_all",
            Mock(
                return_value=[
                    SearchResult(title="t", url="l", snippet="s", source="web")
                ]
            ),
        ) as fake_search:
            result = session._process_turn()

        assert result is True
        fake_search.assert_called_once()
        assert getattr(session, "llm_auth_failed", False) is False


class TestHITLSessionStopsOnAuthError:
    def _session(self, chat_side_effect):
        from fixos.agent.hitl_session import HITLSession

        session = HITLSession.__new__(HITLSession)
        session.config = SimpleNamespace(
            session_timeout=300, enable_web_search=True, serpapi_key="x"
        )
        session.llm = SimpleNamespace(chat=Mock(side_effect=chat_side_effect))
        session.messages = [{"role": "system", "content": "test"}]
        session._setup_timeout = Mock()
        session.remaining = Mock(return_value=100)
        return session

    def test_auth_error_stops_session_after_a_single_attempt(self):
        from fixos.agent import hitl_session

        session = self._session(LLMAuthError("bad key"))

        with (
            patch.object(hitl_session.io, "print_thinking"),
            patch.object(hitl_session.io, "clear_thinking"),
            patch.object(hitl_session.io, "print_llm_error"),
            patch.object(hitl_session.io.console, "print") as fake_print,
        ):
            result = session._process_turn()

        assert result is False
        assert session.llm.chat.call_count == 1
        assert any(
            "popraw klucz" in str(call.args[0]) for call in fake_print.call_args_list
        )


class TestFixosHelpCommand:
    def test_help_with_no_args_shows_root_help(self):
        from fixos.cli.main import cli

        result = CliRunner().invoke(cli, ["help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "fixos" in result.output.lower()

    def test_help_with_command_shows_that_commands_help(self):
        from fixos.cli.main import cli

        result = CliRunner().invoke(cli, ["help", "cleanup"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "cleanup" in result.output

    def test_help_with_unknown_command_errors_instead_of_crashing(self):
        from fixos.cli.main import cli

        result = CliRunner().invoke(cli, ["help", "not-a-real-command"])

        assert result.exit_code != 0
        assert "Nieznana komenda" in result.output
