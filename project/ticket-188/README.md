# Ticket 188: Harden native batch and directory scan completeness contract

- **ID**: ticket-188
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-27

## Goal and scope

Address `semcod/fixos#249` (`PLF-21842`) by hardening `measure_batch`, `scan_dir_native`, and `measure_tree` validation in `fixos/diagnostics/native_scan.py` and error/completeness propagation in `fixos/diagnostics/quick_snapshot.py` against silent missing paths, malformed JSON/records, permission and child/root errors, unsupported CLI invocations (like `fixos-native` HEAD without `batch-measure`/`scan-dir`), non-empty `exclude`, and timeouts.

## Acceptance criteria

- [x] AC-01: `measure_batch` validates every native record against requested resolved paths, rejects malformed payloads/bool counts/extra keys, skips native when `exclude` is non-empty, falls back per missing path when `python_fallback=True`, and never fabricates empty records when `python_fallback=False`.
- [x] AC-02: `scan_dir_native` verifies root and child readability and rejects malformed responses, mismatched `path`/`base`, root errors, silently dropped subdirs, or unreadable omitted child dirs by returning `None` instead of fabricated empty results.
- [x] AC-03: `quick_snapshot._measure_caches` propagates per-path native `errors` / `complete=False` flags into item completeness and falls back to `du` only for unresolved paths.
- [x] AC-04: Contract tests in `tests/unit/test_native_scan.py` and `tests/unit/test_quick_snapshot.py`, full unit suite, and `./project/governance-check.sh --base main` pass.

## Tracking boundary

This directory contains the minimal reviewed intent and acceptance criteria for `semcod/fixos#249`.
