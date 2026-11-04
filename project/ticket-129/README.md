# Ticket 129: Reconcile legacy Fixos workspace evidence and ownership

- **ID**: ticket-129
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested "kontynuuj" following the
PLF-21812 legacy-workspace findings. Publish concrete reconciliation and a
protected-owner handoff in the canonical analysis. This fresh integration
writer owns documentation only; the foreign quarantine and legacy lease are
read-only. Preserve all dirty bytes and unique commits. Evidence and age do
not authorize takeover or deletion. Do not manufacture a protected observation.

## Acceptance criteria

- [ ] AC-01: Reconcile full known ticket109/110 criteria against pinned main and verify recovery of the exact backup commit and dirty file bytes.
- [ ] AC-02: Run current quick-snapshot tests and preserved tests against target source; distinguish behavior equivalence, content differences and unknown ownership.
- [ ] AC-03: Index canonical analysis, run native governance and obtain independent exact-head review; queue exact residual controller work without altering foreign state.

## Result

Canonical result: docs/analysis/legacy-workspace-reconciliation.md.
15 current and 15 preserved tests PASS against the pinned product source;
managed governance PASS (0 errors/warnings). Backup requirements bytes and
file-scoped patch IDs match. A private 21.6 MB bundle was restored with both
exact commit identities; all four dirty-file bytes were separately restored
and verified. Candidate report/evidence pass adopted JSON Schema validation.
Independent publication of this analysis is pending. Legacy lifecycle remains
pending protected identity/handoff and observation: Control says
ticket_not_found for PLF-20296; legacy lease has no fencing/CAS.
No foreign source/lease/ref changes. Raw receipts remain in private recovery.
