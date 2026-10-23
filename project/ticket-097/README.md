# Ticket 097: Honest autonomous completion and dry-run reporting (PLF-034)

- **ID**: ticket-097
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-23

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested continued repair, tests and protected merging of FixOS. The original transcript still reproduces a false all-problems-fixed completion claim when zero repairs occur. Human reporting also counts failed and simulated actions as repairs. Inspection additionally found dry-run guarding only the heuristic path: centralize it in the shared EXEC handler to protect LLM sessions too. Preserve live command policy, legacy FixAction records and machine-output schema. No new deletion target or fleet policy change.

## Acceptance criteria

- [x] AC-01: No-action, failed, successful and dry-run reporting cases pass; both heuristic and LLM dry-runs never execute a command; existing auto safety/JSON tests pass.
- [x] AC-02: Ruff and governance pass; keep IN_PROGRESS/PUBLICATION through independent exact-head review and merge.

## Validation

Before the fix, seven reporting/dry-run cases failed and the legacy JSON case passed. The LLM dry-run failure called only a mocked executor, never a real shell command. After centralizing the guard and fixing reporting, all 49 reporting, auto safety and authentication-stop tests passed. Changed-file Ruff and governance passed. Both session modes retain normal execution outcomes and simulate without calling the executor.
