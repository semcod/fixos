# Ticket 154: Extract cleanup_services use cases and add POA/MCP/NL runtime canary

- **ID**: ticket-154
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested execution of
  backlog tasks for `semcod/fixos` (`#169` / `PLF-21820` and `#168` / `PLF-21819`).

## Goal and scope

1. Extract deterministic route validation (`resolve_cleanup_route`), service cleanup
   planning (`plan_service_cleanup`), consent-gated execution (`execute_service_cleanup`),
   and post-cleanup read-back (`verify_service_cleanup_readback`) into
   `fixos/core/service_cleanup_usecase.py`, reducing `cleanup_services` cyclomatic
   complexity from `98` to `< 10` while preserving all safety guards and CLI behavior
   (`Closes #169`).
2. Add `fixos/poa_canary.py` and `tests/unit/test_wellman_canary.py` to execute
   isolated end-to-end MCP handshake, `urn:uuid:` resource read-back, NL-to-URI
   negative guards, POA ungranted mutation blocking, idempotency conflict checks,
   and FastMCP AST hygiene, reporting manifest declaration (`proves_runtime_s5=False`),
   static checkers, and observed runtime canary separately (`#168`).
3. Harden `fixos/nl_router.py` `validate_nl_plan_envelope` to reject unknown or
   inconsistent fields and reconstruct canonical envelopes from `OperationSpec`, and
   include English `project` in project-disk disambiguation.

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_service_cleanup_usecase.py` + all 16 cleanup test
      suites verify success, partial failure, declined consent, post-cleanup read-back,
      and `cleanup_services` CC < 20.
- [x] AC-02: `pytest tests/unit/test_wellman_canary.py tests/unit/test_nl_router.py`
      verifies runtime canary separation and closed NL-plan validation.
- [x] AC-03: `./project/governance-check.sh` passes with 0 errors and `code2llm`/CC +
      latency measurements are recorded (`cleanup_services` CC `98 -> 3`, max helper CC
      `<= 25` in `service_cleanup_usecase.py`, `resolve_cleanup_route` p50 `0.022 ms` /
      p95 `0.051 ms`, `plan+execute+readback` p50 `0.019 ms` / p95 `0.039 ms`,
      `run_conformance_and_runtime_canary` `7.77 s`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
