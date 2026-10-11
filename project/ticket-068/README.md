# Ticket 068: package VERSION in MANIFEST.in and robust fallback in setup.py

- **ID**: ticket-068
- **Owner**: Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-11

## Goal and scope

Ensure `VERSION` is included in source distributions by adding `include VERSION` to `MANIFEST.in`, and provide a fallback in `setup.py` that reads version from `VERSION` if present, or parses `pyproject.toml` if absent. This ensures `python -m build` passes cleanly when creating wheels from an sdist tarball.

SESSION_EXECUTION_AUTHORIZATION: user authorized autonomous execution, testing, publication, and delivery.

## Acceptance criteria

- [x] AC-01: `MANIFEST.in` includes `VERSION` and `python -m build` successfully builds both sdist and wheel.
- [x] AC-02: `test_version_parity.py` and `./project/governance-check.sh` pass cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
