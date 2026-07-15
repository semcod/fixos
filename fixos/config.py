"""
Zarządzanie konfiguracją fixos.
Ładuje .env / ~/.fixos.conf z priorytetami:
  CLI args > env vars > .env > ~/.fixos.conf > defaults
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

CONSTANT_4 = 4
CONSTANT_8 = 8
CONSTANT_12 = 12
CONSTANT_384 = 384
TIMEOUT_3600 = 3600

# Próbuj załadować python-dotenv
try:
    from dotenv import load_dotenv

    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

# Kolejność szukania .env
ENV_SEARCH_PATHS = [
    Path.cwd() / ".env",
    Path.home() / ".fixos.env",
    Path.home() / ".fixos.conf",
]

PROVIDER_DEFAULTS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash-preview-04-17",
        "key_env": "GEMINI_API_KEY",
        "key_url": "https://aistudio.google.com/app/apikey",
        "free_tier": True,
        "description": "Google Gemini – darmowy tier, bardzo dobry do diagnostyki",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
        "key_url": "https://platform.openai.com/api-keys",
        "free_tier": False,
        "description": "OpenAI GPT-4o-mini – płatny, niezawodny",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-v4-flash",
        "key_env": "OPENROUTER_API_KEY",
        "key_url": "https://openrouter.ai/settings/keys",
        "free_tier": True,
        "description": "OpenRouter – agregator 200+ modeli, darmowe modele dostępne",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "model": "grok-beta",
        "key_env": "XAI_API_KEY",
        "key_url": "https://console.x.ai/",
        "free_tier": False,
        "description": "xAI Grok – model od Elona Muska",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-haiku-20240307",
        "key_env": "ANTHROPIC_API_KEY",
        "key_url": "https://console.anthropic.com/settings/keys",
        "free_tier": False,
        "description": "Anthropic Claude – bardzo dobry do analizy logów",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "key_env": "MISTRAL_API_KEY",
        "key_url": "https://console.mistral.ai/api-keys/",
        "free_tier": True,
        "description": "Mistral AI – europejski provider, darmowy tier",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "key_env": "GROQ_API_KEY",
        "key_url": "https://console.groq.com/keys",
        "free_tier": True,
        "description": "Groq – ultra-szybkie wnioskowanie, darmowy tier",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "model": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        "key_env": "TOGETHER_API_KEY",
        "key_url": "https://api.together.ai/settings/api-keys",
        "free_tier": True,
        "description": "Together AI – open-source modele, $1 kredyt startowy",
    },
    "cohere": {
        "base_url": "https://api.cohere.com/v2",
        "model": "command-r",
        "key_env": "COHERE_API_KEY",
        "key_url": "https://dashboard.cohere.com/api-keys",
        "free_tier": True,
        "description": "Cohere Command-R – darmowy trial, dobry do RAG",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "key_env": "DEEPSEEK_API_KEY",
        "key_url": "https://platform.deepseek.com/api_keys",
        "free_tier": False,
        "description": "DeepSeek – tani chiński provider, bardzo dobry stosunek ceny",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "model": "llama3.1-8b",
        "key_env": "CEREBRAS_API_KEY",
        "key_url": "https://cloud.cerebras.ai/platform/",
        "free_tier": True,
        "description": "Cerebras – najszybsze wnioskowanie na świecie, darmowy tier",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "key_env": None,
        "key_url": "https://ollama.com/download",
        "free_tier": True,
        "description": "Ollama – lokalne modele, brak klucza API, pełna prywatność",
    },
}


def _load_env_files():
    """Ładuje pierwszy znaleziony plik .env."""
    if _HAS_DOTENV:
        for p in ENV_SEARCH_PATHS:
            if p.exists():
                load_dotenv(p, override=False)
                return str(p)
    else:
        # Ręczne parsowanie prostego KEY=VALUE
        for p in ENV_SEARCH_PATHS:
            if p.exists():
                try:
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
                    return str(p)
                except Exception:
                    pass
    return None


@dataclass
class FixOsConfig:
    # Provider
    provider: str = "gemini"
    api_key: Optional[str] = None
    model: Optional[str] = None
    model_fallbacks: List[str] = field(default_factory=list)
    base_url: Optional[str] = None

    # Agent
    agent_mode: str = "hitl"  # hitl | autonomous
    session_timeout: int = TIMEOUT_3600
    max_auto_fixes: int = 10  # limit dla trybu autonomous

    # UI
    show_anonymized_data: bool = True  # Pokaż dane użytkownikowi przed wysłaniem

    # Web search fallback
    enable_web_search: bool = True
    serpapi_key: Optional[str] = None

    # Storage
    save_reports: bool = False
    reports_dir: Path = field(default_factory=lambda: Path("/tmp/fixos-reports"))

    # Internals (ustawiane przez _load)
    env_file_loaded: Optional[str] = None

    @classmethod
    def load(
        cls,
        *,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        agent_mode: Optional[str] = None,
        session_timeout: Optional[int] = None,
        show_anonymized_data: Optional[bool] = None,
    ) -> "FixOsConfig":
        """Tworzy konfigurację z połączonych źródeł."""
        env_file = _load_env_files()
        cfg = cls(env_file_loaded=env_file)

        # Provider
        cfg.provider = (provider or os.environ.get("LLM_PROVIDER", "gemini")).lower()

        if cfg.provider not in PROVIDER_DEFAULTS:
            print(
                f"⚠️  Nieznany provider '{cfg.provider}', używam 'gemini'",
                file=sys.stderr,
            )
            cfg.provider = "gemini"

        pdef = PROVIDER_DEFAULTS[cfg.provider]

        # API Key: argument CLI > env specyficzny dla providera > OPENAI_API_KEY (fallback)
        key_env = pdef.get("key_env")
        cfg.api_key = (
            api_key
            or (os.environ.get(key_env) if key_env else None)
            or os.environ.get("API_KEY")
            or os.environ.get("OPENAI_API_KEY")  # universal fallback
        )

        # Model
        model_env_key = f"{cfg.provider.upper()}_MODEL"
        cfg.model = model or os.environ.get(model_env_key) or pdef["model"]

        # Fallback models: tried in order if the primary model gets rejected
        # by the provider (e.g. "not a valid model ID") — never for other
        # error types (auth/rate-limit/timeout), only an actually-bad model.
        fallbacks_env_key = f"{cfg.provider.upper()}_MODEL_FALLBACKS"
        cfg.model_fallbacks = [
            m.strip()
            for m in os.environ.get(fallbacks_env_key, "").split(",")
            if m.strip() and m.strip() != cfg.model
        ]

        # Base URL
        url_env_key = f"{cfg.provider.upper()}_BASE_URL"
        cfg.base_url = base_url or os.environ.get(url_env_key) or pdef["base_url"]

        # Agent mode
        cfg.agent_mode = (agent_mode or os.environ.get("AGENT_MODE", "hitl")).lower()

        # Timeout
        cfg.session_timeout = session_timeout or int(
            os.environ.get("SESSION_TIMEOUT", "3600")
        )

        # Show data
        if show_anonymized_data is not None:
            cfg.show_anonymized_data = show_anonymized_data
        else:
            val = os.environ.get("SHOW_ANONYMIZED_DATA", "true").lower()
            cfg.show_anonymized_data = val not in ("false", "0", "no")

        # Web search
        val = os.environ.get("ENABLE_WEB_SEARCH", "true").lower()
        cfg.enable_web_search = val not in ("false", "0", "no")
        cfg.serpapi_key = os.environ.get("SERPAPI_KEY")

        # Reports
        val = os.environ.get("SAVE_REPORTS", "false").lower()
        cfg.save_reports = val in ("true", "1", "yes")
        cfg.reports_dir = Path(os.environ.get("REPORTS_DIR", "/tmp/fixos-reports"))

        return cfg

    def validate(self) -> list[str]:
        """Zwraca listę błędów walidacji (pusta = OK)."""
        errors = []
        if not self.api_key and self.provider != "ollama":
            errors.append(
                f"Brak klucza API dla providera '{self.provider}'. "
                f"Ustaw {PROVIDER_DEFAULTS[self.provider].get('key_env')} w .env"
            )
        if self.agent_mode not in ("hitl", "autonomous"):
            errors.append(
                f"Nieprawidłowy AGENT_MODE='{self.agent_mode}'. Użyj: hitl | autonomous"
            )
        return errors

    def summary(self) -> str:
        """Krótkie podsumowanie konfiguracji (bez klucza API)."""
        if self.api_key:
            if len(self.api_key) > CONSTANT_12:
                key_masked = (
                    f"{self.api_key[:CONSTANT_8]}...{self.api_key[-CONSTANT_4:]}"
                )
            else:
                key_masked = "***"
        else:
            key_masked = "❌ BRAK"
        mode_icon = "🤖" if self.agent_mode == "autonomous" else "👤"
        return (
            f"  Provider  : {self.provider} ({self.model})\n"
            f"  API Key   : {key_masked}\n"
            f"  Base URL  : {self.base_url}\n"
            f"  Tryb      : {mode_icon} {self.agent_mode}\n"
            f"  Timeout   : {self.session_timeout}s\n"
            f"  Web search: {'✅' if self.enable_web_search else '❌'}\n"
            f"  .env plik : {self.env_file_loaded or 'nie znaleziono'}"
        )


KEY_PREFIXES: list[tuple[str, str]] = [
    ("AIzaSy", "gemini"),
    ("sk-ant-", "anthropic"),
    ("sk-or-", "openrouter"),
    ("sk-proj-", "openai"),
    ("sk-", "openai"),
    ("xai-", "xai"),
    ("gsk_", "groq"),
    ("r8_", "together"),
    ("hf_", "together"),
    ("sk-cohere-", "cohere"),
]


PROVIDER_MODELS: dict[str, list[str]] = {
    "gemini": [
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ],
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "openrouter": [
        "deepseek/deepseek-v4-flash",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "qwen/qwen3-235b-a22b:free",
        "meta-llama/llama-3.3-70b-instruct",
        "google/gemini-2.0-flash-001",
        "google/gemini-flash-1.5",
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
    ],
    "anthropic": [
        "claude-3-haiku-20240307",
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
    ],
    "mistral": [
        "mistral-small-latest",
        "mistral-medium-latest",
        "mistral-large-latest",
        "open-mixtral-8x22b",
    ],
    "groq": [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "llama3-70b-8192",
        "gemma2-9b-it",
        "mixtral-8x7b-32768",
    ],
    "together": [
        "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "mistralai/Mixtral-8x22B-Instruct-v0.1",
    ],
    "cohere": [
        "command-r",
        "command-r-plus",
        "command-a-03-2025",
    ],
    "deepseek": [
        "deepseek-chat",
        "deepseek-reasoner",
    ],
    "cerebras": [
        "llama3.1-8b",
        "llama-3.3-70b",
        "llama3.1-70b",
    ],
    "xai": [
        "grok-beta",
        "grok-2-1212",
        "grok-2-vision-1212",
    ],
    "ollama": [
        "llama3.2",
        "llama3.1",
        "mistral",
        "gemma2",
        "qwen2.5",
        "phi3",
        "deepseek-r1",
    ],
}


def detect_provider_from_key(key: str) -> Optional[str]:
    """Wykrywa provider na podstawie prefiksu klucza API."""
    for prefix, provider in KEY_PREFIXES:
        if key.startswith(prefix):
            return provider
    return None


def interactive_provider_setup() -> Optional["FixOsConfig"]:
    """
    Interaktywny wybór providera gdy brak konfiguracji.
    Delegates to config_interactive module.
    """
    # Lazy import to avoid circular dependency
    from .config_interactive import interactive_provider_setup as _interactive_setup

    return _interactive_setup()


def get_providers_list() -> list[dict]:
    """Zwraca listę providerów jako listę słowników."""
    result = []
    for name, d in PROVIDER_DEFAULTS.items():
        result.append(
            {
                "name": name,
                "model": d["model"],
                "key_env": d.get("key_env") or "(brak – lokalny)",
                "key_url": d.get("key_url", ""),
                "free_tier": d.get("free_tier", False),
                "description": d.get("description", ""),
            }
        )
    return result
