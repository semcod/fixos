# Ticket 156: Update Wellmanifest standards docs and release FixOS 2.7.0

- **ID**: ticket-156
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution of
  backlog tasks for `semcod/fixos` (`#168` / `PLF-21819` integration slice) and
  release publication via `goal -a`.

## Goal and scope

1. Update `docs/INFORMATION/WELLMANIFEST_STANDARDS.md` (`version: 4`, anchored at
   `e648537b2d87000f32333e97693c6b39249481c7`) documenting pinned POA (`0.1.0@b0432f3`),
   MCP (`0.1.0@91f0271`), NL-URI (`1.5.0@adc0056`, `semantic-v1`), and URIProcess
   (`0.3.0@0a81334`, replacing stale `bootstrap/uriprocess-standard` prose), why
   `nl-api-llm`, `FastMCP`, and standalone `uriprocess.json` packaging are excluded,
   and separate manifest vs static vs observed runtime canary evidence (`Closes #168`).
2. Bump `VERSION` and `pyproject.toml` to `2.7.0` for PyPI publication after merge.

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_version_parity.py tests/unit/test_wellman_canary.py`
      passes on `2.7.0`.
- [x] AC-02: `wellman check --root .` reports 0 errors and `wellmanifest/docs`
      `check.py --deliverable docs/INFORMATION/WELLMANIFEST_STANDARDS.md` reports 0
      findings on `docs/INFORMATION/WELLMANIFEST_STANDARDS.md`.
- [x] AC-03: `./project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
