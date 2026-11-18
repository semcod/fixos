# Ticket 159: Publish Planfile-GitHub sync audit, update Wellmanifest docs to v5, and bump FixOS to 2.7.1

- **ID**: ticket-159
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution, verification, and PyPI publication of remaining FixOS backlog tasks (`#170` / `PLF-21821` and `PLF-033`).

## Goal and scope

1. Publish `docs/ANALYSIS/PLANFILE_GITHUB_SYNC_AUDIT.md` (`wellmanifest.docs/document/v2`) documenting the bidirectional `fixos-planfile-sync.{service,timer}` worker, live canary `PLF-21826` (`semcod/fixos#202`) + `planfile.sync-receipt/v1` receipt, `#130`–`#133` & `PLF-21813`..`21825` reconciliation, classification of all 23 unmapped historical `done` records, and upstream blockers for `#171` (`heyasa/heyasa#891`) and `#174` (`wellmanifest/new-project#575`) (`Closes #170`).
2. Advance `docs/INFORMATION/WELLMANIFEST_STANDARDS.md` to `v5` documenting `PLF-033` pins and applicability classifications (`docs`, `logs`, `worktrees`, `license`, `report`) and link the new audit report in `docs/README.md`.
3. Bump `VERSION` and `pyproject.toml` to `2.7.1`.

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_version_parity.py` passes with `2.7.1`.
- [x] AC-02: `wellmanifest/docs` `check.py --deliverable` reports 0 findings on both v2 documents.
- [x] AC-03: `./project/governance-check.sh` and `wellman check --root .` pass with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
