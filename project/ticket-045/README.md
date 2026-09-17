# Ticket 045: Relock uv.lock after pfix removal

- **ID**: ticket-045
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

Issue #46 / PLF-010: `uv.lock` went stale when ticket-022 removed `pfix`
from `pyproject.toml`, so `uv lock --check` fails on `main` and
`uv sync --locked` does not work. Regenerate the lockfile with the
pinned uv 0.12.13; the direct `pfix` requirement is gone (transitive
entries stay where other packages still need it) and the embedded fixos
version now reads 2.2.49.

SESSION_EXECUTION_AUTHORIZATION: user asked to execute pending tasks.

## Acceptance criteria

- [x] AC-01: `uvx --from uv==0.12.13 uv lock --check` passes.
- [x] AC-02: `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
