# Ticket 141: Release fixos 2.5.0 with printer diagnostics

- **ID**: ticket-141
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-17
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — the user asked to
  continue and merge after ticket-139 and ticket-140 (2026-11-17).

## Goal and scope

Add `docs/information/printers.md` describing `fixos printers`, its checks,
repairs, evidence and limits, list it in `docs/README.md`, and raise `VERSION`
and `pyproject.toml` to 2.5.0 so an installed fixOS includes ticket-139 and
ticket-140. No code changes. `CHANGELOG.md` is owned by the governance
workstream and is not touched here.

## Acceptance criteria

- [x] AC-01: Version carriers agree on 2.5.0.
- [x] AC-02: The document follows the docs standard (front matter, seven
      `docs:section` markers, index entry) and states only verified results.
- [ ] AC-03: Governance check and exact-head review pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
