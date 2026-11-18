# Ticket 144: Document fixos mesh diagnostics and release 2.6.0

- **ID**: ticket-144
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — document the mesh host
  diagnostics (`ticket-142` / `ticket-143`) under `docs/information/mesh.md`
  and raise package version to `2.6.0` (2026-11-18).

## Goal and scope

Document `fixos mesh` and `fixos printers --mesh` under `docs/information/mesh.md`
per `wellmanifest/docs`, index it in `docs/README.md`, and bump `VERSION` and
`pyproject.toml` to `2.6.0`.

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_version_parity.py -q` passes for `2.6.0`.
- [x] AC-02: `wellmanifest/docs` `check.py --deliverable docs/information/mesh.md`
      reports zero findings for `docs/information/mesh.md`.
- [ ] AC-03: Governance check and Wellman check pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
