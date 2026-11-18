"""Contract tests for service_cleanup_usecase extracted from cleanup_services (CC=98) (#169)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from fixos.core.service_cleanup_usecase import (
    CleanupCliRequest,
    execute_service_cleanup,
    plan_service_cleanup,
    resolve_cleanup_route,
    verify_service_cleanup_readback,
)


class _FakeScanner:
    def __init__(self, plans: list[dict[str, Any]]):
        self._plans = list(plans)
        self.calls: list[list[str] | None] = []

    def get_cleanup_plan(self, selected_services=None) -> dict[str, Any]:
        self.calls.append(selected_services)
        idx = min(len(self.calls) - 1, len(self._plans) - 1)
        return self._plans[idx]


def test_route_resolution_and_conflict_guards():
    assert resolve_cleanup_route(CleanupCliRequest()).kind == "service_plan"
    assert resolve_cleanup_route(CleanupCliRequest(threshold_gb=1.5)).threshold_mb == 1536
    assert resolve_cleanup_route(CleanupCliRequest(retention="24h")).effective_days == 1.0

    bad_ret = resolve_cleanup_route(CleanupCliRequest(retention="invalid-ret"))
    assert bad_ret.error_kind == "usage_error"

    conflict_space = resolve_cleanup_route(CleanupCliRequest(snap_old=True, journal_cleanup=True))
    assert conflict_space.error_kind == "styled_error"

    conflict_docker = resolve_cleanup_route(CleanupCliRequest(docker_old=True, docker_all=True))
    assert conflict_docker.error_kind == "styled_error"

    conflict_venv = resolve_cleanup_route(CleanupCliRequest(venvs_old=True, docker_old=True))
    assert conflict_venv.error_kind == "usage_error"


def test_usecase_success_partial_declined_consent_and_readback():
    initial_raw = {
        "services_found": 2,
        "total_size_gb": 3.5,
        "services": [
            {"service_type": "npm", "name": "npm cache", "size_gb": 1.5, "risk_level": "safe"},
            {"service_type": "pip", "name": "pip cache", "size_gb": 2.0, "risk_level": "safe"},
        ],
        "safe_to_cleanup": [
            {"service_type": "npm", "name": "npm cache", "size_gb": 1.5, "risk_level": "safe"},
            {"service_type": "pip", "name": "pip cache", "size_gb": 2.0, "risk_level": "safe"},
        ],
        "requires_review": [],
        "dangerous": [],
    }
    after_success_raw = {
        "services_found": 0,
        "total_size_gb": 0.0,
        "services": [],
        "safe_to_cleanup": [],
        "requires_review": [],
        "dangerous": [],
    }
    after_partial_raw = {
        "services_found": 1,
        "total_size_gb": 2.0,
        "services": [
            {"service_type": "pip", "name": "pip cache", "size_gb": 2.0, "risk_level": "safe"},
        ],
        "safe_to_cleanup": [
            {"service_type": "pip", "name": "pip cache", "size_gb": 2.0, "risk_level": "safe"},
        ],
        "requires_review": [],
        "dangerous": [],
    }

    # 1. Declined consent -> zero runner invocations and skipped read-back
    scanner_declined = _FakeScanner([initial_raw])
    plan = plan_service_cleanup(scanner_declined)
    runner_called = False

    def forbidden_runner(_svc, _dry):
        nonlocal runner_called
        runner_called = True
        return {"success": True}

    declined = execute_service_cleanup(plan, runner=forbidden_runner, consent_granted=False, dry_run=False)
    assert declined.outcome == "declined_consent"
    assert runner_called is False
    rb_declined = verify_service_cleanup_readback(scanner_declined, plan, declined)
    assert rb_declined.verified is False
    assert rb_declined.outcome == "skipped"

    # 2. Full success + read-back verification
    scanner_ok = _FakeScanner([initial_raw, after_success_raw])
    plan_ok = plan_service_cleanup(scanner_ok)
    exec_ok = execute_service_cleanup(
        plan_ok,
        runner=lambda svc, _dry: {"success": True, "space_freed_gb": svc["size_gb"]},
        consent_granted=True,
        dry_run=False,
    )
    assert exec_ok.outcome == "succeeded"
    assert exec_ok.space_freed_gb == 3.5
    rb_ok = verify_service_cleanup_readback(scanner_ok, plan_ok, exec_ok)
    assert rb_ok.verified is True
    assert rb_ok.outcome == "succeeded"
    assert rb_ok.observed_delta_gb == 3.5
    assert rb_ok.remaining_service_types == []

    # 3. Partial failure + truthful read-back
    scanner_part = _FakeScanner([initial_raw, after_partial_raw])
    plan_part = plan_service_cleanup(scanner_part)
    exec_part = execute_service_cleanup(
        plan_part,
        runner=lambda svc, _dry: (
            {"success": True, "space_freed_gb": 1.5}
            if svc["service_type"] == "npm"
            else {"success": False, "error": "permission denied"}
        ),
        consent_granted=True,
        dry_run=False,
    )
    assert exec_part.outcome == "partial"
    assert exec_part.succeeded_count == 1
    assert exec_part.failed_count == 1
    rb_part = verify_service_cleanup_readback(scanner_part, plan_part, exec_part)
    assert rb_part.verified is True
    assert rb_part.outcome == "partial"
    assert rb_part.observed_delta_gb == 1.5
    assert rb_part.remaining_service_types == ["pip"]


def _cyclomatic_complexity(func_node: ast.FunctionDef) -> int:
    branches = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.ExceptHandler,
        ast.With,
        ast.AsyncWith,
        ast.IfExp,
        ast.comprehension,
    )
    score = 1
    for node in ast.walk(func_node):
        if isinstance(node, branches):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
    return score


def test_cleanup_services_cyclomatic_complexity_reduced_below_20():
    cleanup_cmd_path = Path(__file__).resolve().parents[2] / "fixos" / "cli" / "cleanup_cmd.py"
    tree = ast.parse(cleanup_cmd_path.read_text(encoding="utf-8"))
    func = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "cleanup_services"
    )
    assert _cyclomatic_complexity(func) < 20
