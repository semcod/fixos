# Ticket 067: release 2.2.52 version bump in VERSION and pyproject

- **ID**: ticket-067
- **Owner**: Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-11

## Goal and scope

Release projection: bump the two integration-owned version carriers (`VERSION`, `pyproject.toml`) to `2.2.52` so the release packages tickets 065-066 (`python -m fixos.cli` module execution entry point and dynamic setup.py single source of truth version parity).

SESSION_EXECUTION_AUTHORIZATION: user authorized autonomous execution, testing, publication, and delivery.

## Acceptance criteria

- [x] AC-01: `VERSION` and `pyproject.toml` declare `2.2.52`.
- [x] AC-02: `test_version_parity.py` and `./project/governance-check.sh` pass cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
