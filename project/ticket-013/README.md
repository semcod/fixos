# Ticket 013: Preserve accepted HITL choice across turn timeout

- **ID**: ticket-013
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Keep an accepted numbered HITL optimization choice actionable even when the
preceding LLM diagnosis used the previous time budget. Treat the configured
timeout as a limit for each LLM turn, suspend it while waiting for the human,
and show the actual remaining turn time measured after the model response.

This is a bounded regression fix for the iterative menu delivered by
ticket-012. It does not weaken command confirmation, command validation,
verification or trusted merge boundaries.

## Acceptance criteria

- [x] AC-01: Each LLM turn receives a fresh configured timeout without changing
  total wall-clock duration reporting for the interactive session.
- [x] AC-02: Human input does not consume the next LLM turn budget, so an
  accepted diagnostic shortcut reaches its focused planning turn.
- [x] AC-03: The action menu displays remaining time recalculated after the LLM
  reply instead of the stale pre-request value.
- [x] AC-04: Existing command confirmation, dangerous-command and verification
  boundaries remain unchanged.
- [x] AC-05: A regression test covers a diagnostic choice accepted after the
  prior LLM response exhausted its nominal budget.
- [x] AC-06: Focused tests, the full Python checks and the managed governance
  check pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
