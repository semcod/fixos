# Ticket 054: Continue venv cleanup with partial observations

- **ID**: ticket-054
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-28

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user asked to repair the venv cleanup,
test it, and merge it, then clarified that an unreadable portion should be left
alone while the scan continues over what it can inspect. Keep independent
process observations independent: a denied field must not discard paths read
from other fields or suppress candidates in unrelated projects. Preserve the
30-day activity policy and protect environments with local tree errors, recent
activity, or a known process path. The CLI must describe partial observation
without claiming that all removal is blocked.

## Acceptance criteria

- [x] AC-01: Process fields are observed independently. Access errors are
  reported while readable paths from the same process remain available.
- [x] AC-02: Partial process/discovery errors do not abort inventory or blanket
  block unrelated projects; unreadable project/environment trees remain
  protected and their sizes remain unknown.
- [x] AC-03: Removal revalidation applies the same scoped policy and still
  protects known active projects, changed identities, and per-tree errors.
- [x] AC-04: CLI reports partial observation and eligible candidates without
  saying that all removal is blocked.
- [ ] AC-05: Focused regressions, Ruff, and the managed governance gate pass;
  publication uses OneDev and the independent Validator on the exact head.

## Delivery

No user project environments are removed during implementation. Preserve the
existing age threshold and fallback scanner behavior. Focused venv regressions
pass (38 tests), all unit tests pass (593 tests), Ruff passes, and the managed
governance gate passes. Exact-head OneDev and independent Validator evidence is
pending.
