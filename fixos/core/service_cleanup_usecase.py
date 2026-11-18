"""Application Use Cases for Service Cleanup Planning, Execution, and Read-Back (#169).

Extracts deterministic route resolution, service-cleanup planning, consent-gated
execution, and post-cleanup read-back verification out of `fixos/cli/cleanup_cmd.py`
(`cleanup_services`, formerly CC=98), keeping CLI/MCP layers strictly responsible
for argument parsing and presentation while preserving all safety guards.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

SPACE_ACTION_NAMES: tuple[str, ...] = (
    "snap-old",
    "journal",
    "user-cache",
    "jetbrains",
    "libvirt",
    "gitive",
    "docker-buildcache",
    "docker-volumes",
    "tmp",
    "trash",
    "thumbnails",
    "state-old",
    "projects-old",
)


@dataclass(frozen=True)
class CleanupCliRequest:
    """Normalized snapshot of CLI arguments passed to `cleanup_services`."""

    threshold: int = 500
    threshold_gb: float | None = None
    services: str | None = None
    json_output: bool = False
    cleanup: str | None = None
    docker_old: bool = False
    docker_all: bool = False
    docker_buildcache: bool = False
    docker_networks: bool = False
    docker_stale_services: bool = False
    orphaned_projects: bool = False
    pin_orphan_project: str | None = None
    unpin_orphan_project: str | None = None
    list_orphan_pins: bool = False
    process_hours: float = 12.0
    ollama_old: bool = False
    docker_volumes: bool = False
    match: str | None = None
    snap_old: bool = False
    journal_cleanup: bool = False
    user_cache: bool = False
    jetbrains: bool = False
    libvirt: bool = False
    gitive: bool = False
    tmp_cleanup: bool = False
    trash_cleanup: bool = False
    thumbnails_cleanup: bool = False
    state_old: bool = False
    projects_old: bool = False
    venvs_old: bool = False
    projects_path: str | None = None
    days: int | None = None
    retention: str | None = None
    hours: float | None = None
    policy_matrix: bool = False
    dry_run: bool = False
    list_only: bool = False
    yes: bool = False
    free_gb: float | None = None
    full_analysis: bool = False
    artifacts_paths: tuple[str, ...] = ()
    artifacts_min_age_days: float | None = None
    artifacts_receipt_dir: str | None = None
    artifacts_build_caches: bool = False
    artifacts_system_wide: bool = False


@dataclass(frozen=True)
class CleanupRouteDecision:
    """Resolved application route or validation error for `cleanup_services`."""

    kind: str
    action_name: str = ""
    threshold_mb: int = 500
    effective_days: float | None = None
    service_filter: list[str] | None = None
    error_kind: str | None = None  # "usage_error" | "styled_error" | None
    error_message: str = ""


@dataclass(frozen=True)
class ServiceCleanupPlan:
    """Typed service cleanup plan separating planning from consent and execution."""

    raw_plan: dict[str, Any]
    services_found: int
    total_size_gb: float
    safe_services: list[dict[str, Any]]
    requires_review: list[dict[str, Any]]
    dangerous: list[dict[str, Any]]


@dataclass(frozen=True)
class ServiceCleanupExecution:
    """Outcome of executing (or declining/simulating) a service cleanup plan."""

    outcome: str  # "succeeded" | "partial" | "failed" | "declined_consent" | "simulated" | "empty"
    dry_run: bool
    consent_granted: bool
    attempted_count: int
    succeeded_count: int
    failed_count: int
    space_freed_gb: float
    results: list[dict[str, Any]] = field(default_factory=list)
    executed_service_types: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ServiceCleanupReadback:
    """Post-execution read-back verification comparing pre- and post-cleanup service state."""

    verified: bool
    outcome: str  # "succeeded" | "partial" | "failed" | "skipped"
    before_services_count: int
    after_services_count: int
    before_total_gb: float
    after_total_gb: float
    observed_delta_gb: float
    remaining_service_types: list[str]


def _usage_err(msg: str) -> CleanupRouteDecision:
    return CleanupRouteDecision(kind="error", error_kind="usage_error", error_message=msg)


def _styled_err(msg: str) -> CleanupRouteDecision:
    return CleanupRouteDecision(kind="error", error_kind="styled_error", error_message=msg)


def _space_flag_map(req: CleanupCliRequest) -> dict[str, bool]:
    return {
        "snap-old": req.snap_old,
        "journal": req.journal_cleanup,
        "user-cache": req.user_cache,
        "jetbrains": req.jetbrains,
        "libvirt": req.libvirt,
        "gitive": req.gitive,
        "docker-buildcache": req.docker_buildcache,
        "docker-volumes": req.docker_volumes,
        "tmp": req.tmp_cleanup,
        "trash": req.trash_cleanup,
        "thumbnails": req.thumbnails_cleanup,
        "state-old": req.state_old,
        "projects-old": req.projects_old,
    }


def _parse_effective_days(req: CleanupCliRequest) -> tuple[float | None, CleanupRouteDecision | None]:
    if req.retention is not None:
        from fixos.cli._cleanup_space import parse_retention_days

        try:
            return parse_retention_days(req.retention), None
        except ValueError as exc:
            return None, _usage_err(str(exc))
    if req.hours is not None:
        return float(req.hours) / 24.0, None
    if req.days is not None:
        return float(req.days), None
    return None, None


def _has_non_venv_flags(req: CleanupCliRequest) -> bool:
    return any(
        (
            req.full_analysis,
            req.services,
            req.docker_old,
            req.docker_all,
            req.docker_buildcache,
            req.docker_networks,
            req.docker_stale_services,
            req.orphaned_projects,
            req.pin_orphan_project,
            req.unpin_orphan_project,
            req.list_orphan_pins,
            req.ollama_old,
            *(_space_flag_map(req).values()),
        )
    )


def _check_early_exclusive_modes(
    req: CleanupCliRequest,
    threshold_mb: int,
    effective_days: float | None,
) -> CleanupRouteDecision | None:
    if req.venvs_old or req.cleanup == "venvs-old":
        if _has_non_venv_flags(req) or req.cleanup not in (None, "venvs-old"):
            return _usage_err("--venvs-old uruchom jako osobną akcję")
        return CleanupRouteDecision(
            kind="venvs_old",
            threshold_mb=threshold_mb,
            effective_days=effective_days,
        )
    if req.projects_path is not None and not (req.projects_old or req.cleanup == "projects-old"):
        return _usage_err("--projects-path wymaga --venvs-old lub --projects-old")
    if req.free_gb is not None:
        has_other = (
            _has_non_venv_flags(req)
            or bool(req.cleanup)
            or req.venvs_old
            or req.policy_matrix
            or req.pin_orphan_project is not None
            or req.unpin_orphan_project is not None
        )
        if has_other:
            return _usage_err("--free-gb uruchom jako osobną akcję")
        return CleanupRouteDecision(
            kind="free_target",
            threshold_mb=threshold_mb,
            effective_days=effective_days,
        )
    pin_actions = sum(
        v is not None and v is not False
        for v in (req.pin_orphan_project, req.unpin_orphan_project, req.list_orphan_pins)
    )
    if pin_actions > 1:
        return _styled_err("Wybierz tylko jedną operację: pin, unpin albo listę przypięć.")
    if pin_actions:
        pin_conflicts = any(
            (
                req.full_analysis,
                bool(req.services),
                bool(req.cleanup),
                req.docker_old,
                req.docker_all,
                req.docker_networks,
                req.docker_stale_services,
                req.orphaned_projects,
                req.ollama_old,
                *(_space_flag_map(req).values()),
                req.days is not None,
                req.retention is not None,
                req.hours is not None,
                req.dry_run,
            )
        )
        if pin_conflicts:
            return _styled_err("Zarządzanie przypięciami uruchom jako osobną akcję bez --dry-run.")
        return CleanupRouteDecision(kind="orphan_pins", threshold_mb=threshold_mb)
    if req.full_analysis:
        return CleanupRouteDecision(kind="full_analysis", threshold_mb=threshold_mb)
    return None


def _has_artifacts_conflicts(req: CleanupCliRequest) -> bool:
    return any(
        (
            _has_non_venv_flags(req),
            req.venvs_old,
            req.free_gb is not None,
            req.policy_matrix,
            req.projects_path is not None,
            req.days is not None,
            req.retention is not None,
            req.hours is not None,
        )
    )


def _check_docker_mode_conflicts(
    req: CleanupCliRequest,
    *,
    want_docker_old: bool,
    want_docker_all: bool,
    want_docker_containers: bool = False,
    want_docker_networks: bool,
    want_docker_stale: bool,
    want_orphaned: bool,
    want_ollama_old: bool,
) -> CleanupRouteDecision | None:
    docker_data = (
        want_docker_old or want_docker_all or want_docker_networks or want_docker_containers
    )
    if want_docker_old and want_docker_all:
        return _styled_err("Wybierz jeden zakres obrazów: --docker-old albo -c docker-all.")
    if want_docker_containers and (want_docker_old or want_docker_all or want_docker_networks):
        return _styled_err(
            "Wybierz jeden tryb czyszczenia Dockera: -c docker-containers albo obrazy/sieci."
        )
    if want_ollama_old and docker_data:
        return _styled_err("Czyszczenie Ollama i Dockera uruchom jako osobne akcje.")
    if want_docker_stale and (docker_data or want_ollama_old):
        return _styled_err("Optymalizację usług uruchom osobno od czyszczenia danych Dockera/Ollama.")
    if want_orphaned and (docker_data or want_docker_stale or want_ollama_old):
        return _styled_err("Czyszczenie osieroconych projektów uruchom jako osobną akcję.")
    if req.docker_stale_services and req.cleanup and req.cleanup != "docker-stale-services":
        return _styled_err("--docker-stale-services nie można łączyć z innym -c/--cleanup.")
    if req.orphaned_projects and req.cleanup and req.cleanup != "orphaned-projects":
        return _styled_err("--orphaned-projects nie można łączyć z innym -c/--cleanup.")
    if (
        req.docker_networks
        and req.cleanup
        and req.cleanup not in {"docker-all", "docker-unused", "docker-old", "docker-networks"}
    ):
        return _styled_err("--docker-networks można łączyć tylko z docker-all lub docker-old.")
    return None


def _resolve_docker_and_space_modes(
    req: CleanupCliRequest,
    threshold_mb: int,
    effective_days: float | None,
) -> CleanupRouteDecision | None:
    want_docker_old = req.docker_old or (req.cleanup == "docker-old")
    want_docker_all = req.docker_all or req.cleanup in {"docker-all", "docker-unused"}
    want_docker_containers = req.cleanup == "docker-containers"
    want_docker_networks = req.docker_networks or (req.cleanup == "docker-networks")
    want_docker_stale = req.docker_stale_services or (req.cleanup == "docker-stale-services")
    want_orphaned = req.orphaned_projects or (req.cleanup == "orphaned-projects")
    want_ollama_old = req.ollama_old or (req.cleanup == "ollama-old")

    space_flags = _space_flag_map(req)
    want_space = [name for name, flag in space_flags.items() if flag or req.cleanup == name]
    any_service_mode = any(
        (
            want_docker_old,
            want_docker_all,
            want_docker_containers,
            want_docker_networks,
            want_docker_stale,
            want_orphaned,
            want_ollama_old,
        )
    )
    if (
        len(want_space) > 1
        or (want_space and req.cleanup and req.cleanup not in space_flags)
        or (want_space and any_service_mode)
    ):
        return _styled_err(
            "Akcje odzyskiwania miejsca (snap/journal/cache/JetBrains/"
            "libvirt/gitive/docker-buildcache/docker-volumes/tmp/trash/thumbnails) uruchom jako osobną, pojedynczą akcję."
        )
    if want_space:
        return CleanupRouteDecision(
            kind="space_action",
            action_name=want_space[0],
            threshold_mb=threshold_mb,
            effective_days=effective_days,
        )

    conflict = _check_docker_mode_conflicts(
        req,
        want_docker_old=want_docker_old,
        want_docker_all=want_docker_all,
        want_docker_containers=want_docker_containers,
        want_docker_networks=want_docker_networks,
        want_docker_stale=want_docker_stale,
        want_orphaned=want_orphaned,
        want_ollama_old=want_ollama_old,
    )
    if conflict is not None:
        return conflict

    ordered_modes = (
        (want_docker_all, "docker_all"),
        (want_docker_containers, "docker_containers"),
        (want_docker_old, "docker_old"),
        (want_docker_networks, "docker_networks"),
        (want_docker_stale, "docker_stale_services"),
        (want_orphaned, "orphaned_projects"),
        (want_ollama_old, "ollama_old"),
    )
    for active, mode_name in ordered_modes:
        if active:
            return CleanupRouteDecision(
                kind=mode_name,
                threshold_mb=threshold_mb,
                effective_days=effective_days,
            )
    return None


def resolve_cleanup_route(req: CleanupCliRequest) -> CleanupRouteDecision:
    """Deterministically validate CLI flags and resolve the exact cleanup route."""
    if req.artifacts_paths or req.artifacts_system_wide or req.cleanup == "artifacts":
        if req.cleanup not in (None, "artifacts") or _has_artifacts_conflicts(req):
            return _usage_err("--artifacts uruchom jako osobną akcję (-c artifacts)")
        if not req.artifacts_paths and not req.artifacts_system_wide:
            return _usage_err("-c artifacts wymaga --artifacts PATH lub --artifacts-system-wide")
        return CleanupRouteDecision(kind="artifacts")

    threshold_mb = int(req.threshold_gb * 1024) if req.threshold_gb is not None else int(req.threshold)
    if req.policy_matrix:
        return CleanupRouteDecision(kind="policy_matrix", threshold_mb=threshold_mb)

    effective_days, days_err = _parse_effective_days(req)
    if days_err is not None:
        return days_err

    early = _check_early_exclusive_modes(req, threshold_mb, effective_days)
    if early is not None:
        return early

    mode = _resolve_docker_and_space_modes(req, threshold_mb, effective_days)
    if mode is not None:
        return mode

    if req.cleanup:
        return CleanupRouteDecision(
            kind="single_service",
            action_name=req.cleanup,
            threshold_mb=threshold_mb,
            effective_days=effective_days,
        )

    service_filter = [s for s in req.services.split(",") if s] if req.services else None
    return CleanupRouteDecision(
        kind="service_plan",
        threshold_mb=threshold_mb,
        effective_days=effective_days,
        service_filter=service_filter,
    )


def plan_service_cleanup(
    scanner: Any,
    *,
    selected_services: Sequence[str] | None = None,
) -> ServiceCleanupPlan:
    """Build a typed, side-effect-free cleanup plan from ServiceDataScanner."""
    raw = scanner.get_cleanup_plan(
        selected_services=list(selected_services) if selected_services is not None else None
    )
    services = list(raw.get("services") or [])
    total_gb = float(
        raw.get("total_size_gb")
        if raw.get("total_size_gb") is not None
        else sum(float(s.get("size_gb", 0.0) or 0.0) for s in services)
    )
    return ServiceCleanupPlan(
        raw_plan=raw,
        services_found=int(raw.get("services_found", len(services))),
        total_size_gb=round(total_gb, 4),
        safe_services=list(raw.get("safe_to_cleanup") or []),
        requires_review=list(raw.get("requires_review") or []),
        dangerous=list(raw.get("dangerous") or []),
    )


def _invoke_service_runner(
    runner: Callable[[dict[str, Any], bool], Mapping[str, Any]],
    svc: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    try:
        raw_res = runner(svc, dry_run)
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        LookupError,
        subprocess.SubprocessError,
    ) as exc:
        return {"success": False, "error": str(exc) or type(exc).__name__}
    if not isinstance(raw_res, Mapping):
        return {
            "success": False,
            "error": f"invalid runner result type: {type(raw_res).__name__}",
        }
    return dict(raw_res)


def execute_service_cleanup(
    plan: ServiceCleanupPlan,
    *,
    runner: Callable[[dict[str, Any], bool], Mapping[str, Any]],
    selected_services: Sequence[dict[str, Any]] | None = None,
    consent_granted: bool = False,
    dry_run: bool = False,
) -> ServiceCleanupExecution:
    """Execute a service cleanup plan with explicit consent gate and partial-failure accounting."""
    targets = list(selected_services) if selected_services is not None else list(plan.safe_services)
    if not targets:
        return ServiceCleanupExecution(
            outcome="empty",
            dry_run=dry_run,
            consent_granted=consent_granted,
            attempted_count=0,
            succeeded_count=0,
            failed_count=0,
            space_freed_gb=0.0,
        )

    if not dry_run and not consent_granted:
        return ServiceCleanupExecution(
            outcome="declined_consent",
            dry_run=False,
            consent_granted=False,
            attempted_count=0,
            succeeded_count=0,
            failed_count=0,
            space_freed_gb=0.0,
        )

    results: list[dict[str, Any]] = []
    executed_types: list[str] = []
    succeeded = 0
    failed = 0
    freed_gb = 0.0

    for svc in targets:
        res = _invoke_service_runner(runner, svc, dry_run)
        results.append(res)
        stype = str(svc.get("service_type") or svc.get("name") or "")
        if stype and stype not in executed_types:
            executed_types.append(stype)
        if res.get("success", False):
            succeeded += 1
            if not dry_run:
                freed_gb += float(res.get("space_freed_gb", 0.0) or 0.0)
        else:
            failed += 1

    if dry_run:
        outcome = "simulated" if failed == 0 else ("partial" if succeeded > 0 else "failed")
    elif failed == 0:
        outcome = "succeeded"
    elif succeeded > 0:
        outcome = "partial"
    else:
        outcome = "failed"

    return ServiceCleanupExecution(
        outcome=outcome,
        dry_run=dry_run,
        consent_granted=consent_granted,
        attempted_count=len(targets),
        succeeded_count=succeeded,
        failed_count=failed,
        space_freed_gb=round(freed_gb, 4),
        results=results,
        executed_service_types=executed_types,
    )


def verify_service_cleanup_readback(
    scanner: Any,
    plan: ServiceCleanupPlan,
    execution: ServiceCleanupExecution,
) -> ServiceCleanupReadback:
    """Perform explicit post-cleanup read-back via scanner to confirm actual state change."""
    if execution.dry_run or execution.outcome in ("declined_consent", "empty"):
        return ServiceCleanupReadback(
            verified=False,
            outcome="skipped",
            before_services_count=plan.services_found,
            after_services_count=plan.services_found,
            before_total_gb=plan.total_size_gb,
            after_total_gb=plan.total_size_gb,
            observed_delta_gb=0.0,
            remaining_service_types=[
                str(s.get("service_type") or s.get("name") or "") for s in plan.safe_services
            ],
        )

    target_types = execution.executed_service_types or None
    after_plan = plan_service_cleanup(scanner, selected_services=target_types)
    before_targets = [
        s
        for s in plan.raw_plan.get("services", [])
        if target_types is None or s.get("service_type") in target_types
    ]
    before_gb = round(sum(float(s.get("size_gb", 0.0) or 0.0) for s in before_targets), 4)
    after_gb = after_plan.total_size_gb
    delta_gb = round(max(0.0, before_gb - after_gb), 4)
    remaining_types = [
        str(s.get("service_type") or s.get("name") or "")
        for s in after_plan.raw_plan.get("services", [])
    ]

    if execution.outcome == "failed":
        rb_outcome = "failed"
    elif after_plan.services_found == 0 or (delta_gb > 0 and execution.failed_count == 0):
        rb_outcome = "succeeded"
    elif delta_gb > 0 or after_plan.services_found < len(before_targets):
        rb_outcome = "partial"
    else:
        rb_outcome = "partial" if execution.succeeded_count > 0 else "failed"

    return ServiceCleanupReadback(
        verified=True,
        outcome=rb_outcome,
        before_services_count=len(before_targets),
        after_services_count=after_plan.services_found,
        before_total_gb=before_gb,
        after_total_gb=after_gb,
        observed_delta_gb=delta_gb,
        remaining_service_types=remaining_types,
    )
