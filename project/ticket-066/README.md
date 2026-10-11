# Ticket 066: align setup.py dynamic version and update readme badge

- **ID**: ticket-066
- **Owner**: Antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-11

## Goal and scope

Align `setup.py` to read `VERSION` dynamically, adhering to the `GOV-VERSION-001` single source of truth standard.
Update the version badge in `README.md` to `2.2.51`.
Remove stale `setup.py:version` entry from `goal.yaml` `versioning.files`.
Add `setup.py` to `governance.ownedPaths` and `integration.ownedPaths` in `.governance/manifest.json`.

## Acceptance criteria

- [x] AC-01: `setup.py` dynamically evaluates version from `VERSION` (`2.2.51`), and `README.md` displays `version-2.2.51-blue`.
- [x] AC-02: Unit tests pass (`pytest -q tests/unit/test_version_parity.py`) and `./project/governance-check.sh` passes cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
