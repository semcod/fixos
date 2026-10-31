# Ticket 117: Preserve JetBrains system caches and Local History during explicit cleanup

- **ID**: ticket-117
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-31

## Goal and scope

The explicit --jetbrains cleanup path still selects whole IDE system-cache
roots, including LocalHistory, although generic service cleanup protects those
user file revisions. Exclude mixed system caches from this explicit path;
retain existing stale installation/version-data eligibility and explain the
protection in the existing CLI and JSON previews.

SESSION_EXECUTION_AUTHORIZATION: the user requested autonomous FixOS repairs
and execution of remaining host work on 2026-10-31. This safety correction
includes independent protected publication and both existing installations;
it does not authorize deleting live IDE data or user file history.

## Acceptance criteria

- [x] AC-01: Text/JSON previews do not propose entire JetBrains system-cache roots.
- [x] AC-02: Explicit --yes preserves cached user data and Local History while
  existing stale Toolbox cleanup still works; regression and governance pass.
- [ ] AC-03: Full stack checks, independent exact-head publication, deployment
  hashes, controlled history preservation and a live read-only preview pass.

## Validation

Three regression scenarios failed before the fix. All 58 affected tests and
the scoped Testless scan pass after the change. Changed-file Ruff and managed
governance pass. Full checks and independent publication bind the frozen head;
deployment verifies both installations and a read-only live preview.
