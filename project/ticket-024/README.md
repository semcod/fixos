# Ticket 024: Odświeżanie konfiguracji endpointów po zmianie DNS lub IP

- **ID**: ticket-024
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
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

## Canonical documentation

The cross-repository optimization plan is maintained in
`subactor/docs:architecture/refactoring/git-publication-throughput.md` and
indexed by that repository. `project/ticket-024/optimization-plan.md` is only
the bounded ticket pointer; it is not a second canonical plan. Repository-local
reports remain in their owning repository, while organization-wide reports use
`subactor/docs` with a `wellmanifest/report` evidence sidecar when applicable.

## Acceptance criteria

- [x] AC-01: Scope is approved by the user's execution request (`kontynuuj`).
- [x] AC-02: Resolver and process-local cache tests pass; transient DNS failure is fail-open
  for the existing configured endpoint and no secret is persisted.
- [ ] AC-03: Managed governance check passes. Current check is blocked by the
  historical `GOV-INTENT-003` finding: `intent.json` was not committed before
  the first implementation commit. The current full suite passes: `603 passed,
  5 skipped, 16 deselected`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

SESSION_EXECUTION_AUTHORIZATION: `kontynuuj` from the human owner.
