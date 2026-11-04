# Ticket 128: Build packages without recursive cleanup and release storage diagnostics

- **ID**: ticket-128
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested "wykonaj testy, analize,
naprawy, scal, bump"; PLF-21811. This is a material integration build repair,
including its version projections, not a release-only change. The old build
recursively cleans the checkout and calls absent .venv/bin/pip. Repair the
build under Wellman, preserve caches and neighboring worktrees, declare the
frontend in dev extras, and bump to 2.3.0 for the additive storage CLI since
v2.2.59. Application ticket-127 must merge before publishing this release.
No PyPI upload, policy change or user-data cleanup. Runtime installation is a
separate bounded operational effect after independent protected merge.

## Acceptance criteria

- [ ] AC-01: make build produces wheel/sdist from the selected environment without running clean, upgrading pip or changing sentinel files in caches/nested trees.
- [ ] AC-02: VERSION, project version, wheel/sdist metadata and installed CLI agree on 2.3.0; package contents include the qualified storage implementation.
- [ ] AC-03: Canonical docs describe alias evidence and observed validation; governance and independent exact-head publication pass with existing required checks.

## Validation

Application prerequisite merged independently in PR159 (8463c6d, approved
source d039c49). Build smoke produced wheel/sdist 2.3.0 and preserved cache
and nested bytecode sentinels. Package inspection verified 143 Python/YAML
files against source plus metadata, entrypoint and archive boundaries.
Managed governance PASS after observing the protected prerequisite receipt.
Version parity and the 55 affected regressions are rerun on the combined
source. Exact committed-source package checks and independent review follow;
installation happens only after qualified merge. Raw receipts stay private.
