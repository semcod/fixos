# Ticket 083: release 2.2.54: docker volume cleanup, nohardcode waiver, standards docs

- **ID**: ticket-083
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

Release projection for 2.2.54 (PyPI has 2.2.53): `fixos cleanup
--docker-volumes` with parallel size measurement (tickets 081, 082), the
reviewed nohardcode waiver (080), cleanup_planner lint (078) and the
standards/ssot documentation (077, 079). `VERSION` and `pyproject.toml`
declare 2.2.54; the runbook (version 3) documents `--docker-volumes`.
Publication follows the merge via `goal -a --delivery-mode publish-only`.

SESSION_EXECUTION_AUTHORIZATION: user selected "Wydaj fixos 2.2.54".

## Acceptance criteria

- [x] AC-01: version carriers declare 2.2.54; version parity test passes.
- [x] AC-02: docs checker and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
