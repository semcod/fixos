# Ticket 190: Offer idle memory candidates in fixos auto

- **ID**: ticket-190
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-28
- **Related issues**: `semcod/fixos#233`, `semcod/fixos#227`

## Goal and scope

When `fixos auto` sees critical RAM or swap pressure, rank processes by `RSS + VmSwap` with CPU idle time and age, list idle long-running user GUI applications as opt-in candidates (with PID + `create_time` identity verification reused from `orphaned_workloads.py`), provide explicit `--close-idle-apps` and interactive opt-in without killing processes by default, and print a memory before/after summary next to the disk summary.

## Acceptance criteria

- [x] AC-01: Rank processes by `RSS + VmSwap`, CPU idle time, and age when critical RAM/swap is detected, strictly protecting agent sessions and system services.
- [x] AC-02: Offer idle long-running GUI apps as opt-in candidates and close only explicitly confirmed targets (`--close-idle-apps` or interactive confirmation) bound to `(root_pid, create_time)`.
- [x] AC-03: Report before/after available RAM and used swap alongside disk summary in `fixos auto` text and JSON output without regressing existing `auto` or `quick_snapshot` tests.
- [x] AC-04: Pass `ruff check`, full `pytest -q`, and `./project/governance-check.sh --base origin/main`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
