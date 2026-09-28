# Ticket 053: Interactive projects path prompt in stale venvs cleanup

- **ID**: ticket-053
- **Owner**: gemini:fixos-053-20260928
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: Add interactive prompt for custom projects path in stale venvs cleanup, following the days prompt, defaulting to ~/github.

## Acceptance criteria

- [x] AC-01: Interactive venv cleanup prompts for projects path after days prompt, defaulting to ~/github.
- [x] AC-02: Non-interactive and flag-provided path options continue to function unchanged.
- [x] AC-03: Unit tests and governance checks pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
