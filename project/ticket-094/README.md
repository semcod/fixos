# Ticket 094: Expand safe fixos auto reclamation

- **ID**: ticket-094
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-23

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requests more effective fixos auto while excluding user data and Downloads. Existing tickets 088 and 093 are integrated in main; no active checkout or open PR remains. Add explicit regenerable caches, retained Docker build cache cleanup and honest root-filesystem pressure reporting. Preserve dry-run, opt-outs and machine output.

## Acceptance criteria

- [x] AC-01: Cache/Downloads/symlink protections, dry-run, Docker timeout and root accounting regression tests pass.
- [x] AC-02: Governance check passes.

## Validation

168 cleanup and auto regression tests passed. Ruff and governance passed. Live dry-run produced valid JSON and found ~243 MB of additional cache without deletion. Root and tmpfs recovery are reported separately. Trash is opt-in. Publication remains separate from local validation.
