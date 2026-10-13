# Dokumentacja fixOS

Ta dokumentacja dotyczy narzędzia do diagnostyki i naprawy systemu fixOS.

## Dla użytkownika

- [Pierwsze kroki](getting-started.md) — instalacja, szybka analiza i bezpieczne
  czyszczenie.
- [Konfiguracja](configuration.md) — providery LLM, tryby pracy i zmienne
  środowiskowe.
- [README projektu](../README.md) — pełna lista komend i przykładów.

## Dla programisty

- [Architektura](architecture.md) — przepływ szybkiej i pogłębionej diagnostyki.
- [API](api.md) i [moduły](modules.md) — dokumentacja generowana z kodu.
- [Graf zależności](dependency-graph.md) i [pokrycie](coverage.md) — raporty
  generowane; przed publikacją należy je odświeżyć.
- [CONTRIBUTING](CONTRIBUTING.md) — uruchamianie testów i zasady zmian.
- [TODO](../TODO.md) — wyłącznie aktywne, ręcznie zweryfikowane zadania.

## Zmiany (wellmanifest/docs v2)

- [BUGFIX: zwolnione miejsce przy hardlinkach](BUGFIX/CLEANUP_HARDLINK_FREED_SPACE.md)
  — `space_freed_gb` liczy tylko bloki zwrócone systemowi plików.
- [SERVICE: wydajność skanów](SERVICE/SCAN_PERFORMANCE.md) — budżet czasu
  `fixos quick` i jednorazowy pomiar `/tmp`.

## Ważne

Strony `api.md`, `modules.md`, `coverage.md` i `dependency-graph.md` mogą być
regenerowane automatycznie. Strony `README.md`, `getting-started.md` i
`architecture.md` są utrzymywane ręcznie i generator nie powinien ich
nadpisywać.
