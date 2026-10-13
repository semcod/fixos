"""OLLAMA_HOST is the single source for every fixOS Ollama endpoint."""

from __future__ import annotations

import pytest

from fixos.config import DEFAULT_OLLAMA_HOST, FixOsConfig, ollama_host_url
from fixos.diagnostics.service_cleanup import ServiceCleaner


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("OLLAMA_HOST", "OLLAMA_BASE_URL", "LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, f"http://{DEFAULT_OLLAMA_HOST}"),
        ("", f"http://{DEFAULT_OLLAMA_HOST}"),
        ("gpu-box:11434", "http://gpu-box:11434"),
        ("https://ollama.lan/", "https://ollama.lan"),
    ],
)
def test_ollama_host_url(monkeypatch, value, expected):
    if value is not None:
        monkeypatch.setenv("OLLAMA_HOST", value)

    assert ollama_host_url() == expected


def test_llm_config_and_cleanup_share_ollama_host(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "gpu-box:11434")

    cfg = FixOsConfig.load(provider="ollama")

    assert cfg.base_url == "http://gpu-box:11434/v1"
    assert ServiceCleaner._ollama_base_url() == "http://gpu-box:11434"


def test_explicit_ollama_base_url_still_wins(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "gpu-box:11434")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://proxy:8080/v1")

    assert FixOsConfig.load(provider="ollama").base_url == "http://proxy:8080/v1"
