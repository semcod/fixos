"""Tests for ticket-033: cleanup reports only what it actually reclaims.

Covers AC-01 (pnpm/conda prune accounting), AC-02 (Poetry cache clearing),
AC-03 (JetBrains protected mixed-data classification) and AC-04
(Docker stays reviewable when `docker system df` times out).
"""

from __future__ import annotations

from fixos.diagnostics.service_cleanup import (
    POETRY_CLEANUP_COMMAND,
    PRUNE_UNREFERENCED,
    ServiceCleaner,
)
from fixos.diagnostics.service_scanner import (
    ServiceDataInfo,
    ServiceDataScanner,
    ServiceType,
)


def _safe_service(service_type: ServiceType, name: str, size_gb: float) -> ServiceDataInfo:
    return ServiceDataInfo(
        service_type=service_type,
        name=name,
        path=f"/cache/{name.lower()}",
        size_mb=size_gb * 1024,
        size_gb=size_gb,
        description=name,
        can_cleanup=True,
        cleanup_command=f"clean-{name.lower()}",
        preview_command="",
        safe_to_cleanup=True,
        risk_level="safe",
    )


class TestPruneAccounting:
    """AC-01: pnpm/conda are tool-managed prunes, not guaranteed reclaim."""

    def test_reclaim_kind_flags_pnpm_and_conda_as_prune(self):
        assert ServiceCleaner.reclaim_kind(ServiceType.PNPM) == PRUNE_UNREFERENCED
        assert ServiceCleaner.reclaim_kind(ServiceType.CONDA) == PRUNE_UNREFERENCED

    def test_reclaim_kind_is_full_for_ordinary_safe_caches(self):
        assert ServiceCleaner.reclaim_kind(ServiceType.VSCODE) == "full"
        assert ServiceCleaner.reclaim_kind(ServiceType.NPM) == "full"

    def test_cleanup_plan_excludes_prune_services_from_safe_cleanup_gb(self, monkeypatch):
        pnpm = _safe_service(ServiceType.PNPM, "Pnpm", 1.8)
        vscode = _safe_service(ServiceType.VSCODE, "Vscode", 0.5)

        class FakeScanner:
            threshold_mb = 50

            def scan_all_services(self):
                return [pnpm, vscode]

            def scan_service(self, service_type):
                return []

        cleaner = ServiceCleaner(FakeScanner())
        monkeypatch.setattr(cleaner, "list_ollama_models", list)
        monkeypatch.setattr(cleaner, "list_running_ollama_models", lambda: set())

        plan = cleaner.get_cleanup_plan()

        # Only the full-reclaim VS Code cache counts toward the promise.
        assert plan["safe_cleanup_gb"] == 0.5
        assert plan["safe_prune_gb"] == 1.8

        pnpm_dict = next(s for s in plan["safe_to_cleanup"] if s["name"] == "Pnpm")
        assert pnpm_dict["reclaim"] == PRUNE_UNREFERENCED


class TestPoetryCleanup:
    """AC-02: Poetry cleanup clears caches/artifacts, never virtualenvs."""

    def test_scan_paths_never_include_virtualenvs(self):
        paths = ServiceDataScanner.SERVICE_PATHS[ServiceType.POETRY]
        assert all("virtualenvs" not in path for path in paths)
        assert any("pypoetry/cache" in path for path in paths)
        assert any("pypoetry/artifacts" in path for path in paths)

    def test_cleanup_command_clears_every_named_cache_and_artifacts(self):
        command = ServiceCleaner.get_cleanup_command(
            ServiceType.POETRY, "/home/user/.cache/pypoetry"
        )

        assert command == POETRY_CLEANUP_COMMAND
        assert "poetry cache list" in command
        assert "poetry cache clear --all --no-interaction" in command
        assert "~/.cache/pypoetry/cache" in command
        assert "~/.cache/pypoetry/artifacts" in command
        assert "virtualenvs" not in command


class TestJetbrainsCleanup:
    """Local History cannot be counted as rebuildable cache."""

    def test_jetbrains_system_data_is_protected(self):
        assert ServiceCleaner.get_risk_level(ServiceType.JETBRAINS) == "dangerous"
        assert ServiceCleaner.get_cleanup_command(ServiceType.JETBRAINS, "") == ""


class TestDockerTimeoutStaysReviewable:
    """AC-04: a slow `docker system df` keeps Docker in the report."""

    def test_daemon_timeout_returns_size_unknown_reviewable_entry(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=50)
        monkeypatch.setattr(scanner, "measure_service_size_mb", lambda *a, **k: 0.0)
        monkeypatch.setattr(scanner, "_get_docker_daemon_size_mb", lambda: None)
        scanner._docker_usage_timed_out = True

        service = scanner._analyze_service_path(ServiceType.DOCKER, "/var/lib/docker")

        assert service is not None
        assert service.details.get("size_unknown") is True
        assert service.details.get("reason") == "docker_system_df_timeout"
        assert service.safe_to_cleanup is False
        assert service.can_cleanup is True

    def test_timeout_flag_resets_on_successful_probe(self, monkeypatch):
        scanner = ServiceDataScanner(threshold_mb=50)
        scanner._docker_usage_timed_out = True
        monkeypatch.setattr(
            ServiceDataScanner, "_persist_docker_usage", staticmethod(lambda usage: None)
        )

        class FakeResult:
            returncode = 0
            stdout = (
                '{"Type":"Images","TotalCount":"5","Active":"2",'
                '"Size":"1GB","Reclaimable":"200MB (20%)"}\n'
            )
            stderr = ""

        monkeypatch.setattr(
            "fixos.diagnostics.service_scanner.subprocess.run",
            lambda *a, **k: FakeResult(),
        )

        usage = scanner._get_docker_daemon_usage(refresh=True)

        assert usage is not None
        assert scanner._docker_usage_timed_out is False
