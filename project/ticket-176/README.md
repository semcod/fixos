# Ticket 176: Autonomous Docker dangling/ephemeral cleanup and stale /tmp test-dir reclamation in fixos auto

- **ID**: ticket-176
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-19
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION (user requested improving `fixos auto` so it performs safe autonomous disk reclamation without manual intervention)

## Goal and scope

Expand `fixos auto` autonomous disk reclamation in strictly disjoint cleanup modules (`fixos/cli/_auto_cleanup.py`, `fixos/cli/_cleanup_free_target.py`, `fixos/cli/_cleanup_space.py`) so it autonomously reclaims:
1. Dangling (untagged, unreferenced) Docker images (`docker image prune --force`) and dangling Docker build cache (`docker builder prune --force`) in addition to the existing 7-day retained build cache prune.
2. Strictly allowlisted, 0-reference ephemeral/qualification/counterexample Docker images (never touching container-referenced images, protected tags like `approved`/`parent`/`sandbox`/`base`/`latest`/`stable`/`release`/`runtime`/`pinned`, or Docker volumes).
3. Additional regenerable package caches (`.cache/uv`, `.cache/pip`, `.cache/pre-commit`, `.cache/yarn`, `.cache/pnpm`) in `_auto_cleanup._CACHE_PATHS`.
4. Stale current-UID ephemeral test/qualification directories in `/tmp` older than 2 hours (`pytest-of-*`, `heyasa-pytest-*`, `subllm-qualify-*`, `oqllm-*`, `va077-*`, `pip-build-env-*`) during `_scan_tmp` / `fixos auto` while preserving general `/tmp` retention, other users' files, active <2h test dirs, and symlinks.

## Acceptance criteria

- [x] AC-01: `cleanup_docker_builder` in `fixos/cli/_auto_cleanup.py` autonomously prunes dangling Docker images, safe 0-ref ephemeral Docker images, dangling build cache, and retained >7d build cache while remaining dry-run safe and preserving existing `test_auto_cleanup.py` contracts.
- [x] AC-02: `_scan_tmp` in `fixos/cli/_cleanup_space.py` reclaims current-UID stale ephemeral test/qualification directories older than 2 hours while preserving <2h dirs, symlinks, other-UID dirs, and general `/tmp` retention.
- [x] AC-03: `fixos/cli/_cleanup_free_target.py` exposes `docker_remove_ephemeral_unused_images` and prunes dangling build cache in `docker_prune_dangling`.
- [x] AC-04: New regression tests in `tests/unit/test_auto_remediation.py` plus existing `tests/unit/test_auto_cleanup.py`, `tests/unit/test_cleanup_tmp.py`, `tests/unit/test_cleanup_free_target.py`, `./project/governance-check.sh --base origin/main`, and `wellman check` all pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
