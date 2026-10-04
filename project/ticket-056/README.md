# Ticket 056: Add tmp cleanup option and safe defaults integration to fixos cleanup

- **ID**: ticket-056
- **Owner**: agent:gemini
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-10-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requested: "wyczyssc wsyztsko z tmp co jest starrsze niz 1 dzien i dodaj taka funkojcjonalnsoc w biblitece fixos" and "zaktualizuj fixos, aby realizowal takie czysczenie as default bezpieczne".
Add `--tmp` functionality to `fixos cleanup` CLI command to clean files and directories in `/tmp` older than `--days` (default 1 day), protecting system sockets, locks and system directories like `.X11-unix`. Integrate `/tmp` stale file cleanup and Docker buildx builder cache cleanup into the default safe cleanup plan (`fixos cleanup --yes`, `ServiceCleaner.build_safe_age_actions`), and support `--threshold-gb`.

## Acceptance criteria

- [x] AC-01: `--tmp` CLI option cleans or lists items in `/tmp` older than `--days`.
- [x] AC-02: System sockets and locks (`.X11-unix`, `.ICE-unix`, `.X*-lock`, etc.) are protected.
- [x] AC-03: Stale `/tmp` (>1 day) and Docker buildx builder cache are integrated into default safe cleanup (`safe_to_cleanup` / `--yes`).
- [x] AC-04: Supports `--threshold-gb` in `fixos cleanup`.
- [x] AC-05: Unit tests and governance check pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
