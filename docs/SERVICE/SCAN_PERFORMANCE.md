---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "scan-performance",
  "kind": "service",
  "version": 1,
  "title": "fixos quick stays within its time budget and cleanup sizes /tmp in one pass",
  "status": "accepted",
  "owner": "semcod/fixos",
  "scope": "repository",
  "updated": "2026-10-13",
  "source_revision": "d168071323693191be9c786ac69a18c56928beb6",
  "priority": "P1",
  "evidence": ["https://github.com/semcod/fixos/pull/99"]
}
---

# fixos quick stays within its time budget and cleanup sizes /tmp in one pass

<!-- docs:section summary -->
## Cel i rezultat

On a loaded host (load ~65 on 16 CPUs) `fixos cleanup --list` took 110 s and
`fixos quick` 13–72 s. Measured on the same host after ticket-070:
`_scan_tmp()` over 10 102 entries 36.7 s → 0.7 s, `fixos quick` 7.6 s → 2.7 s,
with identical candidates and cache sizes.

<!-- docs:section details -->
## Zakres i rozwiązanie

- `_scan_tmp` started one `du` per stale `/tmp` entry. `_dir_sizes` now runs
  one `du -sbl0` per 512 directories; `--count-links` keeps per-directory
  results and NUL output survives any file name. Missing entries fall back to
  the per-entry measurement.
- `native_scan.measure_batch` accepts `timeout` and `python_fallback`. quick
  passes `2 × cache_timeout` and no Python walk, so a slow disk can no longer
  stretch it to minutes. Results are looked up by resolved path.
- A cache that misses the budget shows its last complete size from quick
  history with `last_complete_at`; it stays `complete: false` and is excluded
  from growth comparisons.

<!-- docs:section validation -->
## Weryfikacja

New tests in `test_cleanup_tmp.py`, `test_native_scan.py` and
`test_quick_snapshot.py`; 80 tests in the related suites and
`./project/governance-check.sh` pass (ticket-070).

<!-- docs:section risks -->
## Ryzyka i następny krok

Under extreme I/O a cache may be shown from history instead of measured.
Rollback: revert ticket-070. Next hotspot: `_discover_xdg_cache_dirs` walks all
of `~/.cache` (~34 s on the same host) and could reuse a cached measurement.
