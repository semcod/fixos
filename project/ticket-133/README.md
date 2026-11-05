# Ticket 133: Fix project scanner stale detection and docker size calculation

- **ID**: ticket-133
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: User authorized fixing the two verified FixOS defects:
1. `scan_project_artifacts` in `fixos/diagnostics/project_scanner.py` falsely marks active project artifacts as `stale` based only on artifact mtime rather than project source activity.
2. `generate_cleanup_plan` in `fixos/diagnostics/service_cleanup.py` double-counts Docker cache in total sizes and safe actions.

## Acceptance criteria

- [x] AC-01: `scan_project_artifacts` checks project source activity and does not mark artifacts as `stale` if the project has recent source activity within `stale_days`.
- [x] AC-02: `generate_cleanup_plan` deduplicates overlapping Docker sizes in `total_size_gb` and safe age actions.
- [x] AC-03: Regression unit tests cover both fixes and `./project/governance-check.sh` passes.

## Validation

- `python3 -m pytest tests/unit/test_project_scanner.py -v`: 32 passed (including `TestProjectScannerActivityAwareStale`).
- `python3 -m pytest tests/unit/test_service_cleanup.py tests/unit/test_cleanup_plan_contract.py -v`: 47 passed (including `TestDockerCleanupPlanDeduplication`).
- `ruff check fixos/diagnostics/project_scanner.py fixos/diagnostics/service_cleanup.py tests/unit/test_project_scanner.py tests/unit/test_service_cleanup.py`: All checks passed.
- `./project/governance-check.sh`: GOV-PASS: passed (0 errors, 0 warnings).
- `wellman check`: passed with 0 errors.
