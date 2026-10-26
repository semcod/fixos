# Ticket 103: Allow planfile.yaml in governance workstream and fix corrupted trailing YAML block

- **ID**: ticket-103
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

Fix the truncated trailing block at the end of `planfile.yaml` (`me: Fix ai-boilerplate issues...`) that causes `yaml.scanner.ScannerError` in Monag and blocks Willman/Heyasa intake (`project_intake_refused:observe,project_observation_errors`), and add `planfile.yaml` to the `governance` workstream `ownedPaths` in `.governance/manifest.json`.

## Acceptance criteria

- [x] AC-01: `planfile.yaml` parses cleanly via `yaml.safe_load` without `ScannerError`.
- [x] AC-02: `./project/governance-check.sh` passes with 0 errors.

## Execution authorization

SESSION_EXECUTION_AUTHORIZATION recorded from user instruction to create new issues and delegate execution for `heyasa` in `semcod/fixos`, reconciling the `project_intake_refused:observe,project_observation_errors` gate per host technical autonomy rules.
