# Ticket 183: Bump version to 2.7.4 for fixos dns release

- **ID**: ticket-183
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-23

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: Explicit user request in active session to bump `fixos` version to `2.7.4` (including `ticket-182` `fixos dns` and built-in `dns` plugin) for PyPI release via `goal`.

## Acceptance criteria

- [x] AC-01: `VERSION` and `pyproject.toml` are updated to `2.7.4`.
- [x] AC-02: `./project/governance-check.sh` and `pytest -q tests/unit/test_dns_plugin.py` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
