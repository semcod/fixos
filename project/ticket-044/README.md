# Ticket 044: Own uv.lock in the integration workstream

- **ID**: ticket-044
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

Issue #46 / PLF-010: ticket-022 removed `pfix` from `pyproject.toml`
without regenerating `uv.lock`, so `uv lock --check` fails on `main`.
The lockfile is not owned by any workstream, so no ticket may legally
edit it. Append `uv.lock` to `integration.ownedPaths` (same precedent as
`MANIFEST.in` in ticket-038); the relock itself is a follow-up
integration ticket.

SESSION_EXECUTION_AUTHORIZATION: user asked to execute pending tasks.

## Acceptance criteria

- [x] AC-01: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
