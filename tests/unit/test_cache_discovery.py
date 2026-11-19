"""Tests for generic cache discovery."""

from __future__ import annotations

import pytest

from fixos.diagnostics.cache_discovery import (
    discover_additional_caches,
    is_generic_cache_safe,
    path_is_covered,
)
from fixos.diagnostics.service_scanner import ServiceType


class TestCacheDiscoveryHelpers:
    def test_path_is_covered_for_nested_path(self, tmp_path):
        pip_root = tmp_path / "cache" / "pip"
        wheels_dir = pip_root / "wheels"
        covered = {str(pip_root)}
        assert path_is_covered(str(wheels_dir), covered)

    def test_is_generic_cache_safe_detects_cache_names(self):
        assert is_generic_cache_safe("foo-cache")
        assert not is_generic_cache_safe("myapp-data")


class TestDiscoverAdditionalCaches:
    @pytest.fixture(autouse=True)
    def _isolated_user_roots(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
        monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
        monkeypatch.setattr(
            "fixos.diagnostics.cache_discovery.os.path.expanduser",
            lambda path: path.replace("~", str(tmp_path)),
        )

    def test_discovers_unknown_large_cache_dir(self, tmp_path):
        cache_root = tmp_path / ".cache"
        mystery = cache_root / "mystery-cache"
        mystery.mkdir(parents=True)

        def fake_size(path: str) -> float:
            if str(mystery) in path:
                return 2048.0
            return 0.0

        results = discover_additional_caches(fake_size, threshold_mb=500, covered_paths=set())

        assert len(results) == 1
        assert results[0].service_type == ServiceType.GENERIC_CACHE
        assert results[0].name == "Cache: mystery-cache"
        assert results[0].safe_to_cleanup is True

    def test_skips_known_cache_names(self, tmp_path):
        cache_root = tmp_path / ".cache"
        (cache_root / "pip").mkdir(parents=True)

        results = discover_additional_caches(lambda _path: 5000.0, 500, set())
        assert results == []

    def test_discovers_electron_cache_for_unknown_app(self, tmp_path):
        config_root = tmp_path / ".config" / "Notion"
        cache_dir = config_root / "Default" / "Cache"
        cache_dir.mkdir(parents=True)

        results = discover_additional_caches(
            lambda path: 600.0 if "Cache" in path else 0.0,
            threshold_mb=500,
            covered_paths=set(),
        )

        assert len(results) == 1
        assert results[0].service_type == ServiceType.ELECTRON
        assert results[0].name == "Notion cache"
        assert results[0].safe_to_cleanup is True

    def test_does_not_duplicate_covered_paths(self, tmp_path):
        cache_root = tmp_path / ".cache"
        mystery = cache_root / "mystery-cache"
        mystery.mkdir(parents=True)

        covered = {str(mystery)}
        results = discover_additional_caches(lambda _path: 2048.0, 500, covered)
        assert results == []

    def test_skips_windows_ntfs_junctions_and_legacy_aliases(self, monkeypatch, tmp_path):
        local_app = tmp_path / "AppData" / "Local"
        (local_app / "Application Data" / "pip" / "Cache").mkdir(parents=True)
        (local_app / "Temporary Internet Files").mkdir(parents=True)
        junction_target = local_app / "RealApp" / "Cache"
        junction_target.mkdir(parents=True)
        junction_alias = local_app / "JunctionApp"
        junction_alias.mkdir(parents=True)
        (junction_alias / "Cache").mkdir(parents=True)

        monkeypatch.setattr(
            "fixos.diagnostics.cache_discovery._is_link_or_junction",
            lambda p: "JunctionApp" in p,
        )

        results = discover_additional_caches(
            lambda _path: 2048.0,
            threshold_mb=500,
            covered_paths=set(),
            system_name="Windows",
        )

        names = {item.name for item in results}
        assert names == {"Cache: RealApp"}


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
            "~/.local/share/Steam/steamapps/shadercache",
        )
        assert "shadercache" in command
        assert "steamapps/common" not in command
