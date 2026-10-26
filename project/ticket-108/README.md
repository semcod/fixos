# Ticket 108: Handle root-owned project artifacts in projects-old cleanup with bounded non-interactive sudo fallback

- **ID**: ticket-108
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

1. In `fixos/cli/_cleanup_space.py`, handle `PermissionError` during project artifact cleanup (`_cleanup_projects_old` / `_remove_selected`) when build tools or Docker leave root-owned artifacts (e.g. `node_modules`, `target`, `.pytest_cache`).
2. Add strict `_project_artifact_allowed` validation ensuring paths resolve strictly within the project root, without following symlinks or escaping the project root, and avoiding mount points.
3. Use bounded non-interactive sudo (`sudo -n rm -rf -- ...`) when available, or emit an actionable remediation command.
4. Add comprehensive unit tests in `tests/unit/test_cleanup_space.py` covering `PermissionError` handling on stale project artifacts without following symlinks or escaping the project root.

SESSION_EXECUTION_AUTHORIZATION: Governed Subactor publication ticket PLF-20295 (GitHub issue semcod/fixos#132).

## Acceptance criteria

- [x] AC-01: When `shutil.rmtree` raises `PermissionError` in `_cleanup_projects_old` (or `_remove_selected`), clearly report permission-denied items and, when `sudo -n` is available and target paths pass strict `_project_artifact_allowed` validation, allow bounded non-interactive removal or emit an actionable remediation command.
- [x] AC-02: Unit tests in `tests/unit/test_cleanup_space.py` cover `PermissionError` handling on stale project artifacts without following symlinks or escaping the project root.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
