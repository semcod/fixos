# Ticket 090: Release v2.2.57 and publish to PyPI via goal

- **ID**: ticket-090
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

SESSION_EXECUTION_AUTHORIZATION: Authorized by user in active session to release v2.2.57 and publish to PyPI via goal.

## Goal and scope

Bump `fixos` version to `2.2.57` in `pyproject.toml` and `VERSION` and publish `fixos==2.2.57` to PyPI.

## Acceptance criteria

- [x] AC-01: `pyproject.toml` and `VERSION` declare `2.2.57` and `fixos==2.2.57` is published to PyPI.
- [x] AC-02: `./project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
