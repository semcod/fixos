# ticket-175: chore(integration): bump VERSION and pyproject.toml to 2.7.3

- **ID**: ticket-175
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

Bump `VERSION` and `pyproject.toml` from `2.7.2` to `2.7.3` in parity with `fixos.__version__` and `CHANGELOG.md` for the `2.7.3` PyPI release.

## Acceptance criteria

- [x] AC-01: `VERSION` and `pyproject.toml` both declare `2.7.3` and `tests/unit/test_version_parity.py` passes.
- [x] AC-02: `./project/governance-check.sh` passes with zero errors and warnings.
