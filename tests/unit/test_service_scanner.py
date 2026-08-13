"""Testy jednostkowe dla ServiceDataScanner."""

from __future__ import annotations

from pathlib import Path

from fixos.diagnostics.service_scanner import (
    ServiceDataInfo,
    ServiceDataScanner,
    ServiceType,
)
from fixos.diagnostics.service_cleanup import ServiceCleaner


def _home_path(*parts: str) -> str:
    return str(Path.home().joinpath(*parts))


class TestChromeSafetyClassification:
    def test_chrome_profile_is_marked_for_review(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)
        profile_path = _home_path(".config", "google-chrome")

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
        cache_path = _home_path(".cache", "google-chrome")

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
        cursor_cache = _home_path(".config", "Cursor", "Cache")
        cursor_extensions = _home_path(".cursor", "extensions")

        def fake_analyze(service_type, path):
            sizes = {
                cursor_cache: 16000.0,
                cursor_extensions: 800.0,
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


class TestRiskLevelClassification:
    """The 3-tier risk model: safe (rebuildable cache) / review (consider,
    e.g. reinstallable apps or unrecognized dirs) / dangerous (real
    installed application data, never auto-selected for bulk cleanup)."""

    def test_cursor_extensions_dir_is_dangerous_not_safe(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)
        path = _home_path(".cursor", "extensions")

        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda p: 1200.0)
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )

        info = scanner._analyze_service_path(ServiceType.CURSOR, path)

        assert info is not None
        assert info.risk_level == "dangerous"
        assert info.safe_to_cleanup is False
        assert "Extensions" in info.name

    def test_cursor_cache_dir_is_safe(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)
        path = _home_path(".config", "Cursor", "Cache")

        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda p: 900.0)
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )

        info = scanner._analyze_service_path(ServiceType.CURSOR, path)

        assert info is not None
        assert info.risk_level == "safe"
        assert info.safe_to_cleanup is True

    def test_vscode_extensions_dir_is_dangerous(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=1)
        path = _home_path(".vscode", "extensions")

        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda p: 2000.0)
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )

        info = scanner._analyze_service_path(ServiceType.VSCODE, path)

        assert info.risk_level == "dangerous"
        assert info.can_cleanup is False
        assert info.cleanup_command == ""

    def test_scan_service_splits_cursor_cache_and_extensions(self, monkeypatch):
        """Real (non-mocked-classification) scan: the safe cache dirs and
        the dangerous extensions dir must land in separate entries, never
        merged into a single "safe" blob."""
        scanner = ServiceDataScanner(threshold_mb=1)
        sizes = {
            _home_path(".config", "Cursor", "Cache"): 900.0,
            _home_path(".config", "Cursor", "CachedData"): 100.0,
            _home_path(".cursor", "extensions"): 1200.0,
        }

        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda p: sizes.get(p, 0.0))
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )
        monkeypatch.setattr(
            "fixos.diagnostics.service_scanner.glob.glob",
            lambda pattern: [pattern],
        )
        monkeypatch.setattr(
            "fixos.diagnostics.service_scanner.os.path.exists",
            lambda path: path in sizes,
        )

        results = scanner.scan_service(ServiceType.CURSOR)

        by_risk = {r.risk_level: r for r in results}
        assert set(by_risk) == {"safe", "dangerous"}
        assert by_risk["safe"].size_mb == 1000.0
        assert by_risk["dangerous"].size_mb == 1200.0
        assert by_risk["safe"].can_cleanup is True
        assert by_risk["dangerous"].can_cleanup is False
        assert by_risk["dangerous"].cleanup_command == ""


class TestDockerDaemonSizeFallback:
    """/var/lib/docker is normally root-only (mode 0710): `du` reports
    permission-denied and silently returns ~0, hiding potentially hundreds
    of GB of real Docker usage. `docker system df` asks the daemon instead,
    which works regardless of filesystem permissions."""

    def test_parse_human_size_to_mb(self):
        parse = ServiceDataScanner._parse_human_size_to_mb
        assert parse("158.3GB") == 158.3 * 1024
        assert parse("13.73GB") == 13.73 * 1024
        assert parse("245MB") == 245.0
        assert parse("0B") == 0.0
        assert parse("1.2TB") == 1.2 * 1024 * 1024
        assert parse("garbage") == 0.0

    def test_var_lib_docker_falls_back_to_daemon_size_when_du_reports_zero(
        self, monkeypatch
    ):
        scanner = ServiceDataScanner(threshold_mb=1)

        # Simulate `du` hitting "Permission denied" on the root-owned dir.
        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda p: 0.0)
        monkeypatch.setattr(
            scanner,
            "_get_docker_daemon_size_mb",
            lambda: 158.3 * 1024 + 13.73 * 1024 + 103.2 * 1024 + 3.732 * 1024,
        )
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )

        info = scanner._analyze_service_path(ServiceType.DOCKER, "/var/lib/docker")

        assert info is not None
        assert info.size_gb > 270
        assert info.risk_level == "dangerous"

    def test_docker_daemon_size_unused_for_other_services(self, monkeypatch):
        """The daemon-size override is scoped to Docker's own root-owned
        path — it must not leak into unrelated scans."""
        scanner = ServiceDataScanner(threshold_mb=1)
        called = {"count": 0}

        def fake_daemon_size():
            called["count"] += 1
            return 999999.0

        monkeypatch.setattr(scanner, "_get_docker_daemon_size_mb", fake_daemon_size)
        monkeypatch.setattr(scanner, "_get_path_size_mb", lambda p: 5.0)
        monkeypatch.setattr(
            scanner._details_provider, "get_details", lambda service_type, path: {}
        )

        scanner._analyze_service_path(ServiceType.NPM, _home_path(".npm"))

        assert called["count"] == 0

    def test_docker_usage_reports_reclaimable_without_losing_active_counts(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        scanner = ServiceDataScanner(threshold_mb=1)
        output = "\n".join(
            [
                '{"Type":"Images","TotalCount":"1799","Active":"136",'
                '"Size":"292.2GB","Reclaimable":"82.84GB (28%)"}',
                '{"Type":"Containers","TotalCount":"169","Active":"108",'
                '"Size":"17.39GB","Reclaimable":"764.3MB (4%)"}',
                '{"Type":"Local Volumes","TotalCount":"564","Active":"66",'
                '"Size":"125.1GB","Reclaimable":"89.81GB (71%)"}',
                '{"Type":"Build Cache","TotalCount":"536","Active":"0",'
                '"Size":"70.88GB","Reclaimable":"64.73GB"}',
            ]
        )
        calls = {"count": 0}

        def fake_run(*args, **kwargs):
            calls["count"] += 1

            class Result:
                returncode = 0
                stdout = output

            return Result()

        monkeypatch.setattr(
            "fixos.diagnostics.service_scanner.subprocess.run", fake_run
        )

        usage = scanner._get_docker_daemon_usage()
        cached = scanner._get_docker_daemon_usage()

        assert usage is cached
        assert calls["count"] == 1
        assert usage["size_gb"] > 500
        assert 237 < usage["reclaimable_gb"] < 239
        details = scanner._docker_usage_details(usage)
        assert details["usage"]["Images"]["active"] == 136
        assert details["usage"]["Local Volumes"]["reclaimable_gb"] == 89.81
        assert details["measurement_source"] == "docker-system-df"
        assert (tmp_path / "fixos" / "docker-usage.json").exists()


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

    def test_uv_paths_never_include_installed_tools_or_python_runtimes(self):
        paths = ServiceDataScanner.SERVICE_PATHS[ServiceType.UV]

        assert paths == ["~/.cache/uv"]
        assert "~/.local/share/uv" not in paths

    def test_pnpm_paths_target_store_not_installed_tools(self):
        paths = ServiceDataScanner.SERVICE_PATHS[ServiceType.PNPM]

        assert "~/.local/share/pnpm/store" in paths
        assert "~/.local/share/pnpm" not in paths

    def test_npm_paths_and_command_cover_npx_download_cache(self):
        paths = ServiceDataScanner.SERVICE_PATHS[ServiceType.NPM]
        command = ServiceCleaner.get_cleanup_command(ServiceType.NPM, paths[0])

        assert "~/.npm/_npx" in paths
        assert "~/.npm/_npx" in command
