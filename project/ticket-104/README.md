# Ticket 104: Integrate auto cleanup with target ladder and report findings honestly

- **ID**: ticket-104
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT

## Goal and scope

1. In `fixos/cli/fix_cmd.py`, integrate `fixos auto` with `run_free_target_ladder` when free space remains below target or safety floor after initial cache pruning.
2. Ensure exit codes from `fixos auto` reflect whether disk pressure remains or goal was unmet (`2` for goal unmet, `3` for disk pressure remaining).
3. In `fixos/agent/autonomous_session.py`, record critical diagnostic findings (including disk pressure and quick snapshot alerts) even when no shell command is provided, instead of falsely reporting 0 problems found.

SESSION_EXECUTION_AUTHORIZATION: user authorized full automated disk cleanup implementation and reporting fixes.

## Acceptance criteria

- [x] AC-01: `autonomous_session` records disk pressure and quick alert findings in `problems_found`.
- [x] AC-02: `fixos auto` honestly reports diagnosed problems and quick alerts in autonomous session.
- [x] AC-03: Full pytest unit suite passes (58 tests passed).
