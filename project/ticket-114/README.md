# Ticket 114: Classify disk pressure using capacity available to services

- **ID**: ticket-114
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-31

## Goal and scope

The live root filesystem has about 2.5% available capacity, but DiskAnalyzer
reports 94% usage and only warning severity because its denominator includes
capacity reserved from ordinary processes. Calculate utilization using used
bytes plus available bytes while preserving raw size fields and thresholds.

SESSION_EXECUTION_AUTHORIZATION: the user requested continuing FixOS repairs
and merges on 2026-10-31. This bounded correction includes independent protected
publication and deployment into the two existing host installations. It grants
no filesystem-reserve change, deletion of unknown data or approval bypass.

## Acceptance criteria

- [x] AC-01: Reserved capacity cannot mask critical or exhausted application
  capacity; unchanged ordinary and empty-filesystem cases remain explicit.
- [ ] AC-02: Affected tests, full required checks and managed governance pass.
- [ ] AC-03: Independent exact-head publication and deployed verification pass.

## Validation

Eight capacity cases cover reserved-block pressure, exhausted available space,
ordinary utilization, an unused filesystem, and an invalid zero-capacity
observation. Four failed against the baseline with warning/healthy severity
instead of critical. All 15 affected tests now pass, including Testless coverage
collection. Changed-file Ruff and whitespace checks passed. The complete suite,
required Python matrix, protected review and deployment are publication work.

The initial XS contract mistakenly estimated 20 active implementation minutes;
the adopted limit is ten. The remaining two-file implementation was bounded to
ten minutes without widening its class, scope or budgets. The owner released
the earlier editing reservation and reacquired a real fenced lease bound to
the corrected intent. External controller receipts retain both plan hashes.

The first full-suite run exposed a pre-existing live BuildKit dependency in a
proposal unit fixture. Independently reviewed ticket-115 / PR #147 fixed that
fixture. This ticket was reconciled onto its merged base with an updated intent
and a fresh controller lease; capacity implementation and regression tests
remain byte-for-byte unchanged. The resulting head requires fresh validation.
