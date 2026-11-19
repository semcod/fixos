# ticket-166: docs(audit): publish #174/#171 closure reports and bump to 2.7.2

- **ID**: ticket-166
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

Publish final governed closure documentation for `#174` (`PLF-21812`) and `#171` (`PLF-21822` / `#209`), refresh `docs/INFORMATION/WELLMANIFEST_STANDARDS.md` (v6) and `docs/README.md`, and bump FixOS version carriers (`VERSION`, `pyproject.toml`) to `2.7.2`.

## Acceptance criteria

- [x] AC-01: `docs/analysis/legacy-workspace-reconciliation.md` (v4), `docs/ANALYSIS/PLANFILE_GITHUB_SYNC_AUDIT.md` (v2), `docs/INFORMATION/WELLMANIFEST_STANDARDS.md` (v6), and `docs/README.md` pass `wellmanifest/docs` `check.py --prepare` and `--complete --deliverable` with zero findings.
- [x] AC-02: `VERSION` and `pyproject.toml` match `2.7.2`, passing `tests/unit/test_version_parity.py` and `./project/governance-check.sh`.

## Evidence

- Verified `wellmanifest/docs` `check.py --complete`, `./project/governance-check.sh` (`GOV-PASS`), and `pytest -q tests/unit/test_version_parity.py tests/unit/test_standard_adoption_projection.py` (`3 passed`).
