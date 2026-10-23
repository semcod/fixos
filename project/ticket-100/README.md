# Ticket 100: Preserve persistent releases during target cleanup

- **ID**: ticket-100
- **Owner**: agent:codex (operator continuation)
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-23

## Goal and scope

Fix semcod/fixos#126. Release and snapshot directories under application data
are persistent deployment/rollback data. Preserve them regardless of age,
mode bits or incomplete reference inventory. Keep target cleanup useful through
its other existing cache tiers. Never execute real deletion during validation.

## Acceptance criteria

- [x] AC-01: old referenced and unreferenced releases/snapshots remain intact;
  direct stale/forged removal candidates and dry-run cannot count them as freed.
- [x] AC-02: meaningful target-cleanup regressions, lint and governance pass.

## Execution authorization

The operator requested safe FixOS cleanup excluding user data, then continued
pending issues with testing and protected merging. Imported GITHUB-126 is the
accepted request. PLF037 native633 is frozen in PR677 awaiting independent CI;
this ticket has disjoint repository/scope and fresh free-scope admission.
No causal claim or repair of previously missing services belongs here.

Validation: 22 target regressions and 161 affected cleanup tests passed. Ruff
and native governance passed. A synthetic baseline confirmed an 8-day-old
unit/current-referenced release was selected by the previous code without
executing deletion. No historical host removal attribution is established.
