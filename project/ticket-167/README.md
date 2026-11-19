# ticket-167: feat(agent,cli): persist HITL anonymization, sign rollback snapshots, and unify legacy CLI

- **ID**: ticket-167
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

1. Maintain a persistent session-scoped `AnonymizationContext` across all turns of `HITLSession` (`fixos/agent/hitl_session.py`, `fixos/agent/session_handlers.py`) so numbered aliases (`[IP-PRIVATE-1]`, `[UUID-1]`, `[USER-2]`) and primary aliases (`[USER]`, `[HOSTNAME]`, `[HOME]`) remain consistent across initial diagnostics, user problem descriptions, command execution outputs, and fail-closed contextual deanonymization.
2. Add signed snapshot persistence (`fixos.rollback-snapshot/v2` with canonical SHA-256 + HMAC-SHA256 verification and `SnapshotIntegrityError`), atomic writes, and pre-execution journal crash recovery (`fixos.rollback-journal/v1`) to `RollbackSession` (`fixos/orchestrator/rollback.py`), with end-to-end integration tests.
3. Unify formatting and PEP 604/585 static typing in legacy CLI commands (`scan`, `features`, `provider` / `llm` / `test-llm`) without altering any public CLI options or subcommands.

## Acceptance criteria

- [x] AC-01: `HITLSession` retains a single `AnonymizationContext` across multiple turns, resolves session-bound numbered and primary aliases without `ResolutionError`, and rejects unknown or unselected aliases fail-closed (`tests/e2e/test_hitl_multiturn_and_snapshot_recovery.py`).
- [x] AC-02: `RollbackSession` signs persisted snapshots (`snapshot_sha256` + `hmac-sha256`), detects tampering via `SnapshotIntegrityError`, and recovers interrupted pre-execution journals and orphaned temporary files after a simulated crash (`tests/e2e/test_hitl_multiturn_and_snapshot_recovery.py`).
- [x] AC-03: `scan`, `features`, and `provider` (`llm`, `providers`, `test-llm`) use unified formatting and complete type annotations while preserving all public Click flags, arguments, and subcommands (`tests/unit/test_legacy_cli_commands.py`).
