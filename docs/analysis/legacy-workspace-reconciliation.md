---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "legacy-workspace-reconciliation",
  "kind": "analysis",
  "version": 4,
  "title": "Uzgodnienie starej kwarantanny i gałęzi backupowej Fixos",
  "status": "implemented",
  "owner": "semcod/fixos",
  "scope": "repository",
  "created": "2026-11-04",
  "updated": "2026-11-19",
  "review_after": "2026-12-19",
  "source_revision": "dbe080ac4d15980f160d501365c882fc17e4662d",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/pull/141",
    "https://github.com/semcod/fixos/pull/144",
    "https://github.com/semcod/fixos/pull/181",
    "https://github.com/semcod/fixos/issues/174",
    "https://github.com/wellmanifest/new-project/pull/576",
    "https://github.com/wellmanifest/new-project/issues/575",
    "https://github.com/subactor/autonom/pull/203"
  ]
}
---

# Uzgodnienie starej kwarantanny i gałęzi backupowej Fixos

<!-- docs:section question -->
## Pytanie

Czy kwarantanna PLF-20296 oraz gałąź `ticket/110-sync-standard-requirements-backup`
zawierają jeszcze potrzebną pracę i jak wykonać autoryzowaną przez właściciela
dyspozycję `archive-and-retire` bez utraty danych ani naruszenia cudzego lease?

<!-- docs:section scope -->
## Zakres

Zamknięcie `semcod/fixos#174` (`PLF-21812`). Pierwotny punkt odniesienia analizy:
`main` w `ff91710a60a19ba3aab96f87c506aa5a806e4aeb` (Fixos 2.3.0) oraz
`5ccc2a927f94054abce1563930dd24b151ca4bdb`; finalna dyspozycja i weryfikacja
przeprowadzone na bazie `da0ea36a101b3444fd6020c79f0ac0c5527e81be` (Fixos 2.7.1,
`wellmanifest/new-project` `0.20.162`). Źródło gałęzi backupowej:
`1e4d4d364c613aeabc8b3c7ab0c229e5cc008d60`. Archiwum kwarantanny odpowiada
odłączonemu worktree na `f787fa4192b39fffd79aa781469dff405f640406`
(`/home/tom/github/subactor/.worktrees/.quarantine/PLF-20296-20261026T113356Z`).
Właścicielem repozytorium jest `semcod/fixos`.

<!-- docs:section method -->
## Metoda

Odczytano komplet obu wersji intentów i kryteriów, źródła na przypiętych
commitach, rejestr terminalnych receiptów, stary lease oraz odpowiedzi GitHub.
Porównano treść, historię i `git patch-id --stable`. Prywatne kopie odtworzono
i zweryfikowano kryptograficznie (SHA-256) przed wykonaniem dyspozycji
właściciela. Wszystkie pliki `.subactor/leases/*.json` pozostały nienaruszone.

<!-- docs:section evidence -->
## Dowody i odzyskiwanie

- GitHub potwierdza scalenie `PR #141` (`2a2287d7...` -> `a2930fc3...`, `#133`
  zamknięte) oraz `PR #144` (`5a59ecca...` -> `da980fac...`).
- Plik `.governance/standard-requirements.json` z backupu i `main` ma identyczny
  skrót SHA-256 `ed470a723ba2d5e1545211f8f308d75dfd63a74a9086d65eee2a02fe936f196d`
  oraz ten sam stabilny `patch-id` `0e1708f56226018e8882e8e3999f2557341d99c8`.
- Bundle `legacy-commits.bundle` (21 587 371 B, SHA-256
  `f0513d1699829c325fc2fbe8649939f131f7a9a7112e5b5cdc34312270680dd5`) oraz pełne
  archiwum kwarantanny (4 118 959 B, SHA-256
  `c3a9c10a79470494fc98ce1883de51bc1760f22dae9e00a398e2234dc56c6ba1`, manifest
  `d2c8ce725c027c13f71d0b5b69ac7e141d0c7aabbdbfefba75e68add3a4c5ea7`) zostały
  ponownie zweryfikowane 2026-11-18 przed wycofaniem refa backupowego.
- Upstreamowa zależność standardu `NP-028` została dostarczona w
  `wellmanifest/new-project#576` (`head: 2df1a1f30a31591661584f2eb8c946a198c73fe1`,
  `merge: de22d44bd692cfac3721f567d587c57390b04ebf`, zatwierdzone przez
  `ifuri-validator-agent` w review `PRR_kwDOTfEh7M8AAAABWLH84A`), a powiązane
  zgłoszenie `wellmanifest/new-project#575` zostało zamknięte.
- Scalony worktree `.worktrees/ticket-138--truthful-partial-removal` (`semcod/fixos#181`,
  `2dbc5c68...` -> `63d64149...`, review `PRR_kwDORTIK388AAAABYUaBsA`, 0 brudnych
  plików, 0 otwartych procesów) został czysto wyrejestrowany.
- Po jawnej decyzji właściciela z 2026-11-18 (`archive-and-retire`) zapisano
  trwały receipt `.subactor/recovery/legacy-retirement-20261104/user-disposition-20261118.json`
  i wycofano lokalny ref `refs/heads/ticket/110-sync-standard-requirements-backup`
  (`1e4d4d364c613aeabc8b3c7ab0c229e5cc008d60`), zachowując pełną odtwarzalność z bundle.

<!-- docs:section facts -->
## Uzgodnienie kryteriów

| Źródło i kryterium | Ocena na `main` | Dowód lub granica |
| --- | --- | --- |
| Backup `ticket-110`, AC-01: synchronizacja wymagań baseline i zależności przechodnich. | Implemented & retired (`archive-and-retire`). | Identyczne bajty `.governance/standard-requirements.json`, ten sam `patch-id`, scalone `PR #144`, trwały bundle i receipt dyspozycji właściciela. |
| Właściwy `ticket-109`, AC-01..AC-03 (`#133` / `PLF-20296`). | Implemented (`PR #141`). | Scalony kod i 15 testów `test_quick_snapshot.py` PASS. |
| Kwarantanna `PLF-20296` i stary lease v1 `ticket-109--coding-agent-plf-20296.json`. | Archived read-only. | Pełne archiwum tar+manifest zweryfikowane SHA-256; plik lease zachowany bez fabrykowania pól v5. |

<!-- docs:section hypotheses -->
## Hipotezy zweryfikowane

Hipoteza, że gałąź `ticket/110-sync-standard-requirements-backup` zawiera
niescalone zmiany merytoryczne względem `main`, została obalona przez identyczny
skrót SHA-256 docelowego pliku wymagań oraz identyczny `git patch-id --stable`
po scaleniu `PR #144`. Hipoteza, że zwykły merge starego commitu `1e4d4d3`
przejdzie bramkę `GOV-INTENT-003`, została również odrzucona eksperymentalnie,
dlatego zastosowano jawnie autoryzowaną przez właściciela procedurę
`archive-and-retire` z zachowaniem pełnego bundle odzyskiwania.

<!-- docs:section limitations -->
## Granice i zachowane ograniczenia

Stary plik `.subactor/leases/ticket-109--coding-agent-plf-20296.json`
(`wellmanifest.worktree-lease/v1`) pozostaje nienaruszony jako historyczny dowód
operacyjny; nie dopisano do niego syntetycznych pól `fencingToken` ani
`leaseRevision`. Surowe archiwa odzyskiwania pozostają poza Git w prywatnym
katalogu `.subactor/recovery/`.

<!-- docs:section recommendations -->
## Zrealizowana dyspozycja

Wszystkie kroki wymagane do zamknięcia `#174` (`PLF-21812`) zostały wykonane:
potwierdzono niezależne scalenie `wellmanifest/new-project#576`, zamknięto `#575`,
ponownie zweryfikowano skróty SHA-256 wszystkich kopii ratunkowych, zapisano
trwały receipt decyzji właściciela `archive-and-retire`, usunięto nadmiarowy ref
`refs/heads/ticket/110-sync-standard-requirements-backup` oraz wyrejestrowano
czysto scalony worktree `ticket-138`.

<!-- docs:section next_actions -->
## Następne kroki operatora

Brak otwartych działań naprawczych dla `#174` (`PLF-21812`). Prywatne kopie w
`.subactor/recovery/legacy-reconciliation-20261104/` oraz
`.subactor/recovery/legacy-retirement-20261104/` pozostają zachowane do celów
audytowych.

<!-- docs:section history -->
## Historia

- Wersja 1: analiza na `ff91710`, ticket-129, pełne AC i odtworzone kopie;
  opublikowana jako merge `9510293`.
- Wersja 2: potwierdzenie zakończenia pracy przez użytkownika, wdrożony
  obserwator z `PR #203` oraz uzgodnienie zawartości backupu w ticket-131.
- Wersja 3: doprecyzowanie ticket-132 na bazie `5ccc2a9` z pełnym archiwum
  kwarantanny.
- Wersja 4: wykonanie autoryzowanej przez właściciela dyspozycji
  `archive-and-retire` (2026-11-18/19), zamknięcie `wellmanifest/new-project#575`,
  wyrejestrowanie scalonego `ticket-138` i zamknięcie `semcod/fixos#174` (`PLF-21812`).
