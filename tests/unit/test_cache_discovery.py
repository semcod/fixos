"""Tests for generic cache discovery."""

from __future__ import annotations

from fixos.diagnostics.cache_discovery import (
    discover_additional_caches,
    is_generic_cache_safe,
    path_is_covered,
)
from fixos.diagnostics.service_scanner import ServiceDataInfo, ServiceType


class TestCacheDiscoveryHelpers:
    def test_path_is_covered_for_nested_path(self):
        covered = {"/home/tom/.cache/pip"}
        assert path_is_covered("/home/tom/.cache/pip/wheels", covered)

    def test_is_generic_cache_safe_detects_cache_names(self):
        assert is_generic_cache_safe("/home/tom/.cache/foo-cache")
        assert not is_generic_cache_safe("/home/tom/.cache/myapp-data")


class TestDiscoverAdditionalCaches:
    def test_discovers_unknown_large_cache_dir(self, monkeypatch, tmp_path):
        cache_root = tmp_path / ".cache"
        mystery = cache_root / "mystery-cache"
        mystery.mkdir(parents=True)

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(
            "fixos.diagnostics.cache_discovery.os.path.expanduser",
            lambda path: path.replace("~", str(tmp_path)),
        )

        def fake_size(path: str) -> float:
            if str(mystery) in path:
                return 2048.0
            return 0.0

        results = discover_additional_caches(fake_size, threshold_mb=500, covered_paths=set())

        assert len(results) == 1
        assert results[0].service_type == ServiceType.GENERIC_CACHE
        assert results[0].name == "Cache: mystery-cache"
        assert results[0].safe_to_cleanup is True

    def test_skips_known_cache_names(self, monkeypatch, tmp_path):
        cache_root = tmp_path / ".cache"
        (cache_root / "pip").mkdir(parents=True)

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(
            "fixos.diagnostics.cache_discovery.os.path.expanduser",
            lambda path: path.replace("~", str(tmp_path)),
        )

        results = discover_additional_caches(lambda _path: 5000.0, 500, set())
        assert results == []

    def test_discovers_electron_cache_for_unknown_app(self, monkeypatch, tmp_path):
        config_root = tmp_path / ".config" / "Notion"
        cache_dir = config_root / "Default" / "Cache"
        cache_dir.mkdir(parents=True)

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(
            "fixos.diagnostics.cache_discovery.os.path.expanduser",
            lambda path: path.replace("~", str(tmp_path)),
        )

        results = discover_additional_caches(
            lambda path: 600.0 if "Cache" in path else 0.0,
            threshold_mb=500,
            covered_paths=set(),
        )

        assert len(results) == 1
        assert results[0].service_type == ServiceType.ELECTRON
        assert results[0].name == "Notion cache"
        assert results[0].safe_to_cleanup is True

    def test_does_not_duplicate_covered_paths(self, monkeypatch, tmp_path):
        cache_root = tmp_path / ".cache"
        mystery = cache_root / "mystery-cache"
        mystery.mkdir(parents=True)

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(
            "fixos.diagnostics.cache_discovery.os.path.expanduser",
            lambda path: path.replace("~", str(tmp_path)),
        )

        covered = {str(mystery)}
        results = discover_additional_caches(lambda _path: 2048.0, 500, covered)
        assert results == []


class TestNewServiceTypes:
    def test_dev_ai_service_paths_exist(self):
        from fixos.diagnostics.service_scanner import ServiceDataScanner

        paths = ServiceDataScanner.SERVICE_PATHS
        assert ServiceType.NVIDIA in paths
        assert ServiceType.UV in paths
        assert ServiceType.STEAM in paths
        assert ServiceType.MINIKUBE in paths

    def test_steam_cleanup_command_for_shader_cache(self):
        from fixos.diagnostics.service_cleanup import ServiceCleaner

        command = ServiceCleaner.get_cleanup_command(
            ServiceType.STEAM,
            "/home/tom/.local/share/Steam/steamapps/shadercache",
        )
        assert "shadercache" in command
        assert "steamapps/common" not in command
