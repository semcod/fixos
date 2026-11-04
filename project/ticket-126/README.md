# Ticket 126: Run storage proc regressions on every platform

- **ID**: ticket-126
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: complete the validation portion of PLF-039
by making the storage proc regressions run on every platform. The independent
Validator rejected the original conditional test. After external merge of
PR156, its worktree was removed; preserve that history and use this freshly
allocated canonical ticket/lease, not the old writer. Recover only the already
prepared test from content-addressed snapshot f0ad67ce3b6a7e95c6ddc1b6991cebca35b5076180eaca03ba256dfbfd3d8d39.
Keep real current-process Linux acceptance evidence separately in recovery.
No runtime, policy, dependencies, markers, host data or other ticket changes.

## Acceptance criteria

- [ ] AC-01: Exercise fd, mmap and deleted-block accounting using portable proc fixtures with assertions on every platform.
- [ ] AC-02: Exercise unavailable proc explicitly; no platform branch bypasses the assertions.
- [ ] AC-03: Run all affected tests, Ruff and managed governance; preserve the separate real Linux process probe and obtain fresh exact-head independent validation.

## Tracking boundary

Validation: 56 affected tests PASS, managed governance PASS (0 errors/warnings),
Ruff PASS. Separate real current-process Linux acceptance confirms open-fd and
open-deleted block detection with the unchanged runtime implementation.
This follow-up strengthens coverage without changing product behavior.

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
