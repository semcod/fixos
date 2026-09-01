---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-013
---
# Participant: codex (AI agent)

## Understanding

The ticket-012 menu correctly accepts a numeric diagnostic choice and queues a
focused planning prompt. However, `_process_turn()` captures the remaining
session time before the LLM request and renders that stale value afterward.
The timeout continues to use the session construction time, so a slow initial
diagnosis can consume the whole budget before the human sees the menu. The
accepted choice then returns to the loop, which raises `SessionTimeout` before
the focused prompt is sent.

The timeout must bound model work without invalidating a human choice already
accepted by the interactive workflow. Total session elapsed time remains a
separate reporting value.

## Execution plan

1. Preserve a distinct wall-clock timestamp for final session reporting.
2. Refresh the signal timeout and turn start at the beginning of every LLM
   turn, after the previous human choice has been accepted.
3. Recalculate the displayed remaining value after the LLM returns and clarify
   that the configured header value is a per-turn limit.
4. Add a regression test for the exact slow-diagnosis then numeric-choice
   transition, plus focused UI timing coverage.
5. Run focused and full stack checks followed by the managed governance gate.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Reproduced the failure path from the supplied transcript: the menu displayed
  a pre-LLM value of `00:02:01`, accepted `7`, then the next loop observed the
  already exhausted session-wide deadline and ended before focused planning.
- Split the total session timestamp from the per-turn timeout timestamp and
  refresh the signal deadline before every accepted LLM interaction.
- Recalculate the displayed remaining time after each model reply and label the
  configured value as `Limit tury LLM` instead of a misleading session maximum.
- Added regression coverage proving that an accepted diagnostic shortcut gets
  its focused second model call even when the previous reply consumed the old
  budget, while final session reporting retains total wall-clock duration.
- Focused tests pass 57 unit tests. Ruff, compileall and the full suite pass;
  the full suite reports 554 passed, 5 skipped and 16 deselected.
- The managed governance gate passes with zero errors and zero warnings.
- Recorded the user's existing explicit `goal -a` publication authorization
  for this continued fix and advanced the ticket to `IN_PROGRESS / PUBLICATION`.

## Blockers

- None inside the recorded intent or validated implementation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
