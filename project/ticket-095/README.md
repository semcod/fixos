# Ticket 095: Protect interactive cache cleanup

- **ID**: ticket-095
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-23

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested continued tests and protected merging of the safe-cleanup objective. PR122 is independently approved and merged as cf8d52b. Its advisory review identifies that interactive user-cache cleanup skips the path safety check used by --yes. Apply the same symlink and nested-mount guard in every mode, including after confirmation. Preserve manual selection of regular unknown cache directories.

## Acceptance criteria

- [x] AC-01: Regression cases for interactive mounts, symlink replacement during confirmation, dry-run and ordinary selected caches pass.
- [x] AC-02: Ruff and governance pass.

## Validation

173 cleanup and auto regression tests passed, including five new interactive safety cases. Ruff and governance passed. PR122 and its protected approval/merge were observed before allocating this bounded follow-up.
