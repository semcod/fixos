# Ticket 078: cleanup_planner: ruff clean and no hardcoded sample home path

- **ID**: ticket-078
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

The last NOHARDCODE-009 error in fixos (wellmanifest/nohardcode balanced,
repository policy) is a literal user home path in the demo `main()` of
`fixos/interactive/cleanup_planner.py`. Changing that file makes CI lint it,
and it carried 47 pre-existing ruff findings (deferred from ticket-074).

ruff --fix (UP006/UP035/I001), `.values()` loops (PERF102/PLC0206), documented
`noqa` for the two intentional broad excepts, shebang removed from the
imported module, sample path via `Path.home()`. Tests pin priority order and
that one malformed suggestion does not drop the plan.

SESSION_EXECUTION_AUTHORIZATION: user requested continuing, merging, standardizing and testing.

## Acceptance criteria

- [x] AC-01: ruff clean on the file; new planner tests pass.
- [x] AC-02: full suite and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
