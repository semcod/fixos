# Ticket 036: Regression test for packaged YAML data files

- **ID**: ticket-036
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

Guard the ticket-035 packaging fix: `tests/unit/test_packaging_data.py`
asserts the eight runtime YAML files are reachable inside the `fixos`
package and that `pyproject.toml` declares matching
`[tool.setuptools.package-data]` patterns. A regression fails CI instead
of silently shipping `features profiles` with an empty list.

SESSION_EXECUTION_AUTHORIZATION: user asked to investigate fixos and fix
found problems.

## Acceptance criteria

- [x] AC-01: `python -m pytest -q tests/unit/test_packaging_data.py` passes.
- [x] AC-02: `./project/governance-check.sh` passes.

## Validation evidence

Recorded below after running the checks.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
