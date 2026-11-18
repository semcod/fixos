# Ticket 152: Input-bound MCP receipts with read-back and POA plan-hash capability grants

- **ID**: ticket-152
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution of
  backlog tasks for `semcod/fixos` (`#163` / `PLF-21814` and `#166` / `PLF-21817`).

## Goal and scope

1. Implement input-bound idempotency (`request_id` bound to `operation_id`,
   `registry_digest`, and canonical `input_digest`), single-flight POSIX/thread
   locking, pre-effect atomic journal (`<req_id>.journal.json`) transitioning to
   `state="uncertain"` on interrupted execution, verifiable `receipt_hash` +
   UUIDv5 `receipt_urn`, and explicit post-cleanup read-back (`succeeded`,
   `partial`, `failed`, `uncertain`) in `fixos/mcp_receipts.py` (`Closes #163`).
2. Implement the minimal POA profile in `fixos/poa_grants.py`: closed task plan
   with pinned RFC 8785 (`RFC8785-JCS+SHA-256`) UTF-16 code-unit canonicalization,
   observation TTL, exact target/input digests, and a separate single-use
   capability grant issuer/verifier required before any mutating (`dry_run=False`)
   MCP execution (`Closes #166`).
3. Restore `wellmanifest.mcp/operation-catalog/v1` on the legacy compatibility
   branch of `registry_search(strict_v1=False)` while keeping
   `wellmanifest.mcp/registry/v1` on `strict_v1=True` and `--registry-v1`.

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_mcp_receipts.py -q` verifies input-bound
      conflict, single-flight concurrency, crash `uncertain` recovery, corruption,
      write failure, and post-cleanup read-back (`partial`/`failed`/`uncertain`).
- [x] AC-02: `pytest tests/unit/test_poa_grants.py tests/unit/test_mcp_server.py -q`
      verifies RFC 8785 canonicalization, bounded single-use grants, and fail-closed
      rejection of missing, expired, replayed, or drifted grants without touching
      real user data.
- [x] AC-03: `./project/governance-check.sh` passes with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
