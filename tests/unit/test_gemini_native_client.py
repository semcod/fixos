"""Testy jednostkowe dla GeminiNativeClient — natywne API Google Gemini."""

from __future__ import annotations

import io
import json
import urllib.error
from dataclasses import dataclass
from unittest import mock

import pytest

from fixos.providers.gemini_native import GeminiNativeClient
from fixos.providers.llm import LLMAuthError, LLMClient, LLMError


@dataclass
class _FakeGeminiConfig:
    provider: str = "gemini"
    model: str = "gemini-2.0-flash"
    model_fallbacks: list[str] | None = None
    api_key: str = "test-key"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_transport: str = "native"


def _http_error(code: int, message: str) -> urllib.error.HTTPError:
    body = json.dumps({"error": {"message": message}}).encode()
    return urllib.error.HTTPError(
        "https://generativelanguage.googleapis.com", code, "err", {}, io.BytesIO(body)
    )


def _response(payload: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(payload).encode())


def _ok_payload(text: str = "pong", total_tokens: int = 9) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"totalTokenCount": total_tokens},
    }


def test_chat_posts_native_generate_content_and_maps_roles(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode())
        return _response(_ok_payload("ok", total_tokens=17))

    monkeypatch.setattr(
        "fixos.providers.gemini_native.urllib.request.urlopen", fake_urlopen
    )
    client = GeminiNativeClient(_FakeGeminiConfig())

    answer = client.chat(
        [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
            {"role": "user", "content": "again"},
        ]
    )

    assert answer == "ok"
    assert client.total_tokens == 17
    assert captured["url"].endswith(
        "/v1beta/models/gemini-2.0-flash:generateContent"
    )
    assert captured["headers"]["X-goog-api-key"] == "test-key"
    assert captured["body"]["systemInstruction"] == {
        "parts": [{"text": "be brief"}]
    }
    assert captured["body"]["contents"] == [
        {"role": "user", "parts": [{"text": "ping"}]},
        {"role": "model", "parts": [{"text": "pong"}]},
        {"role": "user", "parts": [{"text": "again"}]},
    ]


def test_chat_requires_api_key():
    cfg = _FakeGeminiConfig(api_key=None)
    with pytest.raises(LLMError):
        GeminiNativeClient(cfg)


def test_chat_maps_401_to_auth_error(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise _http_error(401, "API key not valid")

    monkeypatch.setattr(
        "fixos.providers.gemini_native.urllib.request.urlopen", fake_urlopen
    )
    client = GeminiNativeClient(_FakeGeminiConfig())

    with pytest.raises(LLMAuthError):
        client.chat([{"role": "user", "content": "ping"}])


def test_chat_falls_back_when_model_rejected(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise _http_error(404, "models/gemini-old is not found")
        return _response(_ok_payload("ok"))

    monkeypatch.setattr(
        "fixos.providers.gemini_native.urllib.request.urlopen", fake_urlopen
    )
    cfg = _FakeGeminiConfig(
        model="gemini-old", model_fallbacks=["gemini-2.0-flash"]
    )
    client = GeminiNativeClient(cfg)

    assert client.chat([{"role": "user", "content": "ping"}]) == "ok"
    assert len(calls) == 2
    assert calls[1].endswith("/models/gemini-2.0-flash:generateContent")


def test_chat_stream_parses_sse_chunks(monkeypatch):
    sse = (
        'data: {"candidates": [{"content": {"parts": [{"text": "he"}]}}]}\n\n'
        'data: {"candidates": [{"content": {"parts": [{"text": "llo"}]}}],'
        ' "usageMetadata": {"totalTokenCount": 5}}\n\n'
        "data: [DONE]\n\n"
    )

    def fake_urlopen(request, timeout=None):
        assert request.full_url.endswith(":streamGenerateContent?alt=sse")
        return io.BytesIO(sse.encode())

    monkeypatch.setattr(
        "fixos.providers.gemini_native.urllib.request.urlopen", fake_urlopen
    )
    client = GeminiNativeClient(_FakeGeminiConfig())

    chunks = list(client.chat_stream([{"role": "user", "content": "hi"}]))

    assert chunks == ["he", "llo"]
    assert client.total_tokens == 5


def test_llm_client_dispatches_native_transport_for_gemini():
    cfg = _FakeGeminiConfig()
    client = LLMClient(cfg)
    assert isinstance(client._impl, GeminiNativeClient)


def test_llm_client_keeps_openai_transport_when_configured(monkeypatch):
    monkeypatch.setattr("fixos.providers.llm._HAS_OPENAI", True)
    monkeypatch.setattr(
        "fixos.providers.llm.openai.OpenAI", lambda **kwargs: mock.Mock()
    )
    cfg = _FakeGeminiConfig(gemini_transport="openai")
    client = LLMClient(cfg)
    from fixos.providers.llm import _OpenAILLMClient

    assert isinstance(client._impl, _OpenAILLMClient)


def test_llm_client_delegates_public_api(monkeypatch):
    def fake_urlopen(request, timeout=None):
        return _response(_ok_payload("pong"))

    monkeypatch.setattr(
        "fixos.providers.gemini_native.urllib.request.urlopen", fake_urlopen
    )
    client = LLMClient(_FakeGeminiConfig())

    assert client.chat([{"role": "user", "content": "ping"}]) == "pong"
    assert client.active_model == "gemini-2.0-flash"
    assert client.ping() is True


def test_chat_structured_uses_native_json_schema(monkeypatch):
    from pydantic import BaseModel

    class _Out(BaseModel):
        value: int

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode())
        return _response(_ok_payload('{"value": 7}'))

    monkeypatch.setattr(
        "fixos.providers.gemini_native.urllib.request.urlopen", fake_urlopen
    )
    client = GeminiNativeClient(_FakeGeminiConfig())

    result = client.chat_structured(
        [{"role": "user", "content": "give a number"}], _Out
    )

    assert result.value == 7
    generation = captured["body"]["generationConfig"]
    assert generation["responseMimeType"] == "application/json"
    assert "responseJsonSchema" in generation
