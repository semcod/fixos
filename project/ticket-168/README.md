# ticket-168: feat(diagnostics): cross-platform Windows and macOS quick scan, cache classification, and lock portability

- **ID**: ticket-168
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

1. Extend `fixos/diagnostics/quick_snapshot.py` and `fixos/diagnostics/cache_discovery.py` with native Windows (`%LOCALAPPDATA%`, `%APPDATA%`, backslash/drive-letter safe path coverage) and macOS (`~/Library/Caches`, `~/Library/Application Support`) cache rules, Electron cache discovery, and safe-vs-review classification without misclassifying non-cache user data.
2. Make POSIX-specific lock/fsync/signal modules (`fixos/mcp_receipts.py`, `fixos/poa_grants.py`, `fixos/agent/autonomous_session.py`) portable on native Windows (`msvcrt` byte-range lock fallback when `fcntl` is absent, Windows-safe directory fsync skip, `platform_utils` signal timeout wrapper).
3. Add integration tests (`tests/e2e/test_cross_platform_quick_cache.py`) exercising live host quick scan + cache classification + CLI `fixos quick --json` + MCP/POA locking as well as native Windows and macOS directory layouts.

## Acceptance criteria

- [x] AC-01: `collect_quick_snapshot` and `discover_additional_caches` classify rebuildable caches (`safe`) versus review-only caches (`review`) accurately across Linux, macOS (`~/Library/Caches`, `~/Library/Application Support`), and Windows (`%LOCALAPPDATA%`, `%APPDATA%`) layouts without selecting arbitrary user data directories.
- [x] AC-02: `mcp_receipts`, `poa_grants`, and `autonomous_session` import and execute cleanly when `fcntl` or `SIGALRM` are absent (native Windows portability).
- [x] AC-03: `tests/e2e/test_cross_platform_quick_cache.py` and existing quick/cache/MCP/POA suites pass with zero lint or governance errors.
