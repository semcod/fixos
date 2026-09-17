# Ticket 043: Release 2.2.49 version bump in VERSION and pyproject

- **ID**: ticket-043
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

Release projection: bump the two integration-owned version carriers
(`VERSION`, `pyproject.toml`) to 2.2.49 so the release packages tickets
040-042 — interactive UX overhaul, the `NoSuchCommand` fix on click 8.2+
and `cleanup --yes`. `fixos/__init__.py` is bumped inside ticket-042.

SESSION_EXECUTION_AUTHORIZATION: user asked to continue and release.

## Acceptance criteria

- [x] AC-01: `VERSION` and `pyproject.toml` declare 2.2.49.
- [x] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
