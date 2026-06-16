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
