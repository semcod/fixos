# Ticket 031: Fast CI preflight, failure taxonomy and actionable summary

- **ID**: ticket-031
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

Usprawnić chroniony workflow CI przez szybki preflight, fail-closed obsługę
błędów oraz jednoznaczne podsumowanie przy porażce. Zakres obejmuje wyłącznie
`.github/workflows/ci.yml`; istniejąca macierz Python pozostaje zachowana, a
preflight ma dostarczyć szybką informację przed pełnymi testami.

## Acceptance criteria

- [x] AC-01: Zakres jest autoryzowany poleceniem użytkownika `wykonaj`.
- [x] AC-02: Preflight uruchamia się przed testami w każdym runnerze macierzy
  i sprawdza checkout, instalację, kompilację oraz kolekcję testów.
- [x] AC-03: Błędy są klasyfikowane jako `CHECKOUT`, `DEPENDENCY`, `TEST`,
  `LINT` albo `INFRASTRUCTURE`, a job summary wskazuje klasę i następny krok.
- [x] AC-04: Workflow nie maskuje błędów przez `|| true`, zachowuje macierz
  Python 3.10/3.11/3.12 i przechodzi walidację governance.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

SESSION_EXECUTION_AUTHORIZATION: `wykonaj` from the human owner.

## Validation result

- YAML workflow parsed successfully and the required-check declaration still
  publishes the single protected job `test`.
- `python -m pytest -q`: `615 passed, 5 skipped, 16 deselected`.
- `./project/governance-check.sh --base origin/main --head HEAD --actor agent`:
  `GOV-PASS`.
- The implementation is ready for exact-head OneDev and Validator review.
