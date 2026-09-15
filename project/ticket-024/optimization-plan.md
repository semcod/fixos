# Plan działania ticket-024 — wskaźnik kanonicznego planu

Ten plik jest ograniczonym nośnikiem zakresu aktywnego ticketu. Nie duplikuje
końcowego planu przekrojowego, ponieważ `wellmanifest/docs` wymaga, aby plan
nie pozostawał wyłącznie w `project/ticket-*`.

## Kanoniczny dokument

Aktualny plan optymalizacji, audyt standardów i rejestr opublikowanych ticketów
znajdują się w:

`subactor/docs:architecture/refactoring/git-publication-throughput.md`

Link GitHub: <https://github.com/subactor/docs/blob/main/architecture/refactoring/git-publication-throughput.md>

Dokument ma metadane `wellmanifest.docs/document/v1`, jest indeksowany w
README repozytorium `subactor/docs` i pozostaje pojedynczym źródłem prawdy dla
zakresu przekrojowego. Ten plik pozostaje wskaźnikiem dla `semcod/fixos`
ticket-024 i przechowuje tylko zakres lokalny oraz decyzje potrzebne do
wykonania tego ticketu.

## Zakres lokalny

- obserwacja DNS/IP bez zapisywania sekretów;
- fail-open dla chwilowej awarii opcjonalnego resolvera przy zachowaniu
  kanonicznego hostname/SNI;
- testy regresyjne endpoint refresh;
- brak automatycznej zmiany DNS, Pleska, sekretów ani niezweryfikowanego IP;
- wynik lokalnych testów i ewentualne ograniczenia środowiska są zapisane w
  `README.md` ticketu.

## Zasady publikacji

Raport przekrojowy nie może być przechowywany tylko w `/tmp` ani w katalogu
ticketu. Publikacja organizacyjna należy do `subactor/docs` i wymaga indeksu
README; raport repozytoryjny należy do repozytorium, którego dotyczy. Jeśli
powstaje raport dowodowy, jego manifest i evidence sidecar muszą przejść
checker `wellmanifest/report`, z digestem wejść, source HEAD, zakresem,
ograniczeniami i łańcuchem dowodów.

## Walidacja

Przed zamknięciem ticketu należy uruchomić lokalny `governance-check.sh`, testy
FixOS oraz przypięty checker Docs dla kanonicznego dokumentu. Wskaźnik w tym
pliku nie jest sam w sobie dowodem publikacji, implementacji ani merge.
