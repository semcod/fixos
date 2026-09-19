# Ticket 049: Protect JetBrains Local History from cleanup

- **ID**: ticket-049
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested safe cleanup audit, blocker repair, tests, push and merge, reaffirmed with “kontynuuj, scalaj, testuj”. Core ticket-361 is frozen in its independent publication queue. This isolated fixOS ticket owns only its declared cleanup source/tests.

The JetBrains system directory contains caches and LocalHistory. Deleting every IDE directory loses recoverable file revisions. Classify this mixed group as protected and remove bulk deletion even for explicit category selection. Keep a read-only inventory and explain Local History.

Reference: https://www.jetbrains.com/help/idea/local-history.html

## Acceptance criteria

- [x] AC-01: Authorized scope and isolated ownership recorded.
- [x] AC-02: JetBrains cannot enter safe automatic cleanup or generate a bulk deletion command; regression tests cover the scanner and explicit cleanup path.
- [ ] AC-03: Full offline test suite and governance pass; independent publication and merge are observed separately.

## Validation

Two regressions reproduced the unsafe behavior before the fix; all 36 focused tests now pass. Full suite: 690 passed, 5 skipped, 16 deselected (slow/docker/real_api). Governance and changed-file Ruff lint pass. Independent review and merge remain pending.
