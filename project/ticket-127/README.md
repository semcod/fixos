# Ticket 127: Protect hardlink aliases in storage diagnostics

- **ID**: ticket-127
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested "wykonaj testy, analize,
naprawy, scal, bump". PLF-21811 tracks this follow-up. Fix the discovered
first-path-only hardlink classification without deleting data. Preserve the
foreign quarantine and existing protected delivery policy. Release build and
version changes require their own integration-owned material implementation.

## Acceptance criteria

- [ ] AC-01: Cache-first aliases cannot mask protected or manager-owned contexts; alias order does not change protection and unique allocation is counted once.
- [ ] AC-02: Table, HTML and CSV expose aliases, decision provenance and observation time with proper escaping; incomplete alias knowledge stays explicit.
- [ ] AC-03: Affected tests, Ruff and managed governance pass, followed by independent exact-head review and authorized merge.

## Validation

55 affected tests PASS; full default suite 1119 PASS, 5 existing skips and
16 default deselections in 57.14 s. Ruff and managed governance PASS
(0 errors/warnings). Eight alias-context regressions fail against the original
source and pass against the repair. Testless collected coverage for the 55
affected tests; its 53 advisory planfiles remain local and grant no deletion
or test-removal authority. Independent exact-head review and merge are pending.
Raw evidence is private recovery storage, not a product artifact.
