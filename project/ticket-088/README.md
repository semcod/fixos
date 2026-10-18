# Ticket 088: Enable LLM-free fixos auto and autonomous repair and optimize space cleanup

- **ID**: ticket-088
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-18

## Goal and scope

Enable `fixos auto`, `fixos fix --mode autonomous`, `AutonomousSession`, and `FixOrchestrator` to run deterministically without an LLM API key or provider (`--no-llm` or automatic heuristic fallback when no LLM is configured), executing safe system diagnostics, known-bug remediations, and safe disk-space cleanups (`/tmp`, `~/.cache`, `~/.local/share/Trash`, `~/.cache/thumbnails`, JetBrains caches, disabled snap revisions, and service caches). Also optimize `_cleanup_space.py` for large `/tmp` candidate sets and shallow `gitive` workspace discovery.

## Acceptance criteria

- [x] AC-01: `fixos auto` and `fixos fix --mode autonomous` execute without an LLM API key or provider, and unit tests in `tests/unit/test_auto_no_llm.py` pass.
- [x] AC-02: `./project/governance-check.sh` passes (`GOV-PASS`).

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Execution Authorization
- SESSION_EXECUTION_AUTHORIZATION: Authorized by user to make `fixos auto` work without LLM and reclaim disk space.
