# Stan autonomizacji i pozostałe prace

## Zrealizowane

- Governance `wellmanifest/new-project` 0.16.1 jest aktywne, a ticket lifecycle
  wymusza dokładny HEAD, zaufany review i dowód merge.
- Diagnostyka i remediacja FixOS działają fail-closed; anonimizacja zachowuje
  relacje danych i nie ujawnia surowych ścieżek ani identyfikatorów.
- Przepływ CI/CD wykonuje lokalne testy, bramki Docker/OneDev oraz chroniony
  Validator. Model LLM pozostaje doradczy.
- Istniejący mechanizm attestacji rozpoznaje źródła `github-review`,
  `github-app-review` i `signed-attestation`, lecz nie ustanawia jeszcze
  lokalnego SQLite jako zaufanego źródła polityki.

## Otwarte blokery

1. Registry musi publikować deterministyczny snapshot SQLite i podpisaną
   attestację zawierającą digest bazy.
2. Chroniony Validator App potrzebuje uprawnień do odczytu artefaktów oraz
   konfiguracji zaufanego issuer/predicate. Bez tego szybki relay ma działać
   fail-closed.
3. Weryfikacja musi wiązać snapshot z repozytorium, ref/HEAD i ticketem przed
   dopuszczeniem review lub merge. Do tego czasu obowiązuje JSON fallback.
4. Należy dodać lokalną usługę Registry (API/CLI + trwały wolumen) i adaptery
   synchronizacji w `subactor/registry/packages/*`; synchronizacja z GitHub,
   PyPI lub npm jest opcjonalna i nie może być wymagana w trybie offline.
5. Kontekst anonimizacji powinien być przechowywany przez cały cykl wielu tur
   HITL, z testem wycieku i testem odtworzenia po restarcie procesu.

## Zalecany przepływ docelowy

`policy source -> SQLite Registry -> checkpoint/digest -> signed attestation ->
protected Validator -> review/merge`

Każdy etap ma lokalny odpowiednik i jawny status. Błąd podpisu, issuer,
powiązania repozytorium albo digestu zatrzymuje publikację.
