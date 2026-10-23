# Ticket 096: Simplify cleanup planning (PLF-020)

- **ID**: ticket-096
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-23

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user repeated continuation, testing and protected merging after completion of tickets094/095. Continue the next open FixOS queue item PLF-020, which explicitly requests a behavior-preserving refactor. Fresh Python/radon measurement is CC24 (the old queue artifact said18) at b1ce525. Extract risk grouping and safe full/prune accounting; preserve exact actions, schema, ordering, warnings, filtering, rounding and user data protection. Local Planfile state and native implementation are linked; no duplicate implementation is active.

## Acceptance criteria

- [x] AC-01: Contract and existing cleanup/scanner regressions pass; get_cleanup_plan CC is at most15 and extracted helpers do not exceed15.
- [x] AC-02: Changed-file Ruff and governance pass; request independent publication of the exact committed head.

## Validation

10 contract tests passed against the unchanged baseline before refactoring. After extracting helpers, all 235 affected cleanup/scanner/auto regressions passed. Fresh radon complexity: get_cleanup_plan 24 to 14; risk grouping 4 and safe reclaim totals 5. Ruff and governance passed. No new cleanup target, dependency or runtime behavior was introduced. Publication remains independent.
