# Ticket 012: Iteracyjny wybór remediacji HITL

- **ID**: ticket-012
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-01

## Goal and scope

Make every diagnosed optimization selectable in the HITL session, including
when an LLM returns a useful human-readable diagnosis but omits the required
structured remediation plan. Present stable, numbered shortcuts, focus the LLM
on one selected problem at a time, and refresh the menu after a successful
remediation so it contains only the work that remains.

## Acceptance criteria

- [x] AC-01: A diagnosis-only LLM response produces a numbered fallback list
  without inventing or executing commands.
- [x] AC-02: Selecting a fallback item asks the LLM for a bounded structured
  remediation plan for only that problem.
- [x] AC-03: Every actionable strategy has a visible numeric shortcut and a
  successful choice removes all alternatives for the resolved finding.
- [x] AC-04: After each successful remediation the next menu is refreshed and
  renumbered to show only remaining optimizations; failed or refused work stays
  selectable.
- [x] AC-05: Existing confirmation, dangerous-command, verification and
  recommended-action safety boundaries remain intact.
- [x] AC-06: Focused tests, the full Python checks and the managed governance
  check pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
