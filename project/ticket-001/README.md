# Ticket 001: Adopt new-project v0.16.1 governance

- **ID**: ticket-001
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
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
- [x] AC-06: Protected CI and deterministic Validator approval bind the exact
  final head; its unchanged tree is merged and post-merge CI passes.

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

## Publication

- Governed Goal pull-request delivery opened
  [PR #1](https://github.com/semcod/fixos/pull/1) from the ticket-bound remote
  branch after repeating all 465 selected tests.
- The prerequisite portability PR #2 was independently approved at exact head
  `1440421905...`, merged as `9b3ab40548...`, and passed post-merge Python and
  five-distribution Docker CI. PR #1 now includes that mainline history and is
  bound to `9b3ab40548...` as its refreshed accepted base.
- PR #1 passed Python 3.10/3.11/3.12, governance and the five-distribution
  Docker matrix on exact head `ca8e19b43440df3f9ace7c5d3d17858407cdcb42`.
  Validator review `4929641466` deterministically approved that SHA for
  `ticket-001`; its LLM observations remained explicitly advisory.
- PR #1 merged as `647dd4baf0ed3d98afbdc26c25211bc5a140479c`.
  Its second parent is the approved head and both trees equal
  `cc9bfba53413fb8c711f254cad89cf14987c172a`.
- Post-merge CI runs `31724131145` and `31724131127` passed all supported
  Python versions, Fedora, Ubuntu, Debian, Arch, Alpine and `test-summary`.
  The remote implementation branch and its merged local worktree were removed
  before this governance-only closure began from integrated `main`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
