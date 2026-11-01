# Ticket 121: Constrain published package contents and verify Goal source observation

- **ID**: ticket-121
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-01
- **maxActiveMinutes**: 45

SESSION_EXECUTION_AUTHORIZATION: execute, test and request protected merge/publication for the existing Goal migration and cyclic release observation. The public Fixos 2.2.58 wheel contains three developer Python files outside fixos/; its implicit namespace discovery also makes source verification unsupported. Constrain package discovery explicitly, retain every Fixos asset, and join 2.2.59 version projections to this material implementation. Consume Goal[publish]>=2.2.8 only after its independent public artifact verification, keeping Python markers and unrelated lock records unchanged. No separate release-only ticket or source/CI bypass.

- [x] AC-01: Exactly the unintended developer entries leave the wheel; all Fixos package assets and 132 Python sources are preserved and match Git.
- [ ] AC-02: Version/lock projections, supported interpreters, affected regressions and governed local delivery pass.
- [ ] AC-03: Required checks and independent merge pass; Goal publishes the package and the canonical public source observer reports matched.
