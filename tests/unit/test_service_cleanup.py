"""Testy jednostkowe dla ServiceCleaner."""

from __future__ import annotations

from fixos.diagnostics.service_cleanup import ServiceCleaner
from fixos.diagnostics.service_scanner import ServiceDataInfo, ServiceType


class TestChromeCleanup:
    def test_chrome_cleanup_command_targets_scanned_profile(self):
        path = "/home/tom/.config/google-chrome"

        command = ServiceCleaner.get_cleanup_command(ServiceType.CHROME, path)

        assert "~/.cache/google-chrome" in command
        assert path in command
        assert "Cache" in command
        assert "Code Cache" in command
        assert "GPUCache" in command
        assert "Service Worker" in command

    def test_chrome_cache_cleanup_does_not_run_find_on_removed_path(self):
        path = "/home/tom/.cache/google-chrome"

        command = ServiceCleaner.get_cleanup_command(ServiceType.CHROME, path)

        assert command == f"rm -rf {path}"
        assert "find" not in command

    def test_cleanup_service_reports_freed_space_for_chrome(self, monkeypatch):
        path = "/home/tom/.config/google-chrome"
        initial_size_mb = 537.0
        service = ServiceDataInfo(
            service_type=ServiceType.CHROME,
            name="Chrome",
            path=path,
            size_mb=initial_size_mb,
            size_gb=round(initial_size_mb / 1024, 3),
            description="Google Chrome cache and data",
            can_cleanup=True,
            cleanup_command=ServiceCleaner.get_cleanup_command(
                ServiceType.CHROME, path
            ),
            preview_command="",
            safe_to_cleanup=True,
        )

        class FakeScanner:
            def scan_service(self, service_type):
                assert service_type == ServiceType.CHROME
                return [service]

            def _get_path_size_mb(self, checked_path):
                assert checked_path == path
                return 0.0

        executed = {}

        def fake_run(command, shell, capture_output, text, timeout):
            executed["command"] = command

            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            return Result()

        monkeypatch.setattr(
            "fixos.diagnostics.service_cleanup.subprocess.run", fake_run
        )

        cleaner = ServiceCleaner(FakeScanner())
        result = cleaner.cleanup_service("chrome")

        assert result["success"] is True
        assert result["space_freed_gb"] >= 0.52
        assert path in executed["command"]
        assert "Code Cache" in executed["command"]


class TestRiskLevelClassification:
    """3-tier risk model used by `fixos cleanup` to decide what's ever
    auto-selected (only 'safe') vs. shown for manual review vs. flagged as
    real, non-cache application data."""

    def test_ollama_models_are_dangerous_not_review(self):
        # cleanup_command removes every installed model, not just unused
        # ones — that's real data, not a cache.
        assert ServiceCleaner.get_risk_level(ServiceType.OLLAMA) == "dangerous"
        assert ServiceCleaner.is_safe_cleanup(ServiceType.OLLAMA) is False

    def test_docker_volumes_are_dangerous(self):
        assert ServiceCleaner.get_risk_level(ServiceType.DOCKER) == "dangerous"

    def test_conda_package_cache_is_safe(self):
        # Scanned paths only ever cover .../pkgs (see test_service_scanner),
        # a plain redownloadable package cache like pip/npm.
        assert ServiceCleaner.get_risk_level(ServiceType.CONDA) == "safe"

    def test_steam_shadercache_is_safe_but_library_is_dangerous(self):
        shadercache = "/home/tom/.local/share/Steam/steamapps/shadercache"
        library_root = "/home/tom/.local/share/Steam"

        assert (
            ServiceCleaner.get_risk_level(ServiceType.STEAM, shadercache) == "safe"
        )
        assert (
            ServiceCleaner.get_risk_level(ServiceType.STEAM, library_root)
            == "dangerous"
        )

    def test_flatpak_defaults_to_review(self):
        # flatpak uninstall --unused only removes unused runtimes, so it's
        # worth a look but isn't treated as high-risk.
        assert ServiceCleaner.get_risk_level(ServiceType.FLATPAK) == "review"
