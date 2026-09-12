# Ticket 021: Ustabilizować launcher CLI w testach e2e

- **ID**: ticket-021
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-12

## Goal and scope

Testy e2e CLI nie powinny wybierać przypadkowego globalnego launchera
`fixos`, gdy uruchomiono je w środowisku virtualenv repozytorium. Fixture ma
preferować executable znajdujący się obok `sys.executable`, a dopiero potem
szukać go w `PATH`.

## Acceptance criteria

- [x] AC-01: Zakres autoryzowany żądaniem użytkownika „kontynuuj, merguj,
  testuj” z 2026-09-12 (`SESSION_EXECUTION_AUTHORIZATION`).
- [x] AC-02: Testy CLI e2e przechodzą z launcherem aktywnego interpretera.
- [x] AC-03: Governance i pełny suite przechodzą na exact HEAD `ded18b7...`;
  wynik: 596 passed, 5 skipped, 16 deselected.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
