# TODO

Aktualna, ręcznie zweryfikowana lista zadań projektu. Zakończone pozycje są
przenoszone do sekcji `Unreleased` / wydań w [CHANGELOG.md](CHANGELOG.md),
zamiast pozostawać tutaj jako rosnąca lista zaznaczonych pól.

Ostatni przegląd: 2026-11-19.

## Aktywne i zablokowane zewnętrznie

- [ ] Odblokować i dokończyć poprawkę uprawnień plików regularnych w `_remove_tree`
  (`#206` / `PLF-21827` / `ticket-161`). Stan: `BLOCKED` na zewnętrznym właścicielu
  `subactor/coding-agent#322` (`_prior_project_attempt` pod projekcją statusu `0.20.162`).
- [ ] Dodać testy integracyjne szybkiego skanu i klasyfikacji cache na natywnych
  środowiskach Windows oraz macOS (obecna macierz CI weryfikuje Python 3.10–3.12
  oraz 5 dystrybucji Linux w kontenerach).
- [ ] Ujednolicić formatowanie i typowanie starszych komend CLI (`scan`,
  `features`, `provider`) bez zmiany ich publicznych opcji.
- [ ] Utrzymywać kontekst anonimizacji przez wiele tur HITL oraz dodać testy
  integracyjne cyklu życia snapshotu, podpisu i odtworzenia po awarii.

## Zasady utrzymania

- Dodawaj tylko zadania, które zostały potwierdzone w aktualnym kodzie lub aktywnym rejestrze zgłoszeń.
- Nie wpisuj tu automatycznie każdego ostrzeżenia lintera. Import względny,
  blok `if __name__ == "__main__"` albo stała liczbowa nie są same w sobie
  defektem.
- Po wykonaniu zadania usuń je z tego pliku i opisz efekt w `CHANGELOG.md`.
- Zadania należące do zewnętrznych repozytoriów (`subactor/registry`, `heyasa/heyasa`,
  `semcod/planfile`, `subactor/coding-agent`) śledź w ich repozytoriach właścicielskich.

## Archiwum

Pliki w katalogu [TODO/](TODO/) są artykułami i historycznymi planami z marca
2026. Nie stanowią bieżącej listy zadań.
