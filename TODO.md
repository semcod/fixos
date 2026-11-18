# TODO

Aktualna, ręcznie zweryfikowana lista zadań projektu. Zakończone pozycje są
przenoszone do sekcji `Unreleased` / wydań w [CHANGELOG.md](CHANGELOG.md),
zamiast pozostawać tutaj jako rosnąca lista zaznaczonych pól.

Ostatni przegląd: 2026-11-18.

## Aktywne i zablokowane zewnętrznie

- [ ] Uzgodnić zachowany historyczny backup `refs/heads/ticket/110-sync-standard-requirements-backup`
  oraz kwarantannę `ticket-109` (`#174` / `PLF-21812`). Stan: `BLOCKED` — `wellmanifest/new-project#576`
  scalono (`de22d44`), nadal wymagane domknięcie `wellmanifest/new-project#575`, jawna decyzja
  właściciela (`archive-and-retire`) oraz dzierżawa `STARTER-029` przed dotknięciem
  `.subactor/leases/` lub `.governance/standard-requirements.json`.
- [ ] Potwierdzić end-to-end pobranie zadania `semcod/fixos` przez centralny indeks Heyasa
  (`#171` / `PLF-21822`). Stan: `BLOCKED` na zewnętrznym właścicielu `heyasa/heyasa#891`
  (skaner `fleet_backlog` czyta wyłącznie `current.yaml` z pominięciem `backlog.yaml`,
  a endpoint `127.0.0.1:18769/tickets/discovery` zwraca `HTTP 503 ticket_index_stale`).
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
  `semcod/planfile`) śledź w ich repozytoriach właścicielskich.

## Archiwum

Pliki w katalogu [TODO/](TODO/) są artykułami i historycznymi planami z marca
2026. Nie stanowią bieżącej listy zadań.
