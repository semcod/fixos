# Architektura fixOS

fixOS ma dwie ścieżki diagnostyczne: natychmiastową analizę heurystyczną oraz
opcjonalną analizę pogłębioną.

```text
CLI
├── quick ──> lokalny snapshot ──> historia trendu ──> wynik bez LLM
├── cleanup ──> skaner usług ──> klasyfikacja ryzyka ──> plan/potwierdzenie
├── projects ──> skaner artefaktów projektów ──> plan/potwierdzenie
├── scan ──> moduły diagnostyczne ──> raport tekstowy/JSON/YAML
└── fix ──> quick + diagnostyka ──> anonimizacja ──> LLM ──> HITL/auto
```

## Warstwy

### CLI

Pakiet `fixos/cli/` definiuje komendy Click i formatowanie wyjścia. Główny
punkt wejścia znajduje się w `fixos.cli:main`; `fixos/__main__.py` zapewnia
równoważne uruchomienie przez `python -m fixos`.

CLI deleguje logikę do diagnostyki i agentów. Nie powinien samodzielnie
rekurencyjnie skanować systemu ani wykonywać surowych operacji usuwania.

### Diagnostyka

`fixos/diagnostics/` zawiera:

- `quick_snapshot.py` — ograniczony czasowo pomiar CPU, RAM, dysku, kontekstu
  systemu i znanych cache,
- `system_checks.py` oraz `checks/` — równoległe moduły diagnostyczne,
- `service_scanner.py` i `service_cleanup.py` — wykrywanie danych usług,
  klasyfikację ryzyka i bezpieczne plany; osobne ścieżki dla
  `docker-unused` / `docker-old` (prune unused images) oraz `ollama-old`
  (modele po `modified_at`, z pominięciem `/api/ps`),
- `project_scanner.py` — artefakty zależne od projektu, np. `.venv`,
  `node_modules` i `target`.

Skaner raportuje ścieżkę, rozmiar, poziom ryzyka i dokładną operację. Cleaner
otrzymuje wybrany wpis planu, dzięki czemu nie przelicza celu na inną ścieżkę
tuż przed wykonaniem.

### Agenci i LLM

`fixos/providers/` ujednolica komunikację z providerami zgodnymi z API OpenAI.
Przed wysłaniem danych `fixos/utils/anonymizer.py` maskuje ścieżki użytkownika,
hosty, adresy oraz tokeny.

`fixos/agent/` udostępnia:

- HITL — każda zmiana wymaga decyzji użytkownika,
- autonomous — ograniczoną liczbę samodzielnych akcji,
- wspólny timeout z `fixos/utils/timeout.py`.

`fixos/orchestrator/` modeluje zależności problemów, wykonanie i rollback.

### Pluginy

`fixos/plugins/` zawiera wbudowane moduły oraz rejestr z autodetekcją pluginów
przez grupę entry points `fixos.diagnostics`.

## Model bezpieczeństwa czyszczenia

Każdy znaleziony wpis otrzymuje jeden poziom:

1. `safe` — odbudowywalny cache z bezpieczną operacją zbiorczą,
2. `review` — dane możliwe do odzyskania, ale wymagające decyzji,
3. `dangerous` — dane rzeczywiste lub mieszane; bez automatycznego zbiorczego
   kasowania.

Tryb dry-run nigdy nie uruchamia komendy usuwającej. Dla wpisów chronionych
pokazuje diagnostykę lub komendę podglądu.

## Historia szybkich pomiarów

`fixos quick` przechowuje małą historię w
`~/.local/state/fixos/quick-history.json`. Jest to lokalny punkt odniesienia,
nie telemetria. Historia służy do pokazania wzrostu dysku, RAM, swapu i znanych
magazynów w ostatnich godzinach oraz od początku dnia.

## Testy

- `tests/unit/` — logika klasyfikacji, cleanup, snapshoty i parsery,
- `tests/e2e/` — zachowanie CLI i warstwy anonimizacji,
- `testql-scenarios/` — scenariusze kontraktowe CLI.

Podstawowa weryfikacja:

```bash
python -m pytest
python -m fixos --help
python -m fixos quick --json --no-save
```
