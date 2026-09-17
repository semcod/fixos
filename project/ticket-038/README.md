# Ticket 038: Own MANIFEST.in in integration workstream

- **ID**: ticket-038
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

`MANIFEST.in` is not listed in any workstream `ownedPaths`, so no ticket
can legally modify it — allocation for a packaging-manifest fix was
rejected with GOV-WORK-START-001 during ticket-035. Add `MANIFEST.in` to
`coordination.workstreams.integration.ownedPaths`; packaging manifests
belong with the dependency manifests already owned by integration.

This is a registry repair, not a component responsibility transfer —
`responsibilityChanges` stays false.

SESSION_EXECUTION_AUTHORIZATION: user asked to investigate fixos and fix
found problems; this is the governance gap found while fixing packaging.

## Acceptance criteria

- [x] AC-01: `.governance/manifest.json` lists `MANIFEST.in` under
  integration `ownedPaths` and `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
