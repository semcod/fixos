# Ticket 034: Default cleanup proposes Docker containers and images

- **ID**: ticket-034
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-17

## Goal and scope

`fixos cleanup` (no flags) must propose removal of stopped Docker containers
and unused Docker images in its default interactive plan. Today the plan only
surfaces unused images/build cache and orphaned networks; stopped containers
are never proposed. SESSION_EXECUTION_AUTHORIZATION: the user asked for this
behavior to be the default without any flag.

Scope: extend `build_safe_age_actions` with a `docker-containers` safe action
(`docker container prune --force`), add `ServiceCleaner.cleanup_docker_containers`,
dispatch it in `_execute_planned_cleanup`, expose `-c docker-containers`, and
cover the safety boundary in `tests/unit/test_cleanup_safety.py`.

## Acceptance criteria

- [x] AC-01: Default plan lists a Docker stopped-containers action when
  `docker system df` reports reclaimable container space.
- [x] AC-02: The action runs only `docker container prune --force`; running
  containers, images, networks and volumes are untouched.
- [x] AC-03: `--dry-run` and `--json` cover the new action; no destructive
  command executes under dry-run.
- [x] AC-04: `-c docker-containers` runs the bounded operation on its own.
- [x] AC-05: `python -m pytest -q tests/unit/test_cleanup_safety.py` and
  `./project/governance-check.sh` pass.

## Validation evidence

- `python -m pytest -q tests/unit/test_cleanup_safety.py` — 21 passed
  (5 new `TestDockerDefaultProposal` cases).
- `python -m pytest -q tests/unit/test_cleanup_cmd.py tests/unit/test_service_cleanup.py`
  — passed, no regressions.
- `./project/governance-check.sh` — GOV-PASS.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
