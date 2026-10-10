# Ticket 062: optimize project scanner disk analyzer and quick snapshot with rust

- **ID**: ticket-062
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-10
- **Authority**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

Accelerate directory and cache diagnostics in `project_scanner.py`, `disk_analyzer.py`, and `quick_snapshot.py` by delegating filesystem sizing and file counts to Rust `fixos-native` (`measure_tree` / `measure_batch`) with transparent, fail-closed Python fallbacks.

## Acceptance criteria

- [ ] AC-01: `project_scanner.py` utilizes native measurements to replace slow sequential `du` subprocesses.
- [ ] AC-02: `disk_analyzer.py` uses `measure_tree` to acquire byte sizes and file counts without spawning `du` or `find`.
- [ ] AC-03: `quick_snapshot.py` measures cache locations with `measure_batch` when available.
- [ ] AC-04: Unit tests and `./project/governance-check.sh` pass with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

