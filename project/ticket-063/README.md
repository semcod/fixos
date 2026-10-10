# Ticket 063: enforce version parity test isolation and dynamic package version

- **ID**: ticket-063
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-10

## Goal and scope

Implement single source of truth for version in fixos package:
1. Make `fixos/__init__.py` dynamically resolve version from `VERSION` (source checkout) or package metadata (installed distribution) so it never drifts from `VERSION`.
2. Add `tests/unit/test_version_parity.py` to assert that `VERSION`, `pyproject.toml`, `setup.py`, and `fixos.__version__` are strictly equal.
3. Isolate developer `.env` in `tests/conftest.py` so local environment keys do not pollute test assertions.
4. Mock filesystem cache root in `tests/unit/test_dashboard.py:test_collect_dashboard_scan_returns_valid_data` to eliminate test timeouts on developer environments.

SESSION_EXECUTION_AUTHORIZATION: user authorized autonomous execution, testing, publication, and investigation across repositories.

## Acceptance criteria

- [x] AC-01: `fixos/__init__.py` dynamically resolves version without hardcoding.
- [x] AC-02: `tests/unit/test_version_parity.py` validates consistency across version carriers.
- [x] AC-03: `tests/unit/test_dashboard.py` and `tests/conftest.py` pass without timeout or environment pollution.
- [x] AC-04: `./project/governance-check.sh` passes with 0 errors and 0 warnings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
