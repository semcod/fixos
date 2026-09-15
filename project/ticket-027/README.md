# Ticket 027: Adopt current Wellmanifest governance and terminal receipt policy

- **ID**: ticket-027
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the human requested continuation after the
protected publication flow exposed that FixOS still pins Wellmanifest/new-project
0.16.1 while the local published standard is 0.20.31. Adopt the immutable current
standard through Goal, make its required managed host files trackable, and align
FixOS with the external terminal merge receipt lifecycle.

The adoption covers governance, host continuity, Python packaging metadata and
the pinned Policy DSL parser required by the current host contract. Application
source, runtime dependencies, tests, secrets and provider configuration remain
outside the accepted scope.

## Acceptance criteria

- [x] AC-01: The read-only adoption preflight identifies the published immutable
  standard revision and no managed target is blocked by Git ignore rules.
- [x] AC-02: Goal upgrades the managed governance package to new-project 0.20.31,
  tracks `.subactor/manifest.json` and `.github/copilot-instructions.md`, and
  records the exact source revision in `pyproject.toml`.
- [ ] AC-03: Managed governance, drift, stack and FixOS checks pass on the exact
  candidate head; no application runtime or dependency path changes.
- [ ] AC-04: The protected Validator verifies the exact material adoption PR and
  publishes the external terminal merge receipt; no closure PR is created.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
