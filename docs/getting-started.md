# Pierwsze kroki z fixOS

fixOS diagnozuje zasoby komputera, wskazuje bezpieczne cache do usunięcia i,
opcjonalnie, używa LLM do pogłębionej analizy oraz napraw.

## Wymagania

- Python 3.10 lub nowszy,
- Linux, Windows 10/11 albo macOS 12+,
- klucz API tylko dla funkcji korzystających z LLM.

## Instalacja

Z PyPI:

```bash
python -m pip install --upgrade fixos
fixos --version
```

Z kodu źródłowego:

```bash
git clone https://github.com/wronai/fixos.git
cd fixos
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

Każdą komendę można też uruchomić jako `python -m fixos`.

## Pierwsze uruchomienie

Najpierw użyj lokalnej analizy heurystycznej:

```bash
fixos quick
```

Komenda nie wywołuje LLM i nie skanuje rekurencyjnie całego katalogu domowego.
Pokazuje bieżące użycie CPU, RAM i dysku, rozmiar jawnie odtwarzalnych cache
oraz zapisuje mały punkt odniesienia. Kolejne uruchomienia wskazują przyrosty
z ostatnich godzin i od początku dnia.

Przydatne warianty:

```bash
fixos quick --json --no-save
fixos quick --hours 24
fixos quick --deep
```

`--deep` uruchamia po szybkim wyniku pełniejszy skan usług.

## Czyszczenie miejsca

Najpierw wykonaj podgląd:

```bash
fixos cleanup --list
fixos cleanup -c npm --dry-run
fixos cleanup --docker-old --days 30 --dry-run
fixos cleanup --ollama-old --days 90 --dry-run
```

Następnie uruchom interaktywne czyszczenie:

```bash
fixos cleanup
```

fixOS dzieli dane na trzy poziomy:

- **bezpieczne** — odtwarzalne cache oraz ograniczone akcje:
  wszystkie nieużywane obrazy Docker (bez wolumenów) i modele Ollama
  niezmieniane od 90+ dni; opcja **[1]** usuwa je zbiorczo,
- **do rozważenia** — wymagają obejrzenia komendy i świadomego potwierdzenia,
- **chronione/mieszane** — pełny Docker z wolumenami, świeże modele AI,
  rozszerzenia edytorów; dostępny jest bezpieczny podgląd, a nie hurtowe kasowanie.

W trybie „Wybierz pojedyncze” lista przechodzi kolejno przez wszystkie trzy
grupy. Element bez bezpiecznej operacji usuwania pokazuje tylko diagnostykę.

Po opcji `[1]` odśwież stan: `fixos cleanup --list` (listy podsumowania
pochodzą ze skanu sprzed wykonania).
## Diagnostyka bez LLM

```bash
fixos scan
fixos scan -M audio,resources
fixos scan --yaml
```

Pełna inwentaryzacja plików jest kosztowna i uruchamiana jawnie przez moduły
rozszerzone. Do szybkiej odpowiedzi używaj `fixos quick`.

## Analiza i naprawa z LLM

Skonfiguruj provider:

```bash
fixos config init
fixos token set TWOJ_KLUCZ
fixos test-llm
```

Następnie:

```bash
fixos fix
```

Domyślny tryb HITL pyta przed wykonaniem proponowanych zmian. Tryb autonomiczny
jest dostępny jawnie:

```bash
fixos fix --mode autonomous --max-fixes 5
```

## Projekty deweloperskie

Artefakty projektów są skanowane osobno od globalnych cache:

```bash
fixos projects --dry-run
fixos projects --path ~/github --only-stale
```

## Co dalej

- [Architektura](architecture.md)
- [Konfiguracja](configuration.md)
- [API](api.md)
- [Zasady współtworzenia](CONTRIBUTING.md)
- [Aktualne zadania](../TODO.md)
