# Ticket 029: Declare nested Docker paths as infrastructure-owned

- **ID**: ticket-029
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the human requested continuation of the
refactoring and publication work. FixOS declares Dockerfiles in nested
`docker/*` directories as supported test assets, but the governance manifest
only assigns the basename pattern `Dockerfile*` to the infrastructure
workstream. The policy matcher therefore rejects ordinary changes to the
declared Docker test images as unowned.

Add the repository-relative `docker/**` pattern to the manifest's
`infrastructure.ownedPaths`. This is a governance-only contract correction;
it does not change any Docker image, workflow, application code or dependency.
It unblocks ticket-028, which supplies the missing `git` package in the three
images used by the Multi-System jobs.

## Acceptance criteria

- [x] AC-01: The scope is authorized by the continuation request and the
  mismatch between `docker`'s declared Dockerfiles and infrastructure ownership
  is reproduced by the managed governance check.
- [x] AC-02: `.governance/manifest.json` assigns `docker/**` to the
  `infrastructure` workstream without changing other ownership rules.
- [x] AC-03: Governance and stack checks pass locally on the current material
  HEAD: `GOV-PASS` and `614 passed, 5 skipped, 16 deselected`.
- [ ] AC-04: The exact material HEAD is published through the protected
  Validator flow.

## Validation evidence

- The pre-change governance check rejected nested Docker paths as unowned by
  `infrastructure`.
- The candidate check passed with `GOV-PASS: passed (0 errors, 0 warnings)`.
- The Python suite passed with `614 passed, 5 skipped, 16 deselected`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
