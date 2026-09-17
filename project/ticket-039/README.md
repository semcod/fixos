# Ticket 039: Include YAML data in MANIFEST.in

- **ID**: ticket-039
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

`MANIFEST.in` only lists `recursive-include fixos *.py`, which excludes the
runtime YAML data from the sdist manifest. ticket-035 already ships the
files via setuptools package-data; this ticket makes the sdist manifest
explicit and consistent so the data is not silently dropped if
package-data is ever removed.

Depends on ticket-038 (MANIFEST.in is now owned by integration).

## Acceptance criteria

- [x] AC-01: MANIFEST.in contains `recursive-include fixos *.yaml`,
  governance-check passes, sdist still ships all 8 YAML files.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
