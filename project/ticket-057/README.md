# Ticket 057: Add cleanup retention transparency and direct options

- **ID**: ticket-057
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested: "dodaj wiecej opcji czysczenia w fixos, aby było transaprentne co mozna czyscic bezposrednio i z jaka retencja, np 24h dla /tmp".
Add more direct cleanup options in `fixos cleanup` (`--trash`, `--thumbnails`, `--retention` parsing for human durations like `24h`, `7d`, `48h`), provide a transparent policy matrix (`--policy` / `--retention-policy`) displaying what can be cleaned directly, default retention, risk levels, protected assets, and CLI examples, and integrate safe age-based trash and thumbnail cleanups.

## Acceptance criteria

- [x] AC-01: Add duration parsing (`parse_retention_days`) supporting strings like `24h`, `12h`, `1d`, `7d`, `30d` via `--retention` option in `fixos cleanup`.
- [x] AC-02: Add `--trash` direct cleanup option with retention support (e.g. items older than retention in `~/.local/share/Trash`).
- [x] AC-03: Add `--thumbnails` direct cleanup option with retention support for thumbnail cache (`~/.cache/thumbnails`).
- [x] AC-04: Add `--policy` / `--retention-policy` flag to output a transparent matrix of cleanup targets, direct availability, retention defaults, risk level, and CLI usage.
- [x] AC-05: Unit tests in `tests/unit/test_cleanup_retention.py` and governance checks pass with 0 errors.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
