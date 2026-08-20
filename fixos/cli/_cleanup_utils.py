"""Shared utilities for cleanup CLI commands."""

from __future__ import annotations

from collections.abc import Sequence

from fixos.diagnostics.utils import format_size as _format_size


def _format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    return _format_size(size_bytes)


def _parse_size_to_bytes(size_str: str) -> int:
    """Parse human-readable size to bytes."""
    size_str = size_str.strip().upper().replace(" ", "")
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
        "TB": 1024**4,
    }

    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(suffix):
            try:
                return int(float(size_str[: -len(suffix)].strip()) * mult)
            except ValueError:
                return 0

    try:
        return int(float(size_str))
    except ValueError:
        return 0


def _parse_size_to_gb(size_str: str) -> float:
    """Parse human-readable size to GB."""
    size_str = size_str.strip().upper()
    multipliers = {
        "B": 1 / (1024**3),
        "KB": 1 / (1024**2),
        "MB": 1 / 1024,
        "GB": 1,
        "TB": 1024,
    }

    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(suffix):
            try:
                return float(size_str[: -len(suffix)].strip()) * mult
            except ValueError:
                return 0

    try:
        return float(size_str) / (1024**3)
    except ValueError:
        return 0


def _parse_selection(
    selection: str,
    max_count: int,
    *,
    priorities: Sequence[str] | None = None,
) -> list[int]:
    """Parse user selection into list of indices."""
    selection = selection.strip().lower()

    if selection in ["none", "n", "skip", "s", ""]:
        return []

    if selection == "all":
        return list(range(max_count))

    if selection == "critical":
        if priorities is None:
            return []
        return [
            index
            for index, priority in enumerate(priorities[:max_count])
            if str(priority).strip().casefold() == "critical"
        ]

    try:
        indices = []
        for part in selection.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < max_count:
                    indices.append(idx)
        return sorted(set(indices))
    except Exception:
        return []


def _parse_numeric_range_set(nums: str) -> set:
    """Parse comma/range number string (e.g. '1,3,5-10') into a set of ints."""
    selected = set()
    for part in nums.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                selected.update(range(int(start), int(end) + 1))
            except ValueError:
                pass
        else:
            try:
                selected.add(int(part))
            except ValueError:
                pass
    return selected


def _build_dep_types(items: list) -> dict:
    """Group dev_projects items by dependency type."""
    dep_types = {}
    for item in items:
        dep_type = item.name.split(" (")[0] if " (" in item.name else item.name
        if dep_type not in dep_types:
            dep_types[dep_type] = {"items": [], "total": 0}
        dep_types[dep_type]["items"].append(item)
        dep_types[dep_type]["total"] += item.size_bytes
    return dep_types
