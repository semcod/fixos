# Ticket 158: Pin PLF-033 Wellmanifest standards in standards-lock and reconcile TODO/CHANGELOG

- **ID**: ticket-158
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution and verification of remaining FixOS backlog tasks (`PLF-033` and `TODO.md` reconciliation).

## Goal and scope

1. Pin immutable 40-hex commit revisions and `sha256:<64-hex>` contract digests for `wellmanifest/docs` (`0.6.0@b536d01`), `wellmanifest/logs` (`0.5.0@b5c8790`), `wellmanifest/worktrees` (`0.5.4@3146119`), `wellmanifest/license` (`1.0.0@313ab4a`), and `wellmanifest/report` (`0.1.0@370f532`) in `.governance/standards-lock.json` (`PLF-033`).
2. Reconcile `TODO.md` against merged `main` commits (`ticket-001`..`ticket-062`), removing completed historical entries and recording current external blockers (`#171`, `#174`) plus verified open backlog items.
3. Record `2.7.0` and `2.7.1` summaries in `CHANGELOG.md`.

## Acceptance criteria

- [x] AC-01: `wellman check --root .` and `python3 .governance/standard_pack_check.py --root .` pass with 0 errors.
- [x] AC-02: `./project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
