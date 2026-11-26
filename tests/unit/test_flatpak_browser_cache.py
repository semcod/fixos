"""Flatpak browser caches live under ~/.var/app/<app-id>/cache and must be scanned and cleaned."""

from __future__ import annotations

from pathlib import Path

import pytest

from fixos.diagnostics.service_cleanup import ServiceCleaner
from fixos.diagnostics.service_scanner import ServiceDataScanner, ServiceType

CASES = [
    (ServiceType.FIREFOX, ".var/app/org.mozilla.firefox/cache/mozilla"),
    (ServiceType.EDGE, ".var/app/com.microsoft.Edge/cache/microsoft-edge"),
]


@pytest.mark.parametrize(("service", "rel"), CASES)
def test_flatpak_browser_cache_is_scanned(tmp_path: Path, monkeypatch, service, rel):
    monkeypatch.setenv("HOME", str(tmp_path))
    cache = tmp_path / rel
    cache.mkdir(parents=True)
    (cache / "entry.bin").write_bytes(b"x" * (2 * 1024 * 1024))

    scanner = ServiceDataScanner(threshold_mb=1)
    monkeypatch.setattr(scanner, "_get_path_size_mb", lambda path: 2.0)
    found = scanner.scan_service(service)

    paths = {info.path for info in found}
    for info in found:
        paths.update(info.details.get("paths", []))
    assert str(cache) in paths


@pytest.mark.parametrize(("service", "rel"), CASES)
def test_flatpak_browser_cache_is_in_cleanup_command(service, rel):
    command = ServiceCleaner.get_cleanup_command(service, str(Path.home() / rel))

    assert f"~/{rel}" in command


@pytest.mark.parametrize(("service", "_rel"), CASES)
def test_flatpak_browser_cache_is_safe(service, _rel):
    assert ServiceCleaner.is_safe_cleanup(service)
