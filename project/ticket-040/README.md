# Ticket 040: Interactive UX: complete shell completer, full command menu, multi-select cleanup

- **ID**: ticket-040
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

Make every fixos option reachable without memorizing flags:

1. `fixos shell` TAB-completion is generated from the live click command
   tree — every registered command, subcommand and option completes; new
   flags (e.g. `-c`, `--docker-containers`) can no longer drift out of
   the hardcoded table.
2. The menu gains a `commands` entry printing the full command catalog
   with one-line help, so users can discover all ~25 commands from one
   place.
3. `fixos cleanup` individual selection shows a numbered list once and
   accepts a single input (`1,3,7-9`, `all`, `none`) instead of a
   confirm prompt per service. Dangerous entries keep their extra gate.

SESSION_EXECUTION_AUTHORIZATION: user asked to improve UX so all options
are reachable and selectable within a single command.

## Acceptance criteria

- [x] AC-01: `python -m pytest -q tests/unit/test_shell_ux.py` passes.
- [x] AC-02: `python -m pytest -q tests/unit` passes.
- [x] AC-03: `./project/governance-check.sh` passes.

## Validation evidence

Recorded below after running the checks.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
