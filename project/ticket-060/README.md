# Ticket 060: add all available commands to interactive shell menu

- **ID**: ticket-060
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-07

## Goal and scope

Populate the interactive shell menu (`fixos shell`) with all 34 available commands
listed under `DOSTĘPNE KOMENDY` in `fixos` welcome banner. Keep shortcuts functional,
format menu columns clearly, and update UX test coverage.

## Acceptance criteria

- [x] AC-01: `MENU_ITEMS` in `fixos/cli/shell_cmd.py` contains all commands from the welcome list.
- [x] AC-02: Column formatting accommodates long commands like `cleanup --docker-stale-services`.
- [x] AC-03: `tests/unit/test_shell_ux.py` validates complete menu shortcuts and execution.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
