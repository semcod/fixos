# Ticket 179: Report incomplete storage scan measurements safely

- **ID**: ticket-179
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-20
- **Source**: [semcod/fixos#244](https://github.com/semcod/fixos/issues/244)

## Goal and scope

Ensure `ServiceDataScanner` never treats incomplete or errored storage measurements as complete or safe to auto-clean:

1. Preserve `measure_tree` errors even when `bytes > 0`.
2. Preserve non-zero `du` exit status as an incomplete measurement alongside the partial KB total.
3. Retain incomplete and errored entries in `scan_service` even when reported size is below `threshold_mb`.
4. Propagate `size_unknown`, `measurement_incomplete`, `measurement_errors`, and disabled cleanup through `_merge_service_entries`.
5. Keep existing full successful measurements unchanged.

## Acceptance criteria

- [x] AC-01: `measure_tree` errors with nonzero bytes mark the scanned service entry incomplete (`size_unknown=True`, `measurement_incomplete=True`, `measurement_errors`, `can_cleanup=False`, `safe_to_cleanup=False`) and emit a scan warning.
- [x] AC-02: Non-zero `du` exits and `_analyze_service_path` exceptions below `threshold_mb` are retained by `scan_service` instead of being silently filtered out.
- [x] AC-03: `_merge_service_entries` retains incomplete/error markers and blocks cleanup when any merged path is incomplete or errored.
- [x] AC-04: Full successful measurements remain unchanged, and all tests + lint + `./project/governance-check.sh --base origin/main` pass.

## Verification commands

- `python3 -m ruff check fixos/diagnostics/service_scanner.py tests/unit/test_service_scanner.py`
- `pytest -q tests/unit/test_service_scanner.py tests/unit/test_cleanup_safety.py tests/unit/test_cleanup_effectiveness.py`
- `pytest -q`
- `./project/governance-check.sh --base origin/main`
