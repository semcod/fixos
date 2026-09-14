# Ticket 024: Odświeżanie konfiguracji endpointów po zmianie DNS lub IP

- **ID**: ticket-024
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-09-14

## Goal and scope

Zapewnić autonomiczne odświeżanie danych o endpointach, gdy zewnętrzny
serwer zmieni adres IP. FixOS obserwuje DNS skonfigurowanego endpointu przy
ładowaniu konfiguracji, utrzymuje nietajny snapshot wyłącznie w pamięci procesu
i pokazuje zmianę lub chwilową awarię DNS. Hostname pozostaje kanoniczną wartością
URL, dzięki czemu klient zachowuje prawidłowe TLS/SNI.

Rozwiązanie nie zapisuje cache'u endpointów ani sekretów na dysku. Zakres nie obejmuje zmiany rekordów DNS, konfiguracji Pleska, sekretów,
automatycznego przełączania na niezweryfikowane adresy IP ani aktywnego
health-checku usługi.

## Acceptance criteria

- [x] AC-01: Scope is approved by the user's execution request (`kontynuuj`).
- [x] AC-02: Resolver and process-local cache tests pass; transient DNS failure is fail-open
  for the existing configured endpoint and no secret is persisted.
- [x] AC-03: Managed governance check passes and the endpoint-refresh tests
  pass. The current host suite is `597 passed, 5 skipped, 6 failed, 16
  deselected`; all six failures are pre-existing environment/dependency
  failures outside endpoint refresh (two global-entrypoint import failures and
  four Click typo-handling failures).

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

SESSION_EXECUTION_AUTHORIZATION: `kontynuuj` from the human owner.
