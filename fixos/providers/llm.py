"""
Ujednolicony klient LLM obsługujący wiele providerów przez OpenAI-compatible API.
Gemini, OpenAI, xAI, OpenRouter, Ollama – wszystkie przez ten sam interfejs.
"""

from __future__ import annotations

import json
import time
from typing import Iterator, Type

try:
    import openai

    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

from ..config import FixOsConfig


class LLMError(Exception):
    """Błąd komunikacji z LLM."""

    pass


class _ModelInvalidError(LLMError):
    """Internal: the configured model itself was rejected by the provider
    (e.g. "not a valid model ID") — advance to the next fallback model
    instead of retrying the same broken one."""


class LLMClient:
    """
    Wrapper nad openai.OpenAI kompatybilny z wieloma providerami.
    Obsługuje retry, streaming i zbieranie tokenu zużycia.

    Jeśli `config.model_fallbacks` jest ustawione, a skonfigurowany model
    zostanie odrzucony przez providera jako nieprawidłowy (błąd 400 "not a
    valid model ID"), klient automatycznie przechodzi do kolejnego modelu z
    listy zamiast tylko ponawiać próby z tym samym, zepsutym modelem.
    """

    def __init__(self, config: FixOsConfig):
        if not _HAS_OPENAI:
            raise LLMError("Zainstaluj openai: pip install openai")

        self.config = config
        self._client = openai.OpenAI(
            api_key=config.api_key or "ollama",  # ollama nie wymaga klucza
            base_url=config.base_url,
            timeout=120.0,
            max_retries=2,
        )
        self._total_tokens = 0
        self._model_candidates = [config.model] + [
            m for m in (config.model_fallbacks or []) if m != config.model
        ]
        self._active_model_index = 0

    @property
    def active_model(self) -> str:
        """Model currently in use — may differ from config.model after a
        fallback switch."""
        return self._model_candidates[self._active_model_index]

    def _advance_model(self) -> bool:
        """Move to the next fallback model. Returns False when exhausted."""
        if self._active_model_index + 1 >= len(self._model_candidates):
            return False
        old = self.active_model
        self._active_model_index += 1
        print(
            f"\n  ⚠️  Model '{old}' nieprawidłowy — próbuję '{self.active_model}'..."
        )
        return True

    @staticmethod
    def _looks_like_invalid_model(e: Exception) -> bool:
        """True when the error message says the *model itself* is the
        problem (bad ID, doesn't exist) rather than auth/quota/network."""
        msg = str(e).lower()
        return any(
            phrase in msg
            for phrase in (
                "not a valid model",
                "model not found",
                "does not exist",
                "invalid model",
                "unknown model",
            )
        )

    def _handle_api_error(self, e: Exception, attempt: int) -> bool:
        """
        Handle a known openai API error.
        Returns True if the caller should retry, False never (raises on fatal errors).
        Raises LLMError (or _ModelInvalidError) for fatal conditions.
        """
        _type = type(e).__name__
        _mod = type(e).__module__
        if not (
            _mod.startswith("openai")
            or _type
            in (
                "AuthenticationError",
                "RateLimitError",
                "NotFoundError",
                "BadRequestError",
                "APIConnectionError",
                "APITimeoutError",
            )
        ):
            raise LLMError(f"Nieoczekiwany błąd API: {e}") from e

        if _type in ("NotFoundError", "BadRequestError") and self._looks_like_invalid_model(e):
            raise _ModelInvalidError(str(e)) from e

        if _type == "AuthenticationError":
            raise LLMError(f"Błąd autoryzacji – sprawdź klucz API: {e}") from e
        if _type == "RateLimitError":
            wait = 10 * (attempt + 1)
            print(f"\n  ⚠️  Rate limit – czekam {wait}s...")
            time.sleep(wait)
            if attempt == 2:
                raise LLMError("Rate limit – przekroczono liczbę prób")
            return True
        if _type == "NotFoundError":
            raise LLMError(
                f"Model '{self.active_model}' nie istnieje dla providera "
                f"'{self.config.provider}': {e}"
            ) from e
        if _type in ("APIConnectionError", "APITimeoutError"):
            if attempt == 2:
                raise LLMError(
                    f"Błąd połączenia z {self.config.base_url}: {e}"
                    if _type == "APIConnectionError"
                    else "Timeout połączenia z API"
                )
            time.sleep(5)
            return True
        raise LLMError(f"Nieoczekiwany błąd API: {e}") from e

    def chat(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 3000,
        temperature: float = 0.3,
        stream: bool = False,
    ) -> str:
        """
        Wysyła wiadomości do LLM i zwraca odpowiedź jako string.
        Automatycznie retry przy rate limit / timeout, i przełącza się na
        kolejny model z model_fallbacks jeśli aktualny okaże się nieprawidłowy.
        """
        last_error: Exception | None = None
        while True:
            try:
                return self._chat_once(
                    messages, max_tokens=max_tokens, temperature=temperature
                )
            except _ModelInvalidError as e:
                last_error = e
                if not self._advance_model():
                    raise LLMError(
                        "Żaden ze skonfigurowanych modeli nie zadziałał "
                        f"({', '.join(self._model_candidates)}): {last_error}"
                    ) from last_error

    def _chat_once(
        self, messages: list[dict], *, max_tokens: int, temperature: float
    ) -> str:
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.active_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False,
                )
                if response.usage:
                    self._total_tokens += response.usage.total_tokens
                return response.choices[0].message.content or ""
            except Exception as e:
                self._handle_api_error(e, attempt)

        raise LLMError("Nie udało się uzyskać odpowiedzi po 3 próbach")

    def chat_stream(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 3000,
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """Generator streamujący tokeny odpowiedzi.

        Przełącza model przed rozpoczęciem streamu, jeśli obecny okaże się
        nieprawidłowy (błąd 400 pojawia się od razu przy tworzeniu streamu,
        zanim jakikolwiek token zostanie zwrócony).
        """
        while True:
            try:
                stream = self._client.chat.completions.create(
                    model=self.active_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )
                break
            except Exception as e:
                if self._looks_like_invalid_model(e) and self._advance_model():
                    continue
                raise LLMError(f"Błąd streamingu: {e}") from e

        try:
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            raise LLMError(f"Błąd streamingu: {e}") from e

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    def chat_structured(
        self,
        messages: list[dict],
        response_model: Type,
        *,
        max_retries: int = 2,
        max_tokens: int = 3000,
        temperature: float = 0.1,
    ):
        """Wywołanie LLM z wymuszonym schematem JSON (Pydantic model).

        Args:
            messages: Lista wiadomości do LLM.
            response_model: Klasa Pydantic BaseModel definiująca schemat.
            max_retries: Ile razy ponowić przy błędzie parsowania.

        Returns:
            Instancja response_model z walidowanymi danymi.
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

        for attempt in range(max_retries + 1):
            raw = self.chat(augmented, max_tokens=max_tokens, temperature=temperature)
            cleaned = self._extract_json(raw)
            try:
                return response_model.model_validate_json(cleaned)
            except Exception as e:
                if attempt < max_retries:
                    augmented.append({"role": "assistant", "content": raw})
                    augmented.append(
                        {
                            "role": "user",
                            "content": f"Invalid JSON. Error: {e}. "
                            f"Please output ONLY valid JSON.",
                        }
                    )
                else:
                    raise ValueError(
                        f"LLM failed to produce valid schema after "
                        f"{max_retries + 1} attempts: {e}"
                    )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Wyciągnij JSON z odpowiedzi LLM (obsługa markdown fences)."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        return text.strip()

    def ping(self) -> bool:
        """Sprawdza czy API odpowiada (krótki test)."""
        try:
            self.chat(
                [{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except LLMError:
            return False
