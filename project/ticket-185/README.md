# Ticket 185: Emit uritime urtlog records for fixos diagnostics and cleanup vetos

- **ID**: ticket-185
- **Owner**: agent:antigravity (SESSION_EXECUTION_AUTHORIZATION from user request)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-23

## Goal and scope

Add a fail-open, zero-dependency `uritime.urtlog.record/v2` telemetry emitter in
`fixos/diagnostics/urtlog_emit.py` and wire `evaluate_cleanup_vetos` in
`fixos/diagnostics/project_scanner.py` to record `HOLD_PROTECTED` cleanup vetos
when `FIXOS_URTLOG_STATE_DIR` or `URTLOG_STATE_DIR` is configured.

## Acceptance criteria

- [x] AC-01: `fixos/diagnostics/urtlog_emit.py` emits valid `uritime.urtlog.record/v2` JSONL records when configured, stays no-op when unconfigured, and fails open on `OSError`.
- [x] AC-02: `evaluate_cleanup_vetos` emits a `fixos.cleanup_veto` record whenever a hard veto forces `HOLD_PROTECTED`.
- [x] AC-03: Unit tests in `tests/unit/test_urtlog_emit.py` and `tests/unit/test_project_scanner.py` pass alongside `./project/governance-check.sh`.
