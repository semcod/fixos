# Ticket 041: Fix NoSuchCommand removed in click 8.2 for typo suggestions

- **ID**: ticket-041
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

`fixos/cli/shared.py` raises `click.exceptions.NoSuchCommand`, which was
removed in click 8.2. On the pinned click (8.3/8.4) every typo path
(`fixos cleanuo`, `fixos quik`, gibberish tokens) dies with
`AttributeError` instead of the intended `No such command … Did you mean
…` usage error — four tests fail on main. Replace it with `ctx.fail`
carrying the same message.

SESSION_EXECUTION_AUTHORIZATION: user asked to continue improving fixos.

## Acceptance criteria

- [x] AC-01: `python -m pytest -q tests/unit/test_ask_and_nl_group.py` passes.
- [x] AC-02: `./project/governance-check.sh` passes.

## Validation evidence

Recorded below after running the checks.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
