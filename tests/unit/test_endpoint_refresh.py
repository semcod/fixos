"""Deterministic tests for DNS-backed endpoint observation."""

from __future__ import annotations

import socket

from fixos.config import FixOsConfig
from fixos.endpoint_refresh import refresh_endpoint


def _resolver(*addresses):
    def resolve(host, port, **kwargs):
        return [
            (
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (address, port or 443),
            )
            for address in addresses
        ]

    return resolve


def test_dns_observation_detects_changed_addresses_without_rewriting_url():
    observations = {}

    first = refresh_endpoint(
        "llm:test",
        "https://api.example.test/v1",
        observations=observations,
        now=100,
        resolver=_resolver("192.0.2.10"),
    )
    second = refresh_endpoint(
        "llm:test",
        "https://api.example.test/v1",
        observations=observations,
        now=500,
        resolver=_resolver("192.0.2.11"),
    )

    assert first.source == "dns"
    assert second.source == "dns"
    assert second.changed is True
    assert second.addresses == ("192.0.2.11",)
    assert observations["llm:test"]["hostname"] == "api.example.test"


def test_fresh_cache_avoids_dns_lookup():
    observations = {}
    refresh_endpoint(
        "llm:test",
        "https://api.example.test/v1",
        observations=observations,
        now=100,
        resolver=_resolver("192.0.2.10"),
    )

    def fail_resolver(*args, **kwargs):
        raise AssertionError("fresh cache should avoid DNS")

    result = refresh_endpoint(
        "llm:test",
        "https://api.example.test/v1",
        observations=observations,
        now=200,
        resolver=fail_resolver,
    )
    assert result.source == "cache"
    assert result.addresses == ("192.0.2.10",)


def test_transient_dns_failure_returns_explicit_stale_cache():
    observations = {}
    refresh_endpoint(
        "llm:test",
        "https://api.example.test/v1",
        observations=observations,
        now=100,
        resolver=_resolver("192.0.2.10"),
    )

    def unavailable(*args, **kwargs):
        raise socket.gaierror("temporary resolver outage")

    result = refresh_endpoint(
        "llm:test",
        "https://api.example.test/v1",
        observations=observations,
        now=700,
        force=True,
        resolver=unavailable,
    )
    assert result.source == "stale-cache"
    assert result.stale is True
    assert result.addresses == ("192.0.2.10",)
    assert "temporary resolver outage" in (result.error or "")


def test_ip_literal_is_reported_without_dns_or_observation():
    observations = {}
    result = refresh_endpoint(
        "llm:test",
        "https://192.0.2.10/v1",
        observations=observations,
        resolver=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    assert result.source == "ip-literal"
    assert result.addresses == ("192.0.2.10",)
    assert observations == {}


def test_malformed_observation_is_ignored():
    observations = {"llm:test": {"addresses": ["not-an-ip"]}}
    result = refresh_endpoint(
        "llm:test",
        "https://api.example.test/v1",
        observations=observations,
        now=100,
        resolver=_resolver("192.0.2.12"),
    )
    assert result.source == "dns"
    assert result.addresses == ("192.0.2.12",)


def test_config_load_exposes_observation_and_can_be_disabled(monkeypatch):
    monkeypatch.setenv("FIXOS_ENDPOINT_REFRESH", "false")
    disabled = FixOsConfig.load(provider="openrouter")
    assert disabled.endpoint_status is None
    assert "wyłączone" in disabled.summary()

    monkeypatch.setenv("FIXOS_ENDPOINT_REFRESH", "true")
    enabled = FixOsConfig.load(provider="openrouter")
    assert enabled.endpoint_status is not None
    assert enabled.endpoint_status.hostname == "openrouter.ai"


def test_config_load_keeps_custom_url_compatibility_when_refresh_cannot_parse_it(
    monkeypatch,
):
    monkeypatch.setenv("FIXOS_ENDPOINT_REFRESH", "true")
    config = FixOsConfig.load(
        provider="openrouter", base_url="not-a-url", refresh_endpoints=True
    )
    assert config.base_url == "not-a-url"
    assert config.endpoint_status is not None
    assert config.endpoint_status.source == "error"
