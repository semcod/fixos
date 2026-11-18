# Ticket 148: Document printer/mesh updates, index host-anomalies, and release 2.6.1

- **ID**: ticket-148
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user asked to execute
  backlog tasks for `semcod/fixos`, publish the updated release, and verify
  proper operation (2026-11-18).

## Goal and scope

1. Index `docs/information/host-anomalies.md` in `docs/README.md` (resolving the
   `DOCS_INDEX` finding reported by `wellmanifest/docs`).
2. Update `docs/information/printers.md` (`version: 2`) and
   `docs/information/mesh.md` (`version: 2`) to document `ticket-145` (`#183`),
   `ticket-146` (`#185`), and `ticket-147`.
3. Raise `VERSION` and `pyproject.toml` to `2.6.1`.

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_version_parity.py -q` passes for `2.6.1`.
- [x] AC-02: `wellmanifest/docs` `check.py` reports zero findings for
      `docs/information/printers.md`, `docs/information/mesh.md`, and
      `docs/information/host-anomalies.md`.
- [x] AC-03: Governance check passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
