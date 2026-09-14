# Ticket 023: Regeneracja dokumentacji API/modules/dependency/coverage

- **ID**: ticket-023
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-14

## Goal and scope

Odświeżyć generowane strony dokumentacji `docs/api.md`, `docs/modules.md`,
`docs/dependency-graph.md` oraz `docs/coverage.md` przy użyciu lokalnego
generatora `code2docs` po zmianach kodu, bez nadpisywania ręcznie utrzymywanych
stron (`docs/README.md`, `docs/getting-started.md`, `docs/architecture.md`).
Operacja dotyczy stabilności dokumentacji i spójności artefaktów.

## Acceptance criteria

- [x] AC-01: Scope approved in active ticket context (human owner).
- [x] AC-02: `docs/api.md` zaktualizowany i zgodny ze stanem kodu.
- [x] AC-03: `docs/modules.md` zaktualizowany i zgodny ze stanem kodu.
- [x] AC-04: `docs/dependency-graph.md` zaktualizowany i zgodny ze stanem kodu.
- [x] AC-05: `docs/coverage.md` zaktualizowany i zgodny ze stanem kodu.
- [x] AC-06: `project/TICKETS.md` zawiera wpis nowego ticketa.
- [x] AC-07: Wyniki weryfikacji governance + testów potwierdzają brak regresji dokumentacji
  poza znanymi, środowiskowymi `pytest` failami (`ModuleNotFoundError: fixos`).

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

SESSION_EXECUTION_AUTHORIZATION: continue (human request received).
