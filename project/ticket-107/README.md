# Ticket 107: Accelerate DevProjectAnalyzer and DiskAnalyzer with fixos-native measurement and 7d activity checks

- **ID**: ticket-107
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-26

## Goal and scope

Accelerate `DevProjectAnalyzer` and `DiskAnalyzer` by using fixos-native measurement (`measure_tree` / `measure_batch`) with bounded fallbacks, checking recent project git and source activity for last modified time, replacing unbounded `rglob('*')` walks in `DiskAnalyzer` with bounded `os.walk` and native scan, and aligning dependency staleness reporting with `DEV_PROJECT_OLD_DAYS` (7 days).

## Acceptance criteria

- [ ] AC-01: `DevProjectAnalyzer._get_dir_size` uses `fixos.diagnostics.native_scan.measure_tree` first with bounded fallback, and `_get_last_modified` checks native scan, git activity, and project source files.
- [ ] AC-02: `DevProjectAnalyzer.get_summary()` replaces hardcoded 30-day threshold with `DEV_PROJECT_OLD_DAYS` (7 days) for staleness labeling.
- [ ] AC-03: `DiskAnalyzer._get_oldest_file_date` and `DiskAnalyzer._get_newest_file_date` replace unbounded `rglob('*')` with native `measure_tree` and bounded `os.walk` to prevent stalling on deep log directories.
- [ ] AC-04: Unit regression tests verify native scan integration, bounded log walk execution, and 7-day staleness reporting.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
