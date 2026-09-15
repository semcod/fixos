# Ticket 032: Bezpieczny triage literowek i package cleanup

- **ID**: ticket-032
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

Wdrożyć bezpieczny triage literówek i rekomendacji czyszczenia pakietów.
Polecenia generowane przez model lub diagnostykę nie mogą rozszerzać zakresu
usuwania przez `autoremove`, globy ani podstawienia powłoki. Plan ma pokazywać
konkretne pakiety, podgląd i weryfikację; zastosowanie pozostaje po jawnym
potwierdzeniu użytkownika.

Zakres jest ograniczony do generatora komend `ask`, parsera planów HITL,
systemowego analizatora pakietów oraz ich testów. Nie wykonuje się żadnego
czyszczenia na hoście.

## Acceptance criteria

- [x] AC-01: SESSION_EXECUTION_AUTHORIZATION recorded from the user's
  request to continue and execute the work.
- [x] AC-02: Broad package cleanup is blocked until exact package inventory
  and an explicit preview/confirmation path exist.
- [x] AC-03: Diagnostics emit exact, shell-quoted package targets and never
  emit command substitution or wildcard removal commands.
- [x] AC-04: Typo/package safety and regression tests pass with no secrets in
  output.
- [ ] AC-05: Governance, stack checks, OneDev local verification and the
  protected Validator merge pass for the exact HEAD.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
