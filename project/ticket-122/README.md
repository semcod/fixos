# Ticket 122: Enhance autonomous disk remediation for subactor caches and stale IDE version data

- **ID**: ticket-122
- **Owner**: agent:agent-antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-04

## Goal and scope

Rozszerzenie autonomicznych mechanizmów zwalniania miejsca na dysku w `fixos auto` i `fixos cleanup`:
1. Dodanie regenerowalnych pamięci podręcznych Subactor (`.cache/subactor-search`, `virt-builder`, `tree-sitter-language-pack`, `google-chrome-headless`) do bezpiecznej listy `_USER_CACHE_SAFE` oraz `_CACHE_PATHS`.
2. Dołączenie czyszczenia regenerowalnych pamięci kompilatorów i repozytoriów (`.cargo/registry/cache`, `.android/build-cache`) do `_cleanup_build_caches`.
3. Automatyczne dołączanie wyłączonych starych rewizji snap (`--snap-old`) podczas wywołania `fixos auto --services` przy dostępności `snap` w systemie.
4. Pokrycie zmian testami jednostkowymi i pomyślne przejście bramki `./project/governance-check.sh`.

## Acceptance criteria

- [x] AC-01: Rozszerzenie `_USER_CACHE_SAFE` i `_CACHE_PATHS` o regenerowalne cache subactor i narzędzi developerskich.
- [x] AC-02: Rozszerzenie `_cleanup_build_caches` o bezpieczne cache cargo/android.
- [x] AC-03: Włączenie obsługi wyłączonych rewizji snap w trybie `auto --services`.
- [x] AC-04: Wszystkie testy jednostkowe `tests/unit/test_cleanup_space.py` przechodzą na zielono.
- [x] AC-05: Pomyślne przejście bramki `./project/governance-check.sh`.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
