# Ticket 042: Non-interactive cleanup --yes plus version 2.2.49 in package init

- **ID**: ticket-042
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

`fixos cleanup` currently requires a TTY: without stdin answers the
interactive selection stalls, so the command cannot run over plain SSH,
in cron or in CI. Add `--yes` which executes the same "all safe" plan
without prompting (identical safety gates; review/dangerous sections are
still displayed). Also bumps `fixos.__version__` to 2.2.49 — the version
bump joins this material ticket; VERSION/pyproject follow in the paired
integration ticket.

SESSION_EXECUTION_AUTHORIZATION: user asked to continue improving fixos.

## Acceptance criteria

- [x] AC-01: `python -m pytest -q tests/unit/test_cleanup_safety.py` passes.
- [x] AC-02: `python -m pytest -q tests/unit` passes.
- [x] AC-03: `./project/governance-check.sh` passes.

## Validation evidence

Recorded below after running the checks.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
