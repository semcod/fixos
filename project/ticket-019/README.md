# Ticket 019: Fix CLI command typo detection and execution safety

- **ID**: ticket-019
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-12

## Goal and scope

Detect and intercept CLI command typos (e.g. `cleanuo` -> `cleanup`) before forwarding to the LLM.
Improve command routing in `NaturalLanguageGroup` and heuristic matching in `ask_cmd.py` (prevent accidental Docker stops/removals).
Add execution safety checks (`is_dangerous`, interactive confirmation for system modifications) to prevent destructive commands from running without approval.

## Acceptance criteria

- [x] AC-01: Unknown command typos with close matches (like `cleanuo` -> `cleanup`) suggest the correct command and are not blindly treated as LLM prompts.
- [x] AC-02: Heuristic matching in `ask_cmd` only targets Docker when docker keywords are present, and properly routes module-specific repairs (e.g. audio).
- [x] AC-03: Generated LLM commands check `is_dangerous` and prompt for confirmation on modifying actions in interactive sessions.
- [x] AC-04: Automated tests verify typo interception, heuristic matching, and safety guards.
- [x] AC-05: `./project/governance-check.sh` passes.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-antigravity.md](ai-antigravity.md)

