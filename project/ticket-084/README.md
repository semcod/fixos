# Ticket 084: fix-perf-audit-and-adopt-standard-packs

- **ID**: ticket-084
- **Owner**: antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-17

## Goal and scope

Resolve all 17 `PERF-AUDIT-*` findings (`PERF-AUDIT-KWARG-001` and `PERF-AUDIT-SUBPROC-001`) across 15 files in `fixos/` and adopt `wellmanifest/wellman` baseline standard packs in `.governance/standard-adoption.json`.

SESSION_EXECUTION_AUTHORIZATION: user selected "Remediate all PERF-AUDIT-* findings and verify standard-pack adoption".

## Acceptance criteria

- [x] AC-01: `audit_repository` reports 0 `PERF-AUDIT-*` findings on `fixos`.
- [x] AC-02: `python3 .governance/standard_pack_check.py --root .` reports `findings=0` and `./project/governance-check.sh` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
