# ticket-171: fix(diagnostics,tests): include XDG cache roots on Darwin/Windows and use sys.executable in rollback test

- **ID**: ticket-171
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

1. Include cross-platform XDG `~/.cache` and `~/.config` directories alongside native macOS (`~/Library/Caches`, `~/Library/Application Support`) and Windows (`%LOCALAPPDATA%`, `%APPDATA%`) roots in `fixos/diagnostics/cache_discovery.py` so CLI/Electron caches stored in XDG locations on macOS/Windows are discovered cleanly.
2. Replace `python3 -c` with `sys.executable` in `tests/e2e/test_hitl_multiturn_and_snapshot_recovery.py` so rollback execution tests run natively on Windows where `python.exe` is the active interpreter.

## Acceptance criteria

- [x] AC-01: `_resolve_platform_roots` includes `~/.cache` and `~/.config` on Darwin and Windows alongside OS-native directories, passing `tests/unit/test_cache_discovery.py` under `system_name="Darwin"` and `"Windows"`.
- [x] AC-02: `tests/e2e/test_hitl_multiturn_and_snapshot_recovery.py` invokes `sys.executable` and passes `pytest` + `ruff` + `./project/governance-check.sh`.
