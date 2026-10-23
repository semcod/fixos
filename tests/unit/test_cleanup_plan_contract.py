"""Public cleanup-plan contracts for PLF-020's behavior-preserving refactor."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from fixos.diagnostics.service_cleanup import PRUNE_UNREFERENCED, ServiceCleaner
from fixos.diagnostics.service_scanner import ServiceDataInfo, ServiceType


def service(kind, name, size_gb, risk, **kwargs):
    return ServiceDataInfo(
        service_type=kind,
        name=name,
        path=f"/cache/{name}",
        size_mb=size_gb * 1024,
        size_gb=size_gb,
        description=name,
        can_cleanup=True,
        cleanup_command=f"clean-{name}",
        preview_command=f"preview-{name}",
        safe_to_cleanup=risk == "safe",
        risk_level=risk,
        **kwargs,
    )


@pytest.fixture
def planning_inputs(monkeypatch):
    services = [
        service(ServiceType.NPM, "review", 3.456, "review"),
        service(ServiceType.PNPM, "prune", 2.345, "safe"),
        service(
            ServiceType.NPM,
            "cache",
            1.236,
            "safe",
            details={"reclaimable_size_gb": "0.26"},
        ),
        service(
            ServiceType.OLLAMA,
            "models",
            4.567,
            "dangerous",
            details={"reclaimable_size_gb": "0.333"},
        ),
        service(
            ServiceType.DOCKER,
            "unknown",
            5.678,
            "unknown",
            details={"reclaimable_size_gb": "0.011"},
        ),
        service(ServiceType.CONDA, "conda-prune", 0.789, "safe"),
    ]
    scanner = SimpleNamespace(
        threshold_mb=50,
        scan_all_services=Mock(return_value=services),
        scan_warnings=[{"service_type": "docker", "code": "partial-scan"}],
    )
    cleaner = ServiceCleaner(scanner)
    age_action = {"name": "old-tmp", "size_gb": 0.111, "risk_level": "safe"}
    build_age = Mock(return_value=[age_action])
    monkeypatch.setattr(cleaner, "build_safe_age_actions", build_age)
    return cleaner, scanner, services, age_action, build_age


def test_plan_preserves_schema_order_risk_tiers_and_reclaim_totals(planning_inputs):
    cleaner, scanner, services, age_action, build_age = planning_inputs
    original_services = deepcopy(services)
    plan = cleaner.get_cleanup_plan()

    assert set(plan) == {
        "threshold_mb",
        "services_found",
        "total_size_gb",
        "safe_cleanup_gb",
        "safe_prune_gb",
        "requires_review_gb",
        "dangerous_gb",
        "manager_reported_reclaimable_gb",
        "services",
        "safe_to_cleanup",
        "requires_review",
        "dangerous",
        "warnings",
    }
    assert plan["threshold_mb"] == 50
    assert plan["services_found"] == 7
    assert plan["total_size_gb"] == 18.18
    assert plan["safe_cleanup_gb"] == 1.35
    assert plan["safe_prune_gb"] == 3.13
    assert plan["requires_review_gb"] == 3.46
    assert plan["dangerous_gb"] == 4.57
    assert plan["manager_reported_reclaimable_gb"] == 0.6
    assert [s["name"] for s in plan["services"]] == [
        "old-tmp",
        "review",
        "prune",
        "cache",
        "models",
        "unknown",
        "conda-prune",
    ]
    assert [s["name"] for s in plan["safe_to_cleanup"]] == [
        "old-tmp",
        "prune",
        "cache",
        "conda-prune",
    ]
    assert [s["name"] for s in plan["requires_review"]] == ["review"]
    assert [s["name"] for s in plan["dangerous"]] == ["models"]
    assert plan["safe_to_cleanup"][0] is age_action
    assert plan["services"][0] is age_action
    assert plan["safe_to_cleanup"][1]["reclaim"] == PRUNE_UNREFERENCED
    assert plan["safe_to_cleanup"][2]["cleanup_command"] == "clean-cache"
    assert plan["safe_to_cleanup"][2]["preview_command"] == "preview-cache"
    assert plan["warnings"] == scanner.scan_warnings
    assert plan["warnings"] is not scanner.scan_warnings
    assert services == original_services
    scanner.scan_all_services.assert_called_once_with()
    build_age.assert_called_once_with(None)


@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        (None, ["review", "prune", "cache", "models", "unknown", "conda-prune"]),
        ([], ["review", "prune", "cache", "models", "unknown", "conda-prune"]),
        (["npm"], ["review", "cache"]),
        (["missing"], []),
    ],
)
def test_service_filter_preserves_empty_list_semantics_and_age_input(
    planning_inputs,
    selected,
    expected,
):
    cleaner, _, _, _, build_age = planning_inputs
    build_age.return_value = []
    plan = cleaner.get_cleanup_plan(selected)
    assert [s["name"] for s in plan["services"]] == expected
    assert plan["services_found"] == len(expected)
    build_age.assert_called_once_with(selected)


def test_empty_plan_has_zero_totals_and_handles_absent_scan_warnings(monkeypatch):
    scanner = SimpleNamespace(threshold_mb=25, scan_all_services=Mock(return_value=[]))
    cleaner = ServiceCleaner(scanner)
    monkeypatch.setattr(cleaner, "build_safe_age_actions", lambda selected: [])
    plan = cleaner.get_cleanup_plan()
    for field in (
        "total_size_gb",
        "safe_cleanup_gb",
        "safe_prune_gb",
        "requires_review_gb",
        "dangerous_gb",
        "manager_reported_reclaimable_gb",
    ):
        assert plan[field] == 0
    for field in (
        "services",
        "safe_to_cleanup",
        "requires_review",
        "dangerous",
        "warnings",
    ):
        assert plan[field] == []


@pytest.mark.parametrize(
    ("tier", "name"),
    [
        ("safe_to_cleanup", "cache"),
        ("requires_review", "review"),
        ("dangerous", "models"),
    ],
)
def test_each_tier_keeps_independent_top_level_service_dictionaries(
    planning_inputs,
    tier,
    name,
):
    cleaner, _, _, _, _ = planning_inputs
    plan = cleaner.get_cleanup_plan()
    all_entry = next(s for s in plan["services"] if s["name"] == name)
    tier_entry = next(s for s in plan[tier] if s["name"] == name)
    assert all_entry == tier_entry
    tier_entry["cleanup_command"] = "selected-command"
    assert all_entry["cleanup_command"] == f"clean-{name}"


def test_failed_scan_does_not_become_an_empty_successful_plan(monkeypatch):
    scanner = SimpleNamespace(
        scan_all_services=Mock(side_effect=RuntimeError("scan failed"))
    )
    cleaner = ServiceCleaner(scanner)
    build_age = Mock()
    monkeypatch.setattr(cleaner, "build_safe_age_actions", build_age)
    with pytest.raises(RuntimeError, match="scan failed"):
        cleaner.get_cleanup_plan()
    build_age.assert_not_called()
