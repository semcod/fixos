# Ticket 106: Expand additional_cache_candidates and quick_snapshot CACHE_RULES for developer caches

- **ID**: ticket-106
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

Expand `_CACHE_PATHS` in `fixos/cli/_auto_cleanup.py` and `CACHE_RULES` in `fixos/diagnostics/quick_snapshot.py` to cover regenerable developer caches (`.cache/go-build`, `.cache/ruff`, `.cache/mypy`, `.cache/Flake8`, `.cache/black`, and `~/.cache/pnpm`) while ensuring strict protections against symlinks, nested mounts, browser profiles, and model weights (`.cache/huggingface`). Unit tests in `tests/unit/test_auto_cleanup.py` verify that developer caches are reclaimed and protected paths remain untouched.

## Acceptance criteria

- [x] AC-01: Add safe regenerable developer cache leaves (`.cache/go-build`, `.cache/ruff`, `.cache/mypy`, `.cache/Flake8`, `.cache/black`) to `_CACHE_PATHS` in `fixos/cli/_auto_cleanup.py` preserving strict `cache_path_allowed` guards.
- [x] AC-02: Align `CACHE_RULES` in `fixos/diagnostics/quick_snapshot.py` so `go-build` and Python linter/typecheck caches are reflected in `safe_reclaim` estimates.
- [x] AC-03: Unit tests in `tests/unit/test_auto_cleanup.py` verify that new regenerable developer caches are cleaned and protected paths (models, browser data) remain untouched.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
