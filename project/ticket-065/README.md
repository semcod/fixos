# Ticket 065: allow module execution as python -m fixos.cli

- **ID**: ticket-065
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-11
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

Allow executing the fixOS CLI directly via `python -m fixos.cli` in addition to `python -m fixos` and the `fixos` console script.
Add `fixos/cli/__main__.py` and unit tests in `tests/unit/test_cli_main.py`.

## Acceptance criteria

- [x] AC-01: `python -m fixos.cli --version` and `--help` execute successfully and are verified by unit tests.
- [x] AC-02: `./project/governance-check.sh` passes with zero errors and warnings.

## Evidence

- `fixos/cli/__main__.py`: delegates to `fixos.cli.main()`.
- `tests/unit/test_cli_main.py`: tests module execution for `fixos` and `fixos.cli`.
