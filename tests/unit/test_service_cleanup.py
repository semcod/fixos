"""Testy jednostkowe dla ServiceCleaner."""

from __future__ import annotations

from datetime import datetime, timezone

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

    def test_docker_cleanup_never_prunes_volumes_or_all_images(self):
        command = ServiceCleaner.get_cleanup_command(
            ServiceType.DOCKER, "/var/lib/docker"
        )

        assert "builder prune" in command
        assert "--volumes" not in command
        assert "system prune" not in command
        assert "image prune -a" not in command

    def test_docker_old_unused_command_filters_by_age_and_skips_volumes(self):
        command = ServiceCleaner.get_docker_old_unused_command(days=30)

        assert "image prune -a" in command
        assert "--filter until=720h" in command
        assert "builder prune" in command
        assert "--volumes" not in command
        assert "system prune" not in command

    def test_docker_old_unused_rejects_non_positive_days(self):
        try:
            ServiceCleaner.get_docker_old_unused_command(days=0)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_docker_old_unused_dry_run_reports_command(self, monkeypatch):
        service = ServiceDataInfo(
            service_type=ServiceType.DOCKER,
            name="Docker",
            path="/var/lib/docker",
            size_mb=100 * 1024,
            size_gb=100.0,
            description="docker",
            can_cleanup=True,
            cleanup_command="docker builder prune --force --filter until=168h",
            preview_command="docker system df",
            safe_to_cleanup=False,
            risk_level="dangerous",
            details={
                "usage": {
                    "Images": {"reclaimable_gb": 12.5},
                    "Build Cache": {"reclaimable_gb": 1.5},
                }
            },
        )

        class FakeScanner:
            def scan_service(self, service_type):
                assert service_type == ServiceType.DOCKER
                return [service]

        result = ServiceCleaner(FakeScanner()).cleanup_docker_old_unused(
            days=30, dry_run=True
        )

        assert result["success"] is True
        assert result["until_hours"] == 720
        assert "until=720h" in result["command"]
        assert result["estimated_max_gb"] == 14.0
        assert "Volumes" not in result["command"]
        assert "image prune -a" in result["output"]

    def test_docker_old_unused_executes_bounded_command(self, monkeypatch):
        executed = {}

        class FakeScanner:
            def scan_service(self, service_type):
                return []

            def _get_docker_daemon_usage(self, *, refresh=False):
                sizes = executed.setdefault(
                    "usage",
                    [
                        {
                            "rows": {
                                "Images": {"size_gb": 10.0},
                                "Build Cache": {"size_gb": 2.0},
                            }
                        },
                        {
                            "rows": {
                                "Images": {"size_gb": 3.0},
                                "Build Cache": {"size_gb": 0.5},
                            }
                        },
                    ],
                )
                return sizes.pop(0)

        def fake_run(command, shell, capture_output, text, timeout):
            executed["command"] = command
            executed["timeout"] = timeout

            class Result:
                returncode = 0
                stdout = "Deleted Images:\nuntagged: old:latest\nTotal reclaimed space: 8.5GB\n"
                stderr = ""

            return Result()

        monkeypatch.setattr(
            "fixos.diagnostics.service_cleanup.subprocess.run", fake_run
        )

        result = ServiceCleaner(FakeScanner()).cleanup_docker_old_unused(
            days=45, dry_run=False
        )

        assert result["success"] is True
        assert "until=1080h" in executed["command"]
        assert "--volumes" not in executed["command"]
        assert result["space_freed_gb"] == 8.5
        assert executed["timeout"] >= 1800

    def test_docker_unused_command_has_no_age_filter(self):
        command = ServiceCleaner.get_docker_unused_command()
        assert "image prune -a" in command
        assert "until=" not in command
        assert "--volumes" not in command

    def test_docker_cleanup_can_attach_orphan_network_cleanup(self, monkeypatch):
        class FakeScanner:
            def scan_service(self, service_type):
                return []

        cleaner = ServiceCleaner(FakeScanner())
        monkeypatch.setattr(
            cleaner,
            "cleanup_docker_networks",
            lambda days=0, dry_run=False: {
                "success": True,
                "candidates": [{"id": "a" * 64, "name": "old_default"}],
                "removed": [],
                "failed": [],
                "pool_probe": {"available": None},
            },
        )

        result = cleaner.cleanup_docker_unused(
            dry_run=True,
            include_networks=True,
        )

        assert result["success"] is True
        assert result["orphan_networks_found"] == 1
        assert result["orphan_networks_removed"] == 0
        assert result["network_cleanup"]["candidates"][0]["name"] == "old_default"

    def test_safe_actions_include_network_only_cleanup(self, monkeypatch):
        class FakeScanner:
            def scan_service(self, service_type):
                return []

        cleaner = ServiceCleaner(FakeScanner())
        monkeypatch.setattr(cleaner, "list_ollama_models", lambda: [])
        monkeypatch.setattr(cleaner, "list_running_ollama_models", lambda: set())
        monkeypatch.setattr(
            cleaner,
            "cleanup_docker_networks",
            lambda days=0, dry_run=False: {
                "success": True,
                "candidates": [
                    {
                        "id": "a" * 64,
                        "name": "old_default",
                        "subnets": ["10.64.1.0/24"],
                    }
                ],
                "removed": [],
                "failed": [],
            },
        )

        actions = cleaner.build_safe_age_actions(selected_services=["docker"])

        assert len(actions) == 1
        action = actions[0]
        assert action["cleanup_kind"] == "docker-networks"
        assert action["size_gb"] == 0
        assert action["details"]["orphan_networks"] == [
            {
                "id": "a" * 64,
                "name": "old_default",
                "subnets": ["10.64.1.0/24"],
            }
        ]

    def test_exhausted_pool_is_advisory_after_successful_network_removal(
        self, monkeypatch
    ):
        class FakeScanner:
            def scan_service(self, service_type):
                return []

        cleaner = ServiceCleaner(FakeScanner())
        monkeypatch.setattr(
            cleaner,
            "cleanup_docker_networks",
            lambda days=0, dry_run=False: {
                "success": False,
                "candidates": [{"id": "a" * 64, "name": "old_default"}],
                "removed": [{"id": "a" * 64, "name": "old_default"}],
                "failed": [],
                "pool_probe": {
                    "available": False,
                    "error": "address pools exhausted",
                },
            },
        )

        result = cleaner.cleanup_docker_old_unused(
            days=30,
            dry_run=True,
            include_networks=True,
        )

        assert result["success"] is True
        assert result["orphan_networks_removed"] == 1
        assert result["network_cleanup"]["pool_probe"]["available"] is False

    def test_parse_docker_reclaimed_gb(self):
        assert (
            ServiceCleaner._parse_docker_reclaimed_gb("Total reclaimed space: 12.34GB")
            == 12.34
        )


class TestOllamaOldUnused:
    def test_parse_ollama_timestamp_with_long_fraction(self):
        dt = ServiceCleaner._parse_ollama_modified_at(
            "2025-09-25T12:45:48.30752109+02:00"
        )
        assert dt.tzinfo is not None
        assert dt.year == 2025
        assert dt.month == 9

    def test_select_old_ollama_models_skips_running_and_recent(self):
        now = datetime(2026, 8, 7, tzinfo=timezone.utc)
        models = [
            {
                "name": "old:7b",
                "size_bytes": 4 * 1024**3,
                "modified_at": "2025-09-25T12:00:00+00:00",
            },
            {
                "name": "recent:7b",
                "size_bytes": 4 * 1024**3,
                "modified_at": "2026-07-20T12:00:00+00:00",
            },
            {
                "name": "running-old:7b",
                "size_bytes": 4 * 1024**3,
                "modified_at": "2025-01-01T12:00:00+00:00",
            },
        ]
        selected = ServiceCleaner.select_old_ollama_models(
            models,
            days=90,
            now=now,
            running={"running-old:7b"},
        )
        assert [m["name"] for m in selected] == ["old:7b"]

    def test_cleanup_ollama_old_dry_run(self, monkeypatch):
        models = [
            {
                "name": "deepseek-r1:7b",
                "size_bytes": 4683075440,
                "modified_at": "2025-09-25T12:45:48+02:00",
            }
        ]
        monkeypatch.setattr(
            ServiceCleaner, "list_ollama_models", staticmethod(lambda: models)
        )
        monkeypatch.setattr(
            ServiceCleaner, "list_running_ollama_models", staticmethod(lambda: set())
        )

        result = ServiceCleaner(object()).cleanup_ollama_old_unused(
            days=90, dry_run=True
        )

        assert result["success"] is True
        assert result["models"][0]["name"] == "deepseek-r1:7b"
        assert "ollama rm" in result["command"]
        assert result["estimated_max_gb"] > 4.0

    def test_cleanup_ollama_old_executes_rm(self, monkeypatch):
        models = [
            {
                "name": "llava:7b",
                "size_bytes": 2 * 1024**3,
                "modified_at": "2025-07-11T15:00:00+02:00",
            }
        ]
        monkeypatch.setattr(
            ServiceCleaner, "list_ollama_models", staticmethod(lambda: models)
        )
        monkeypatch.setattr(
            ServiceCleaner, "list_running_ollama_models", staticmethod(lambda: set())
        )
        executed = []

        def fake_run(cmd, capture_output, text, timeout):
            executed.append(cmd)

            class Result:
                returncode = 0
                stdout = "deleted llava:7b"
                stderr = ""

            return Result()

        monkeypatch.setattr(
            "fixos.diagnostics.service_cleanup.subprocess.run", fake_run
        )

        result = ServiceCleaner(object()).cleanup_ollama_old_unused(
            days=90, dry_run=False
        )

        assert result["success"] is True
        assert executed == [["ollama", "rm", "llava:7b"]]
        assert result["space_freed_gb"] == 2.0

    def test_ollama_bulk_cleanup_is_disabled(self):
        assert (
            ServiceCleaner.get_cleanup_command(
                ServiceType.OLLAMA, "/usr/share/ollama/.ollama/models"
            )
            == ""
        )

    def test_all_protected_data_stores_disable_bulk_cleanup(self):
        protected = {
            ServiceType.CONTAINERD: "/var/lib/containerd",
            ServiceType.PODMAN: "/var/lib/containers",
            ServiceType.OLLAMA: "/models",
            ServiceType.LMSTUDIO: "/home/user/.lmstudio/models",
            ServiceType.HUGGINGFACE: "/home/user/.cache/huggingface",
            ServiceType.JUPYTER: "/home/user/.local/share/jupyter",
            ServiceType.MINIKUBE: "/home/user/.minikube",
            ServiceType.APPIMAGE: "/home/user/.local/share/AppImage",
            ServiceType.VBOX: "/home/user/VirtualBox VMs",
            ServiceType.VMWARE: "/home/user/vmware",
            ServiceType.VSCODE: "/home/user/.vscode/extensions",
            ServiceType.CURSOR: "/home/user/.cursor/extensions",
            ServiceType.STEAM: "/home/user/.local/share/Steam",
        }

        for service_type, path in protected.items():
            assert ServiceCleaner.get_risk_level(service_type, path) == "dangerous"
            assert ServiceCleaner.get_cleanup_command(service_type, path) == ""

    def test_editor_cache_remains_cleanable_without_touching_extensions(self):
        vscode = ServiceCleaner.get_cleanup_command(
            ServiceType.VSCODE, "/home/user/.config/Code/Cache"
        )
        cursor = ServiceCleaner.get_cleanup_command(
            ServiceType.CURSOR, "/home/user/.config/Cursor/Cache"
        )

        assert "Code/Cache" in vscode
        assert "extensions" not in vscode
        assert "Cursor/Cache" in cursor
        assert "extensions" not in cursor

    def test_docker_is_only_protected_service_with_bounded_bulk_cleanup(self):
        command = ServiceCleaner.get_cleanup_command(
            ServiceType.DOCKER, "/var/lib/docker"
        )

        assert command == "docker builder prune --force --filter until=168h"

    def test_ollama_dry_run_returns_preview_instead_of_cleanup_error(self):
        service = ServiceDataInfo(
            service_type=ServiceType.OLLAMA,
            name="Ollama",
            path="/models",
            size_mb=10 * 1024,
            size_gb=10.0,
            description="models",
            can_cleanup=False,
            cleanup_command="",
            preview_command="ollama list",
            safe_to_cleanup=False,
            risk_level="dangerous",
        )

        class FakeScanner:
            def scan_service(self, service_type):
                return [service]

        result = ServiceCleaner(FakeScanner()).cleanup_service(
            "ollama",
            dry_run=True,
        )

        assert result["success"] is True
        assert result["requires_item_selection"] is True
        assert "ollama list" in result["output"]

    def test_uv_cleanup_never_deletes_uv_data_directory(self):
        command = ServiceCleaner.get_cleanup_command(
            ServiceType.UV,
            "/home/user/.cache/uv",
        )

        assert command == "uv cache clean"
        assert ".local/share/uv" not in command

    def test_conda_package_cache_is_safe(self):
        # Scanned paths only ever cover .../pkgs (see test_service_scanner),
        # a plain redownloadable package cache like pip/npm.
        assert ServiceCleaner.get_risk_level(ServiceType.CONDA) == "safe"

    def test_steam_shadercache_is_safe_but_library_is_dangerous(self):
        shadercache = "/home/tom/.local/share/Steam/steamapps/shadercache"
        library_root = "/home/tom/.local/share/Steam"

        assert ServiceCleaner.get_risk_level(ServiceType.STEAM, shadercache) == "safe"
        assert (
            ServiceCleaner.get_risk_level(ServiceType.STEAM, library_root)
            == "dangerous"
        )

    def test_flatpak_defaults_to_review(self):
        # flatpak uninstall --unused only removes unused runtimes, so it's
        # worth a look but isn't treated as high-risk.
        assert ServiceCleaner.get_risk_level(ServiceType.FLATPAK) == "review"


class TestConsistentPostCleanupMeasurement:
    def test_planned_entry_executes_exact_selected_path_without_rescan(
        self, monkeypatch
    ):
        class FakeScanner:
            def scan_service(self, service_type):
                raise AssertionError("planned cleanup must not pick a different entry")

            def measure_service_size_mb(self, service_type, path, *, refresh=False):
                assert path == "/cache/safe"
                assert refresh is True
                return 0

        executed = []

        def fake_run(command, **kwargs):
            executed.append(command)

            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            return Result()

        monkeypatch.setattr(
            "fixos.diagnostics.service_cleanup.subprocess.run", fake_run
        )
        planned = {
            "service_type": "vscode",
            "name": "VS Code cache",
            "path": "/cache/safe",
            "size_gb": 1.0,
            "can_cleanup": True,
            "cleanup_command": "clean-only-safe-cache",
            "details": {},
        }

        result = ServiceCleaner(FakeScanner()).cleanup_service(
            "vscode",
            planned_service=planned,
        )

        assert result["success"] is True
        assert executed == ["clean-only-safe-cache"]

    def test_docker_uses_daemon_measurement_after_cleanup(self, monkeypatch):
        service = ServiceDataInfo(
            service_type=ServiceType.DOCKER,
            name="Docker",
            path="/var/lib/docker",
            size_mb=500 * 1024,
            size_gb=500.0,
            description="Docker mixed data",
            can_cleanup=True,
            cleanup_command="docker builder prune --force --filter until=168h",
            preview_command="docker system df -v",
            safe_to_cleanup=False,
            risk_level="dangerous",
        )

        class FakeScanner:
            def scan_service(self, service_type):
                return [service]

            def measure_service_size_mb(self, service_type, path, *, refresh=False):
                assert service_type == ServiceType.DOCKER
                assert path == "/var/lib/docker"
                assert refresh is True
                return 460 * 1024

        def fake_run(*args, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            return Result()

        monkeypatch.setattr(
            "fixos.diagnostics.service_cleanup.subprocess.run", fake_run
        )

        result = ServiceCleaner(FakeScanner()).cleanup_service("docker")

        assert result["success"] is True
        assert result["space_freed_gb"] == 40.0
        assert result["remaining_size_gb"] == 460.0

    def test_service_without_safe_bulk_command_is_refused(self):
        service = ServiceDataInfo(
            service_type=ServiceType.OLLAMA,
            name="Ollama",
            path="/models",
            size_mb=10 * 1024,
            size_gb=10.0,
            description="models",
            can_cleanup=False,
            cleanup_command="",
            preview_command="ollama list",
            safe_to_cleanup=False,
            risk_level="dangerous",
        )

        class FakeScanner:
            def scan_service(self, service_type):
                return [service]

        result = ServiceCleaner(FakeScanner()).cleanup_service("ollama")

        assert result["success"] is False
        assert "wybierz konkretne elementy" in result["error"]

    def test_stale_protected_plan_cannot_execute_old_bulk_command(self, monkeypatch):
        class FakeScanner:
            def scan_service(self, service_type):
                raise AssertionError(
                    "the exact plan should be checked without a rescan"
                )

        def fail_run(*args, **kwargs):
            raise AssertionError("protected command must never reach subprocess")

        monkeypatch.setattr(
            "fixos.diagnostics.service_cleanup.subprocess.run",
            fail_run,
        )
        stale_plan = {
            "service_type": "lmstudio",
            "name": "Lmstudio",
            "path": "/home/user/.lmstudio/models",
            "size_gb": 29.0,
            "can_cleanup": True,
            "cleanup_command": "rm -rf ~/.lmstudio/models/*",
            "preview_command": "ls ~/.lmstudio/models",
            "risk_level": "dangerous",
            "details": {},
        }

        result = ServiceCleaner(FakeScanner()).cleanup_service(
            "lmstudio",
            planned_service=stale_plan,
        )

        assert result["success"] is False
        assert "zbiorcze czyszczenie jest wyłączone" in result["error"]

    def test_docker_dry_run_estimates_build_cache_not_entire_store(self):
        service = ServiceDataInfo(
            service_type=ServiceType.DOCKER,
            name="Docker",
            path="/var/lib/docker",
            size_mb=505 * 1024,
            size_gb=505.0,
            description="Docker mixed data",
            can_cleanup=True,
            cleanup_command="docker builder prune --force --filter until=168h",
            preview_command="docker system df -v",
            safe_to_cleanup=False,
            risk_level="dangerous",
            details={
                "usage": {
                    "Build Cache": {
                        "reclaimable_gb": 64.73,
                    }
                }
            },
        )

        class FakeScanner:
            def scan_service(self, service_type):
                return [service]

        result = ServiceCleaner(FakeScanner()).cleanup_service("docker", dry_run=True)

        assert result["success"] is True
        assert result["space_freed_gb"] == 64.73
        assert result["space_freed_gb"] != service.size_gb
