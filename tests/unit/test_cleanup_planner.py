"""CleanupPlanner grouping and priority order (guards the ruff cleanup)."""

from __future__ import annotations

from fixos.interactive.cleanup_planner import CleanupPlanner, Priority


def _suggestion(path: str, priority: str, size_gb: float) -> dict:
    return {
        "type": "cache_cleanup",
        "priority": priority,
        "path": path,
        "size_gb": size_gb,
        "description": path,
        "command": f"rm -rf {path}",
        "safe": True,
        "impact": "high",
    }


def test_prioritized_order_is_high_then_medium_then_low():
    planner = CleanupPlanner()
    grouped = planner.group_by_category(
        [
            _suggestion("/tmp/low", "low", 9.0),
            _suggestion("/tmp/high", "high", 1.0),
            _suggestion("/tmp/medium", "medium", 5.0),
        ]
    )

    ordered = planner.prioritize_actions(grouped)

    assert [a.priority for a in ordered[:3]] == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]


def test_malformed_suggestion_does_not_drop_the_plan():
    planner = CleanupPlanner()

    grouped = planner.group_by_category([None, _suggestion("/tmp/ok", "high", 1.0)])

    assert sum(len(actions) for actions in grouped.values()) >= 1
