"""Testy jednostkowe dla LLMClient — przełączanie na model_fallbacks przy
błędzie "nieprawidłowy model" (np. 400 "not a valid model ID")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from unittest import mock

import pytest

from fixos.providers.llm import LLMClient, LLMError


def _fake_openai_error(name: str, message: str) -> Exception:
    """A fake exception impersonating an openai.* SDK error class, without
    needing to construct the real (httpx-response-requiring) SDK classes."""
    cls = type(name, (Exception,), {})
    cls.__module__ = "openai"
    return cls(message)


@dataclass
class _FakeConfig:
    provider: str = "openrouter"
    model: str = "openrouter/qwen/qwen3.7-plus"
    model_fallbacks: Optional[List[str]] = None
    api_key: str = "sk-test"
    base_url: str = "https://openrouter.ai/api/v1"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("fixos.providers.llm._HAS_OPENAI", True)
    fake_openai_client = mock.Mock()
    monkeypatch.setattr(
        "fixos.providers.llm.openai.OpenAI", lambda **kwargs: fake_openai_client
    )
    cfg = _FakeConfig(model_fallbacks=["minimax/minimax-m3", "google/gemini-2.5-flash-lite"])
    c = LLMClient(cfg)
    return c, fake_openai_client


class TestModelCandidates:
    def test_primary_plus_fallbacks_in_order(self, client):
        c, _ = client
        assert c._model_candidates == [
            "openrouter/qwen/qwen3.7-plus",
            "minimax/minimax-m3",
            "google/gemini-2.5-flash-lite",
        ]
        assert c.active_model == "openrouter/qwen/qwen3.7-plus"

    def test_duplicate_primary_in_fallbacks_is_not_repeated(self, monkeypatch):
        monkeypatch.setattr("fixos.providers.llm._HAS_OPENAI", True)
        monkeypatch.setattr("fixos.providers.llm.openai.OpenAI", lambda **k: mock.Mock())
        cfg = _FakeConfig(model="a", model_fallbacks=["a", "b"])

        c = LLMClient(cfg)

        assert c._model_candidates == ["a", "b"]


class TestChatFallsBackOnInvalidModel:
    def test_switches_to_next_model_and_succeeds(self, client):
        c, fake_client = client

        bad_response = _fake_openai_error(
            "BadRequestError",
            "Error code: 400 - {'error': {'message': "
            "'openrouter/qwen/qwen3.7-plus is not a valid model ID'}}",
        )

        good_response = mock.Mock()
        good_response.usage = None
        good_response.choices = [mock.Mock(message=mock.Mock(content="hello"))]

        def create(**kwargs):
            call = create.calls
            create.calls += 1
            if call == 0:
                raise bad_response
            return good_response

        create.calls = 0
        fake_client.chat.completions.create.side_effect = create

        result = c.chat([{"role": "user", "content": "hi"}])

        assert result == "hello"
        assert c.active_model == "minimax/minimax-m3"

    def test_raises_once_all_fallbacks_exhausted(self, client):
        c, fake_client = client

        def always_bad(**kwargs):
            raise _fake_openai_error(
                "BadRequestError", f"{kwargs['model']} is not a valid model ID"
            )

        fake_client.chat.completions.create.side_effect = always_bad

        with pytest.raises(LLMError) as exc_info:
            c.chat([{"role": "user", "content": "hi"}])

        assert "Żaden ze skonfigurowanych modeli" in str(exc_info.value)
        assert c.active_model == "google/gemini-2.5-flash-lite"

    def test_no_fallback_configured_raises_immediately(self, monkeypatch):
        monkeypatch.setattr("fixos.providers.llm._HAS_OPENAI", True)
        fake_client = mock.Mock()
        monkeypatch.setattr("fixos.providers.llm.openai.OpenAI", lambda **k: fake_client)
        cfg = _FakeConfig(model_fallbacks=[])
        c = LLMClient(cfg)

        fake_client.chat.completions.create.side_effect = lambda **k: (_ for _ in ()).throw(
            _fake_openai_error("BadRequestError", "not a valid model ID")
        )

        with pytest.raises(LLMError):
            c.chat([{"role": "user", "content": "hi"}])

    def test_auth_error_does_not_trigger_model_switch(self, client):
        c, fake_client = client
        fake_client.chat.completions.create.side_effect = lambda **k: (_ for _ in ()).throw(
            _fake_openai_error("AuthenticationError", "invalid api key")
        )

        with pytest.raises(LLMError, match="autoryzacji"):
            c.chat([{"role": "user", "content": "hi"}])

        # Must not have advanced past the primary model for an unrelated error.
        assert c.active_model == "openrouter/qwen/qwen3.7-plus"


class TestChatResponseResilience:
    def test_glm53_uses_low_reasoning_options(self, monkeypatch):
        monkeypatch.setattr("fixos.providers.llm._HAS_OPENAI", True)
        fake_client = mock.Mock()
        monkeypatch.setattr("fixos.providers.llm.openai.OpenAI", lambda **k: fake_client)
        c = LLMClient(_FakeConfig(model="z-ai/glm-5.3", model_fallbacks=[]))
        response = mock.Mock()
        response.usage = None
        response.choices = [
            mock.Mock(message=mock.Mock(content="analysis"), finish_reason="stop")
        ]
        fake_client.chat.completions.create.return_value = response

        assert c.chat([{"role": "user", "content": "hi"}], max_tokens=50_000) == (
            "analysis"
        )

        assert fake_client.chat.completions.create.call_args.kwargs == {
            "model": "z-ai/glm-5.3",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 50_000,
            "temperature": 0.3,
            "stream": False,
            "extra_body": {
                "reasoning": {
                    "effort": "low",
                    "exclude": True,
                }
            },
        }

    def test_empty_completion_switches_to_configured_fallback(self, client):
        c, fake_client = client
        empty_response = mock.Mock()
        empty_response.usage = None
        empty_response.choices = [
            mock.Mock(message=mock.Mock(content=""), finish_reason="length")
        ]
        good_response = mock.Mock()
        good_response.usage = None
        good_response.choices = [
            mock.Mock(message=mock.Mock(content="cleanup plan"), finish_reason="stop")
        ]
        fake_client.chat.completions.create.side_effect = [
            empty_response,
            good_response,
        ]

        result = c.chat([{"role": "user", "content": "cleanup"}])

        assert result == "cleanup plan"
        assert c.active_model == "minimax/minimax-m3"
        assert fake_client.chat.completions.create.call_count == 2

    def test_empty_completion_without_fallback_raises_visible_error(self, monkeypatch):
        monkeypatch.setattr("fixos.providers.llm._HAS_OPENAI", True)
        fake_client = mock.Mock()
        monkeypatch.setattr("fixos.providers.llm.openai.OpenAI", lambda **k: fake_client)
        c = LLMClient(_FakeConfig(model="z-ai/glm-5.3", model_fallbacks=[]))
        response = mock.Mock()
        response.usage = None
        response.choices = [
            mock.Mock(message=mock.Mock(content=None), finish_reason="length")
        ]
        fake_client.chat.completions.create.return_value = response

        with pytest.raises(LLMError, match="użytecznej odpowiedzi"):
            c.chat([{"role": "user", "content": "hi"}])


class TestLooksLikeInvalidModel:
    def test_matches_known_phrasings(self):
        assert LLMClient._looks_like_invalid_model(Exception("not a valid model ID"))
        assert LLMClient._looks_like_invalid_model(Exception("Model not found"))
        assert LLMClient._looks_like_invalid_model(Exception("model 'x' does not exist"))

    def test_does_not_match_unrelated_errors(self):
        assert not LLMClient._looks_like_invalid_model(Exception("rate limit exceeded"))
        assert not LLMClient._looks_like_invalid_model(Exception("connection refused"))
