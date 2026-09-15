# Ticket 026: Harden endpoint observation contract and publish optimization plan

- **ID**: ticket-026
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

Uzupełnić materialny kontrakt obserwacji endpointów FixOS: URL zawierający
poświadczenia ma zostać odrzucony przed resolverem DNS, a lokalny magazyn
obserwacji ma pozostać pusty. Ticket publikuje także bounded plan optymalizacji
powiązany z wcześniejszym wdrożeniem ticket-024.

## Acceptance criteria

- [x] AC-01: Zakres jest autoryzowany przez użytkownika poleceniem
  `kontynuuj, wypchnij, scal`.
- [x] AC-02: Test potwierdza odrzucenie URL z poświadczeniami przed DNS oraz
  brak zapisu obserwacji.
- [ ] AC-03: Governance, checki CI i chroniony Validator przechodzą dla
  exact HEAD.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

SESSION_EXECUTION_AUTHORIZATION: `kontynuuj, wypchnij, scal` from the human owner.
