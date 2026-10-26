# Ticket 101: Reclaim unused 7d project artifacts and state partitions in auto and target cleanup

- **ID**: ticket-101
- **Owner**: agent:antigravity (operator request)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

Improve `fixos` (`fixos auto`, `fixos cleanup --free-gb`, `fixos cleanup --state-old`, `fixos cleanup --projects-old`, `fixos projects`) so that it reclaims disk space from developer projects and date-partitioned application state/data unused for more than 7 days (1 week), while preserving all active projects, recent worktrees, user personal files, and persistent deployment releases/snapshots (`~/.local/share/<owner>/releases|release|snapshots`).

## Acceptance criteria

- [x] AC-01: `fixos` reclaims date-partitioned state/data (`--state-old`, default 7 days) and safe regenerable project artifacts (`venv`/`.venv`, `node_modules`, `target`, build/test/lint caches) in projects with no source or artifact modification in the last 7 days (`> 7 days`) and no active processes, mounts, symlinks, or active delivery worktrees; `scan_venvs` skips costly source tree walks when a project has no `venv`/`.venv`.
- [x] AC-02: Unit tests, `ruff check`, `./project/governance-check.sh`, and `wellman check` pass.

## Execution authorization

Direct user prompt on 2026-10-26 requesting freeing disk space with `fixos` and improving `fixos` to reclaim space for projects and data from the last week (`> 7 days`) when unused.
