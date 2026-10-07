# Ticket 059: Expose tmp cleanup and correct offline ask routing

- **ID**: ticket-059
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-07

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requests correction of missing tmp cleanup and wrong command mapping; original request authorizes fixing and merging confirmed bugs. Operational Planfile PLF-031 records this scope. Prior Willman source merged and runtime recovery completed; FixOS74/75 retain ownership blockers in checkpoints.

Local work-start reconciliation: archived024/031 deltas concern endpoint/governance files and have no overlap with the five CLI/test files. No registered competing writer or open PR found; preserve archive branches.

## Acceptance criteria

- [x] AC-01: Expose tmp cleanup and retention in the available commands and consistent shell menu mapping.
- [x] AC-02: Exact tmp cleanup requests invoke existing interactive cleanup without LLM/config API lookup; preserve dry-run and confirmation; unrelated intents remain separate.
- [x] AC-03: Tests and governance pass; LLM errors retain original prompt and show neutral relevant guidance.
- [ ] AC-04: Publish and merge via protected OneDev and independent Validator.

## Validation

643 unit tests passed, including87 targeted tests. Ruff and governance passed (0 errors,0 warnings). Host /tmp was never cleaned during development; deletion regression uses an isolated test fixture.
