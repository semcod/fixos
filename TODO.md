# TODO

Aktualna, ręcznie zweryfikowana lista zadań projektu. Zakończone pozycje są
przenoszone do sekcji `Unreleased` w [CHANGELOG.md](CHANGELOG.md), zamiast
pozostawać tutaj jako rosnąca lista zaznaczonych pól.

Ostatni przegląd: 2026-07-23.

## Aktywne

- [ ] Dostarczyć [ticket-001](project/ticket-001/README.md): przypiąć pełny
  standard `wellmanifest/new-project` v0.16.1, skonfigurować ścieżki FixOS,
  istniejący Docker i chroniony delivery Goal, a następnie potwierdzić drift,
  governance, testy oraz kontenery. Stan: `IN_PROGRESS / PUBLICATION`.

- [ ] Uzupełnić semantykę wyboru `critical` w
  `fixos/cli/_cleanup_utils.py::_parse_selection`. Obecna funkcja nie otrzymuje
  priorytetów elementów, dlatego `critical` wybiera wszystkie pozycje.
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
