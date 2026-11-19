# ticket-174: fix(diagnostics,tests): skip Windows NTFS junctions and normalize expanded cache roots

- **ID**: ticket-174
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-11-19

## Goal and scope

1. Skip Windows NTFS compatibility junctions (`os.path.isjunction`) and legacy Windows directory aliases (`Application Data`, `Temporary Internet Files`, `History`) as well as known package caches (`pip`, `uv`, etc.) during generic and Electron cache discovery in `fixos/diagnostics/cache_discovery.py`, and normalize `os.path.expanduser` roots via `os.path.normpath` so mixed-separator paths never occur on Windows.
2. Isolate `USERPROFILE`, `LOCALAPPDATA`, and `APPDATA` in `tests/unit/test_cache_discovery.py` and add coverage for NTFS junctions and legacy Windows directory aliases.

## Acceptance criteria

- [x] AC-01: `cache_discovery.py` normalizes expanded roots, skips NTFS junctions (`_is_link_or_junction`), and excludes Windows legacy directory aliases (`Application Data`, `Temporary Internet Files`, `History`) and package caches from Electron classification.
- [x] AC-02: `tests/unit/test_cache_discovery.py` and `tests/e2e/test_cross_platform_quick_cache.py` pass cleanly under `pytest` + `ruff` + `./project/governance-check.sh`.
