"""
Natywny klient Google Gemini API (generateContent / streamGenerateContent).

Używa endpointu ``https://generativelanguage.googleapis.com/v1beta`` z
uwierzytelnieniem nagłówkiem ``x-goog-api-key`` — bez warstwy
OpenAI-compatible i bez zależności od pakietu ``openai``. Udostępnia ten sam
interfejs co ``LLMClient`` (chat / chat_stream / chat_structured / ping /
total_tokens), więc może być używany zamiennie przez fabrykę w ``llm.py``.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from .llm import (
    LLMAuthError,
    LLMError,
    _ModelInvalidError,
    _ModelUnusableResponseError,
)


class GeminiNativeClient:
    """Klient natywnego API Gemini z retry i fallbackiem modeli.

    ``config.api_key`` trafia wyłącznie do nagłówka żądania i nigdy nie jest
    logowany ani zapisywany.
    """

    DEFAULT_API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
    _TIMEOUT_SECONDS = 120.0

    def __init__(self, config) -> None:
        self.config = config
        self._api_key = getattr(config, "api_key", None)
        if not self._api_key:
            raise LLMError(
                "Brak klucza API dla Gemini – ustaw GEMINI_API_KEY "
                "(https://aistudio.google.com/app/apikey)"
            )
        root = str(getattr(config, "base_url", None) or self.DEFAULT_API_ROOT)
        root = root.rstrip("/")
        root = root.removesuffix("/openai")
        self._api_root = root or self.DEFAULT_API_ROOT
        self._total_tokens = 0
        self._model_candidates = [config.model] + [
            m for m in (getattr(config, "model_fallbacks", None) or [])
            if m != config.model
        ]
        self._active_model_index = 0

    @property
    def active_model(self) -> str:
        return self._model_candidates[self._active_model_index]

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    def _advance_model(self, reason: str = "nieprawidłowy") -> bool:
        if self._active_model_index + 1 >= len(self._model_candidates):
            return False
        old = self.active_model
        self._active_model_index += 1
        print(f"\n  ⚠️  Model '{old}' {reason} — próbuję '{self.active_model}'...")
        return True

    # ── transport ────────────────────────────────────────────────────────

    def _endpoint(self, action: str, *, stream: bool = False) -> str:
        url = f"{self._api_root}/models/{self.active_model}:{action}"
        if stream:
            url += "?alt=sse"
        return url

    def _request(self, payload: dict[str, Any], *, stream: bool = False):
        action = "streamGenerateContent" if stream else "generateContent"
        request = urllib.request.Request(
            self._endpoint(action, stream=stream),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )
        try:
            return urllib.request.urlopen(request, timeout=self._TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            raise self._map_http_error(exc) from exc
        except urllib.error.URLError as exc:
            raise LLMError(
                f"Błąd połączenia z {self._api_root}: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise LLMError("Timeout połączenia z API Gemini") from exc

    def _map_http_error(self, exc: urllib.error.HTTPError) -> LLMError:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - diagnostyka błędu nie może rzucać
            body = ""
        message = body
        try:
            message = str(json.loads(body).get("error", {}).get("message") or body)
        except (json.JSONDecodeError, AttributeError):
            pass
        lowered = message.lower()
        if exc.code in (401, 403):
            return LLMAuthError(
                f"Błąd autoryzacji Gemini – sprawdź klucz API: {message}"
            )
        if exc.code in (400, 404) and any(
            phrase in lowered
            for phrase in (
                "not found",
                "not a valid",
                "does not exist",
                "is not supported",
                "invalid model",
                "unknown model",
            )
        ):
            return _ModelInvalidError(message)
        if exc.code == 429:
            return LLMError(f"Rate limit Gemini: {message}")
        return LLMError(f"Błąd API Gemini (HTTP {exc.code}): {message}")

    # ── mapowanie wiadomości ─────────────────────────────────────────────

    @staticmethod
    def _translate_messages(messages: list[dict]) -> dict[str, Any]:
        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role") or "user")
            content = str(message.get("content") or "")
            if role == "system":
                system_parts.append({"text": content})
                continue
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": content}],
                }
            )
        payload: dict[str, Any] = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        return payload

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            raise _ModelUnusableResponseError("provider returned no candidates")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(str(part.get("text") or "") for part in parts)
        if not text.strip():
            finish = candidates[0].get("finishReason") or "unknown"
            raise _ModelUnusableResponseError(
                f"empty candidate content (finishReason={finish})"
            )
        return text

    def _record_usage(self, payload: dict[str, Any]) -> None:
        usage = payload.get("usageMetadata") or {}
        total = usage.get("totalTokenCount")
        if isinstance(total, (int, float)):
            self._total_tokens += int(total)

    # ── API publiczne ────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 3000,
        temperature: float = 0.3,
        stream: bool = False,
    ) -> str:
        """generateContent z retry i fallbackiem na kolejny model."""
        if stream:
            return "".join(
                self.chat_stream(
                    messages, max_tokens=max_tokens, temperature=temperature
                )
            )
        last_error: Exception | None = None
        while True:
            try:
                return self._chat_once(
                    messages, max_tokens=max_tokens, temperature=temperature
                )
            except (_ModelInvalidError, _ModelUnusableResponseError) as exc:
                last_error = exc
                reason = (
                    "zwrócił pustą odpowiedź"
                    if isinstance(exc, _ModelUnusableResponseError)
                    else "nieprawidłowy"
                )
                if not self._advance_model(reason):
                    raise LLMError(
                        "Żaden ze skonfigurowanych modeli nie zwrócił "
                        "użytecznej odpowiedzi "
                        f"({', '.join(self._model_candidates)}): {last_error}"
                    ) from last_error

    def _chat_once(
        self, messages: list[dict], *, max_tokens: int, temperature: float
    ) -> str:
        payload = self._translate_messages(messages)
        payload["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        for attempt in range(3):
            try:
                response = self._request(payload)
            except LLMError as exc:
                if isinstance(exc, (_ModelInvalidError, LLMAuthError)):
                    raise
                if "rate limit" in str(exc).lower() and attempt < 2:
                    wait = 10 * (attempt + 1)
                    print(f"\n  ⚠️  Rate limit – czekam {wait}s...")
                    time.sleep(wait)
                    continue
                raise
            try:
                body = json.loads(response.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise LLMError(f"Nieprawidłowa odpowiedź Gemini: {exc}") from exc
            self._record_usage(body)
            return self._extract_text(body)
        raise LLMError("Nie udało się uzyskać odpowiedzi po 3 próbach")

    def chat_stream(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 3000,
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """Stream tokenów przez streamGenerateContent?alt=sse."""
        payload = self._translate_messages(messages)
        payload["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        while True:
            try:
                response = self._request(payload, stream=True)
                break
            except _ModelInvalidError:
                if not self._advance_model("nieprawidłowy"):
                    raise
            except LLMError:
                raise
        try:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                self._record_usage(chunk)
                for candidate in chunk.get("candidates") or []:
                    for part in (candidate.get("content") or {}).get("parts") or []:
                        text = part.get("text")
                        if text:
                            yield str(text)
        except urllib.error.URLError as exc:
            raise LLMError(f"Błąd streamingu: {exc}") from exc

    def chat_structured(
        self,
        messages: list[dict],
        response_model: type,
        *,
        max_retries: int = 2,
        max_tokens: int = 3000,
        temperature: float = 0.1,
    ):
        """Wymusza odpowiedź JSON zgodną z modelem Pydantic.

        Używa natywnego ``responseJsonSchema``; przy błędzie parsowania
        ponawia z podpowiedzią tak jak ``LLMClient.chat_structured``.
        """
        schema = response_model.model_json_schema()
        schema_prompt = (
            "\n\n---\n"
            "CRITICAL: Respond ONLY with a valid JSON object matching "
            f"this schema:\n```json\n{json.dumps(schema, indent=2)}\n```\n"
            "No markdown, no explanation, no preamble. ONLY the JSON object."
        )
        augmented = [m.copy() for m in messages]
        augmented[-1] = {
            **augmented[-1],
            "content": augmented[-1]["content"] + schema_prompt,
        }

        payload = self._translate_messages(augmented)
        payload["generationConfig"] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        }

        for attempt in range(max_retries + 1):
            response = self._request(payload)
            try:
                body = json.loads(response.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise LLMError(f"Nieprawidłowa odpowiedź Gemini: {exc}") from exc
            self._record_usage(body)
            raw = self._extract_text(body)
            cleaned = self._extract_json(raw)
            try:
                return response_model.model_validate_json(cleaned)
            except Exception as exc:  # noqa: BLE001 - ponawiamy z podpowiedzią
                if attempt >= max_retries:
                    raise ValueError(
                        f"LLM failed to produce valid schema after "
                        f"{max_retries + 1} attempts: {exc}"
                    )
                augmented.append({"role": "assistant", "content": raw})
                augmented.append(
                    {
                        "role": "user",
                        "content": f"Invalid JSON. Error: {exc}. "
                        "Please output ONLY valid JSON.",
                    }
                )
                payload = self._translate_messages(augmented)
                payload["generationConfig"] = {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema,
                }

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                lines[1:-1] if lines[-1].startswith("```") else lines[1:]
            )
        return text.strip()

    def ping(self) -> bool:
        """Krótki test łączności z natywnym API."""
        try:
            self.chat([{"role": "user", "content": "ping"}], max_tokens=5)
            return True
        except LLMError:
            return False
