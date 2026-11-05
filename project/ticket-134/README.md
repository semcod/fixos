# Ticket 134: Track the branch-hygiene workflow before adoption

- **ID**: ticket-134
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-05

## Goal and scope

Continue the workflow-tracking prerequisite recorded under Fixos PLF-21812.
The existing broad workflow ignore prevents the canonical immutable adopter
from installing `.github/workflows/new-project-branch-hygiene.yml`.
Add its exact unignore alongside the existing governance-workflow exception.
The user's continuation, testing and merge request provides
SESSION_EXECUTION_AUTHORIZATION for this bounded slice and protected publication.

## Acceptance criteria

- [x] AC-01: Native Git reports the branch-hygiene workflow as trackable.
- [x] AC-02: Unrelated workflows remain ignored and installed managed bytes retain their pin.
- [ ] AC-03: Deterministic governance and independent exact-head publication pass.

The full immutable adoption and migration of the independently pinned PolicyDSL
files remain separate steps under PLF-21812. No legacy disposal is included.
