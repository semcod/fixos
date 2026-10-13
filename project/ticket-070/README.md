# Ticket 070: faster cleanup and quick scans: batch tmp du, honor quick time budget

- **ID**: ticket-070
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-13

## Goal and scope

Profiled on a loaded host (load ~65 on 16 CPUs) on 2026-10-13:

- `fixos cleanup --list`: 110 s, of which 54 s were 9 752 separate `du`
  processes in `_scan_tmp` (one per stale `/tmp` entry).
- `fixos quick`: 13–72 s although it promises seconds; 92 % was
  `native_scan.measure_batch` with a 120 s limit and an unbounded Python
  fallback, ignoring quick's 1.5 s cache budget.

Changes: `_dir_sizes` measures stale `/tmp` directories with one
`du -sbl0` per 512 entries (per-entry fallback kept); `measure_batch` takes
`timeout` and `python_fallback`; quick uses `2 × cache_timeout` without the
Python walk and shows the last complete history size for caches that missed
the budget (still `complete: false`, excluded from growth).

SESSION_EXECUTION_AUTHORIZATION: user requested faster task execution in fixos ("popraw, aby na przyszlosc szybciej realizowal zadania").

## Acceptance criteria

- [x] AC-01: tests prove one `du` process for many stale directories, a bounded native batch without Python fallback, and history fill for timed-out caches.
- [x] AC-02: related quick/cleanup suites and `./project/governance-check.sh` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.

## Evidence (same host, load ~40–48, 2026-10-13)

| | main `fcef9db` | ticket-070 |
|---|---|---|
| `_scan_tmp()` (10 102 entries, 511.8 MB) | 36.7 s | 0.7 s |
| `fixos quick --no-save` | 7.6 s (7 450 ms) | 2.7 s (1 721 ms) |

Both runs returned identical candidates/bytes and complete cache sizes.
