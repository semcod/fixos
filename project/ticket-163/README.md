# Ticket 163: Stop auto cleanup at the free space goal

- **ID**: ticket-163
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18

## Goal and scope

Stop automatic disk cleanup between existing stages when the root filesystem
has reached the requested free-space target. Do not add cleanup candidates or
claim that existing grouped cache cleanup protects active processes.

## Acceptance criteria

- [x] AC-01: No subsequent cleanup stage runs after the target is reached;
  an already-satisfied target skips cleanup.
- [x] AC-02: Dry-run remains a preview and does not delete data; JSON reports
  executed stages and actual measured free space.
- [x] AC-03: Tests cover initially satisfied, mid-run and unmet targets.

## Session authorization

SESSION_EXECUTION_AUTHORIZATION: the user requested autonomous implementation,
verification and protected publication of the FixOS auto improvement.

## Verification commands

- `python3 -m ruff check fixos/cli/fix_cmd.py tests/unit/test_auto_cleanup.py`
- `pytest -q tests/unit/test_auto_cleanup.py tests/unit/test_auto_no_llm.py tests/unit/test_autonomous_reporting.py`
- `pytest -q`
- `./project/governance-check.sh --base origin/main`

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
