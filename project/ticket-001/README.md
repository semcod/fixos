# Ticket 001: Adopt new-project v0.16.1 governance

- **ID**: ticket-001
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-13

## Goal and scope

Adopt the complete, published `wellmanifest/new-project` v0.16.1 package at
exact revision `4e6ba5ec...`, preserve the existing analysis-owned
`project/README.md` and root `project.sh`, and configure FixOS-specific Python,
Docker, workstream and governed Goal delivery contracts.

## Acceptance criteria

- [x] AC-01: The user's instruction to standardize both repositories records
  `SESSION_EXECUTION_AUTHORIZATION` for this bounded adoption.
- [x] AC-02: The lock pins published new-project v0.16.1 at exact 40-character
  revision `4e6ba5ec...`, and an immediate adoption check reports no drift.
- [x] AC-03: The target manifest maps `fixos/**`, the existing nested Docker
  definitions and Python stack without replacing project-owned analysis.
- [x] AC-04: Goal delivery requires `goal -a`, defaults to protected PR mode
  and retains explicit direct-main/publish-only release modes.
- [x] AC-05: Governance, package tests, Compose validation and representative
  Docker build/runtime checks pass before a protected PR.

## Reviewed adoption plan

- Create the exact 37-file managed package from the published standard.
- Preserve the existing root `project.sh` and analysis-generated
  `project/README.md`; the standard installs canonical gates under `project/`.
- Limit target-specific customization to `.governance/manifest.json`,
  `.gitignore` and `goal.yaml`; retain `project.bat` as the standard's
  compatibility seed.
- Add narrow `.gitignore` exceptions for managed governance JSON, ticket
  intents and the adopted workflow; keep all other generated JSON and
  `.github` content under the existing ignore policy.
- Do not modify source, tests, dependency manifests, versions or releases.

## Boundary

- No package version bump, tag or registry publication.
- No deletion or modification of existing Docker networks or other worktrees.
- No use of the dirty live new-project worktree as adoption input.
- No human-owned `user-*.md` file is created or modified.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
