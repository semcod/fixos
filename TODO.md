# TODO

Aktualna, ręcznie zweryfikowana lista zadań projektu. Zakończone pozycje są
przenoszone do sekcji `Unreleased` w [CHANGELOG.md](CHANGELOG.md), zamiast
pozostawać tutaj jako rosnąca lista zaznaczonych pól.

Ostatni przegląd: 2026-07-23.

## Aktywne

- [x] Dostarczyć [ticket-013](project/ticket-013/README.md): zachować przyjęty
  wybór optymalizacji HITL po wolnej odpowiedzi modelu, licząc timeout osobno
  dla każdej tury LLM i pokazując aktualny pozostały czas. Stan:
  `DONE / DONE`; PR #27 zatwierdzono dla dokładnego HEAD `5cd7227...` i scalono
  jako `4cc84ab...`.

- [x] Dostarczyć [ticket-012](project/ticket-012/README.md): dodać numerowane
  wybieranie pojedynczych problemów także dla odpowiedzi zawierających samą
  diagnozę oraz po każdym sukcesie odświeżać listę pozostałych optymalizacji.
  Stan: `DONE / DONE`; PR #25 zatwierdzono dla dokładnego HEAD `8d7ae075...`
  i scalono jako `94d557e...`.

- [x] Dostarczyć [ticket-011](project/ticket-011/README.md): zastąpić płaską
  listę poleceń HITL standaryzowanymi findingami, wariantami remediacji,
  zestawami komend i weryfikacją zgodną z rozdzieleniem odpowiedzialności
  `wellmanifest/logs`. Stan: `DONE / DONE`; PR #23 zatwierdzono dla dokładnego
  HEAD `ebce3b2...` i scalono jako `19c0ef6...`.

- [x] Dostarczyć [ticket-010](project/ticket-010/README.md): poprawić wykrywanie
  głównej JVM JetBrains i dodać bezpieczne sterowanie dokładnymi wtyczkami AI
  oraz helperami Qoder bez zamykania okien IDE. Stan: `DONE / DONE`; PR #20
  zatwierdzono dla dokładnego HEAD `d500e3f...` i scalono jako `f38c473...`.

- [x] Dostarczyć [ticket-009](project/ticket-009/README.md): dodać trwałe,
  zarządzalne przypięcia katalogów projektów Compose, które pozostają widoczne
  w diagnostyce, ale są chronione przed czyszczeniem osieroconych obciążeń.
  Stan: `DONE / DONE`; PR #18 zatwierdzono dla dokładnego HEAD `6643838...`
  i scalono jako `942fa1d...`.

- [x] Dostarczyć [ticket-008](project/ticket-008/README.md): udostępnić
  `fixos jetbrains doctor` z diagnostyką JVM, EDT i logów oraz opcjonalnym,
  ściśle uzasadnionym GC bez zamykania okien IDE. Stan: `DONE / DONE`; PR #16
  został zatwierdzony przez Validator App dla HEAD `98fd63d...` i scalony jako
  `d3c76d9...`.

- [x] Dostarczyć [ticket-006](project/ticket-006/README.md): opisać użycie,
  kryteria, potwierdzenia i rezultat funkcji
  `fixos cleanup --orphaned-projects`. Stan: `DONE / DONE`; PR #12 został
  zatwierdzony przez Validator App i scalony jako `db81ef8...`.

- [x] Dostarczyć [ticket-005](project/ticket-005/README.md): zawsze pokazywać
  próbkowane procesy najbardziej obciążające CPU lub RAM w `fixos quick` oraz
  zweryfikować konserwatywny przegląd usług Docker nieaktywnych od ponad trzech
  dni. Stan: `DONE / DONE`; PR #8 został zatwierdzony przez Validator App i
  scalony jako `715f961...`, a testy po merge przeszły.

- [x] Dostarczyć [ticket-004](project/ticket-004/README.md): wykrywać i jawnie
  czyścić kontenery Compose z brakującym katalogiem projektu oraz stare drzewa
  agentów IDE i serwerów developerskich, z ochroną bieżącego IDE/Codex i bez
  usuwania danych. Stan: `DONE / DONE`; PR #9 został zatwierdzony przez
  Validator App i scalony jako `6af598a...`.

- [x] Dostarczyć [ticket-002](project/ticket-002/README.md): wykrywanie świeżych
  łańcuchów procesów blokujących starsze aplikacje oraz bezpieczne, jawnie
  wybrane zamykanie drzewa z weryfikacją po wykonaniu, wraz z odzyskiwaniem
  responsywności współdzielonej JVM JetBrains bez zamykania okien. Stan:
  `DONE / DONE`; PR #6 został zatwierdzony przez Validator App i scalony jako
  `10c550c...`.

- [x] Dostarczyć [ticket-003](project/ticket-003/README.md): konserwatywnie
  wykrywać stare kontenery Docker uruchamiane automatycznie, wiązać je z
  nieaktywnymi repozytoriami Git i wyłączać autostart wyłącznie po jawnym
  wyborze, bez usuwania danych Dockera oraz udostępnić ten przepływ w menu
  `fixos cleanup`. Stan: `DONE / DONE`; PR #4 został zatwierdzony przez
  Validator App i scalony jako `085c636...`, a testy po merge przeszły.

- [x] Dostarczyć [ticket-001](project/ticket-001/README.md): przypiąć pełny
  standard `wellmanifest/new-project` v0.16.1, skonfigurować ścieżki FixOS,
  istniejący Docker i chroniony delivery Goal, a następnie potwierdzić drift,
  governance, testy oraz kontenery. Stan: `DONE / DONE`; PR #1 został scalony
  bez zmiany zatwierdzonego drzewa jako `647dd4b...`, a testy po merge przeszły.

- [x] Dostarczyć [ticket-007](project/ticket-007/README.md): wykluczyć procesy
  kontenerowe z czyszczenia procesów hosta i uzupełnić semantykę wyboru
  `critical`. Stan: `DONE / DONE`; PR #14 został zatwierdzony przez Validator
  App dla dokładnego HEAD `c525f3b...` i scalony jako `cb10227...`.
- [ ] Regenerować dokumentację API (`docs/api.md`, `docs/modules.md`,
  `docs/coverage.md` i `docs/dependency-graph.md`) w wydaniu, w którym generator
  potrafi zachować ręczne strony `docs/README.md`, `docs/getting-started.md`
  i `docs/architecture.md`.
- [ ] Dodać testy integracyjne szybkiego skanu i klasyfikacji cache na Windows
  oraz macOS. Obecne testy jednostkowe dobrze pokrywają Linux, ale nie wykonują
  prawdziwych menedżerów usług na pozostałych platformach.
- [ ] Ujednolicić formatowanie i typowanie starszych komend CLI (`scan`,
  `features`, `provider`) bez zmiany ich publicznych opcji.

## Zasady utrzymania

- Dodawaj tylko zadania, które zostały potwierdzone w aktualnym kodzie.
- Nie wpisuj tu automatycznie każdego ostrzeżenia lintera. Import względny,
  blok `if __name__ == "__main__"` albo stała liczbowa nie są same w sobie
  defektem.
- Po wykonaniu zadania usuń je z tego pliku i opisz efekt w `CHANGELOG.md`.
- Raporty narzędzi statycznych przechowuj jako artefakty CI, nie jako trwałą
  listę z numerami linii.

## Archiwum

Pliki w katalogu [TODO/](TODO/) są artykułami i historycznymi planami z marca
2026. Nie stanowią bieżącej listy zadań.
