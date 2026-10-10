# Ticket 064: release 2.2.51 version bump in VERSION and pyproject

- **ID**: ticket-064
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-10

## Goal and scope

Release projection: bump the two integration-owned version carriers (`VERSION`, `pyproject.toml`) to 2.2.51 so the release packages tickets 059-063 (offline tmp cleanup routing, all commands in interactive shell menu, rust native scan acceleration and shell visual dashboard, quick_snapshot rust optimization, and dynamic version parity with test isolation).

SESSION_EXECUTION_AUTHORIZATION: user authorized autonomous execution, testing, publication, and investigation across repositories.

## Acceptance criteria

- [x] AC-01: `VERSION` and `pyproject.toml` declare 2.2.51.
- [x] AC-02: `test_version_parity.py` and `governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
