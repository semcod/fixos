# ticket-165: docs(governance): reconcile TODO and CHANGELOG for 2.7.2 (#174, #171, #209)

- **ID**: ticket-165
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

Retire completed `#174` (`PLF-21812`) and `#171` (`PLF-21822`) items from `TODO.md` and record the `2.7.2` release summary in `CHANGELOG.md` covering `PR #208` (`ticket-162`), `PR #214` (`ticket-164` / `#209`), `#174`, and `#171`.

## Acceptance criteria

- [x] AC-01: `TODO.md` removes completed `#174` and `#171` entries and updates review date to `2026-11-19`.
- [x] AC-02: `CHANGELOG.md` records `## [2.7.2] - 2026-11-19` with verified links and `./project/governance-check.sh` passes with 0 errors.

## Evidence

- Verified `./project/governance-check.sh` (`GOV-PASS`) and `pytest -q tests/unit/test_standard_adoption_projection.py` (`1 passed`).
