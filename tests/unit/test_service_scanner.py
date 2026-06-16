"""Testy jednostkowe dla ServiceDataScanner."""

from __future__ import annotations

from fixos.diagnostics.service_scanner import (
    ServiceDataInfo,
    ServiceDataScanner,
    ServiceType,
)


class TestChromeSafetyClassification:
    def test_chrome_profile_is_marked_for_review(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)
        profile_path = "/home/tom/.config/google-chrome"

        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda path: 537.0)
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )

        info = scanner._analyze_service_path(ServiceType.CHROME, profile_path)

        assert info is not None
        assert info.safe_to_cleanup is False
        assert profile_path in info.cleanup_command

    def test_chrome_cache_path_is_marked_safe(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)
        cache_path = "/home/tom/.cache/google-chrome"

        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda path: 40.0)
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )

        info = scanner._analyze_service_path(ServiceType.CHROME, cache_path)

        assert info is not None
        assert info.safe_to_cleanup is True
        assert cache_path in info.cleanup_command


class TestServiceMerge:
    def test_scan_service_merges_multiple_paths(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)

        def fake_analyze(service_type, path):
            sizes = {
                "/home/tom/.config/Cursor/Cache": 16000.0,
                "/home/tom/.cursor/extensions": 800.0,
            }
            size_mb = sizes.get(path, 0.0)
            if size_mb <= 0:
                return None
            return ServiceDataInfo(
                service_type=service_type,
                name=service_type.value.title(),
                path=path,
                size_mb=size_mb,
                size_gb=round(size_mb / 1024, 3),
                description="Cursor editor cache",
                can_cleanup=True,
                cleanup_command="rm -rf cache",
                preview_command="du -sh",
                safe_to_cleanup=False,
            )

        monkeypatch.setattr(scanner, "_analyze_service_path", fake_analyze)
        monkeypatch.setattr(
            "fixos.diagnostics.service_scanner.glob.glob",
            lambda pattern: [pattern],
        )
        monkeypatch.setattr(
            "fixos.diagnostics.service_scanner.os.path.exists", lambda path: True
        )

        results = scanner.scan_service(ServiceType.CURSOR)

        assert len(results) == 1
        assert results[0].size_mb == 16800.0
        assert results[0].details["merged_count"] == 2
        assert len(results[0].details["paths"]) == 2


class TestServicePathTargets:
    def test_conda_paths_scan_package_cache_only(self):
        paths = ServiceDataScanner.SERVICE_PATHS[ServiceType.CONDA]
        assert paths
        assert all("pkgs" in path for path in paths)
        assert "~/miniconda3" not in paths

    def test_ollama_paths_avoid_whole_system_tree(self):
        paths = ServiceDataScanner.SERVICE_PATHS[ServiceType.OLLAMA]
        assert paths
        assert "/usr/share/ollama" not in paths
        assert "~/.ollama/models" in paths

    def test_jetbrains_paths_target_cache_directories(self):
        paths = ServiceDataScanner.SERVICE_PATHS[ServiceType.JETBRAINS]
        assert "~/.cache/JetBrains" in paths
        assert "~/.JetBrains" not in paths
