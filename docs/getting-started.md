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
fixos cleanup --docker-networks --dry-run
fixos cleanup --ollama-old --days 90 --dry-run
```

Następnie uruchom interaktywne czyszczenie:

```bash
fixos cleanup
```

Gdy Docker zgłasza wyczerpanie puli adresowej, rozpocznij od podglądu
`fixos cleanup --docker-networks --dry-run`, a następnie uruchom tę samą komendę
bez `--dry-run`. fixOS usuwa tylko sieci bez endpointów, chroni sieci wbudowane
i kończy operację testem utworzenia oraz usunięcia tymczasowej sieci.

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

### Osierocone obciążenia projektów

Menu wyświetlane przez samo `fixos` zawiera akcję
`fixos cleanup --orphaned-projects`. Jest to skrót informacyjny: uruchomienie
menu niczego automatycznie nie zatrzymuje. Najpierw obejrzyj kandydatów:

```bash
fixos cleanup --orphaned-projects --days 3 --dry-run
fixos cleanup --orphaned-projects --days 3 --list
fixos cleanup --orphaned-projects --days 3 --process-hours 12 --json
```

Równoważny alias to `fixos cleanup -c orphaned-projects`. Domyślny próg wynosi
3 dni dla kontenerów i 12 godzin dla procesów. Kontener Compose trafia na listę
tylko wtedy, gdy ma politykę startową `always` lub `unless-stopped`, jego
bezwzględna ścieżka katalogu projektu już nie istnieje, a wiek przekracza próg.
Procesy obejmują stare drzewa agentów PyCharma oraz serwery developerskie PHP
lub Node bez podłączonych klientów. Wynik pokazuje PID, wiek, potomków, RAM,
porty i połączenia.

FixOS chroni własne drzewo procesu, konta systemowe, główny proces JetBrains
oraz bieżące procesy Codex. Sam wiek nie powoduje zmiany. Bez `--dry-run` lub
`--list` wybierasz dokładne numery (`1,3-5` albo `all`), następnie osobno
potwierdzasz:

1. ustawienie `restart=no` i zatrzymanie wybranych kontenerów,
2. łagodne zakończenie wybranych drzew procesów,
3. opcjonalne wymuszenie tylko dla procesów, które nie zakończyły się łagodnie.

Przed zmianą FixOS wykonuje świeży skan i ponownie sprawdza pełny identyfikator
kontenera oraz czas utworzenia PID. Procesy są kończone od liści do korzenia.
Po sukcesie wybrane kontenery pozostają zapisane w stanie `exited` z
`restart=no`, a wybrane drzewa procesów nie działają. Kontenery, wolumeny,
obrazy, sieci, katalogi projektów i pliki nie są usuwane. Ponowne uruchomienie
dry-run powinno pokazać, że wykonane cele nie są już kandydatami.

## Diagnostyka bez LLM

```bash
fixos scan
fixos scan -M audio,resources
fixos scan --yaml
```

Pełna inwentaryzacja plików jest kosztowna i uruchamiana jawnie przez moduły
rozszerzone. Do szybkiej odpowiedzi używaj `fixos quick`.

Bezpieczne czyszczenie Dockera może objąć również osierocone sieci:

```bash
fixos cleanup --docker-all --dry-run
fixos cleanup --docker-old --days 30 --dry-run
fixos cleanup --docker-networks --dry-run
```

Pierwsze dwie akcje łączą obrazy/cache z sieciami; trzecia pozostawia obrazy
bez zmian. Żadna z nich nie usuwa kontenerów ani wolumenów.

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
fixos projects --path ~/github --only-stale --docker-networks --dry-run
```

Flaga `--docker-networks` pokazuje, a po osobnym potwierdzeniu usuwa wyłącznie
nieużywane sieci Docker Compose oznaczone etykietą wybranego projektu. Nie
usuwa repozytoriów, kontenerów ani wolumenów.

## Co dalej

- [Architektura](architecture.md)
- [Konfiguracja](configuration.md)
- [API](api.md)
- [Zasady współtworzenia](CONTRIBUTING.md)
- [Aktualne zadania](../TODO.md)
