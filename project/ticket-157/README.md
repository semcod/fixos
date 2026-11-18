# Ticket 157: Harden service_cleanup_usecase guards and add Planfile sprint contract tests

- **ID**: ticket-157
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-18
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION — user requested completion and verification of all remaining FixOS backlog tasks (`#170` / `PLF-21821` and PR `#199` Validator advisory findings).

## Goal and scope

1. Enforce `-c docker-containers` mutual exclusion in `_check_docker_mode_conflicts` against `docker_all`, `docker_old`, `docker_networks`, `ollama_old`, `docker_stale_services`, and `orphaned_projects`.
2. Reject unrelated cleanup, analysis, target-space, and retention flags when `--artifacts` / `--artifacts-system-wide` / `-c artifacts` is requested in `resolve_cleanup_route`.
3. Isolate per-service exceptions and non-`Mapping` runner return values in `execute_service_cleanup` (`_invoke_service_runner`) so subsequent services still run and `outcome` (`partial` / `failed`) is reported truthfully.
4. Add `tests/unit/test_planfile_sprint_contract.py` verifying official `planfile` writer -> persisted sprint YAML -> `planfile validate schema --file-type sprint` roundtrip and SHA-256 CAS backup migration preserving existing tickets and history (`#170`).

## Acceptance criteria

- [x] AC-01: `pytest tests/unit/test_service_cleanup_usecase.py tests/unit/test_cleanup_cmd.py` passes all conflict guards and per-service exception isolation tests.
- [x] AC-02: `pytest tests/unit/test_planfile_sprint_contract.py` passes both CAS backup migration and official `planfile` writer/validator roundtrip checks.
- [x] AC-03: `./project/governance-check.sh` and `ruff check` pass with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
