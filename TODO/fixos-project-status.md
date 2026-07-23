---
title: "fixOS — Status projektu i plan rozwoju"
slug: fixos-project-status
date: 2026-03-15
author: wronai
categories:
  - Projekty
  - Open Source
tags:
  - fixOS
  - Python
  - diagnostyka systemowa
  - LLM
  - refactoring
excerpt: "Przegląd aktualnego stanu projektu fixOS — AI-powered diagnostyka i naprawa systemów Linux/Windows/macOS. Metryki zdrowia kodu, plan refaktoryzacji i roadmapa nowych funkcji."
featured_image: ""
status: publish
---

# fixOS — Status projektu i plan rozwoju

> **Archiwalny snapshot (2026-03-15).** Wersja, metryki i plan poniżej opisują
> stan historyczny. Rozbicie CLI, klasy sesji, pluginy, rollback, profile,
> structured output i watch mode zostały już wdrożone. Bieżące zadania:
> [`../TODO.md`](../TODO.md); wykonane zmiany: [`../CHANGELOG.md`](../CHANGELOG.md).

**Repozytorium:** [github.com/wronai/fixfedora](https://github.com/wronai/fixfedora)
**Wersja:** 0.1.0
**Licencja:** Apache-2.0
**Python:** >=3.10

## Czym jest fixOS?

fixOS to narzędzie CLI do automatycznej diagnostyki i naprawy problemów systemowych na Linux, Windows i macOS. Wykorzystuje LLM (Large Language Models) do analizy danych diagnostycznych i proponowania konkretnych komend naprawczych. Projekt działa w trzech trybach: interaktywnym (HITL — Human-in-the-Loop), autonomicznym (agent sam wykonuje naprawy z ograniczeniami bezpieczeństwa) oraz orkiestracyjnym (graf zależności problemów z topologicznym sortowaniem kolejności napraw).

## Metryki kodu — stan na marzec 2026

| Metryka | Wartość |
|---------|---------|
| Moduły | 30 |
| Funkcje | 203 |
| Klasy | 31 |
| Średnia złożoność cyklomatyczna | 6.0 |
| Funkcje krytyczne (CC ≥ 10) | 41 (20%) |
| Pokrycie docstringami | 76.5% |
| Cykle zależności | 1 |
| Czas analizy | 3.25s |

## Obszary wymagające refaktoryzacji

### Krytyczne funkcje o nadmiernej złożoności

Analiza wykazała 18 funkcji z CC > 15, z czego 5 wymaga natychmiastowego rozbicia:

**`_handle_natural_command` (CC=37)** — absolutny rekord złożoności w projekcie. Ta funkcja w `cli.py` próbuje zinterpretować polecenie użytkownika w języku naturalnym, wykryć intencję, załadować konfigurację, wywołać LLM i wykonać akcję — wszystko w jednej metodzie. Jej fan-out wynosi 18, co oznacza że wywołuje 18 różnych funkcji.

**`run_hitl_session` (CC=34, fan=42)** — najgorętszy hotspot projektu. Sesja HITL zarządza całym cyklem życia interakcji: wyświetlanie diagnostyki, anonimizacja danych, komunikacja z LLM, parsowanie odpowiedzi, wyświetlanie menu akcji, wykonywanie komend i obsługa timeoutu. Fan-out 42 oznacza, że ta funkcja jest de facto orkiestratorem całego trybu interaktywnego.

**`cleanup_services` (CC=33)** — komenda CLI obsługująca skanowanie, filtrowanie, wyświetlanie i czyszczenie danych usług. Ma 41 węzłów w grafie sterowania i 4 punkty wyjścia.

**`interactive_provider_setup` (CC=24)** — setup providera LLM z wieloma ścieżkami logiki: auto-detekcja klucza API, interaktywny wybór, walidacja, fallback do darmowych providerów.

**`execute_cleanup_actions` (CC=24)** — wykonywanie akcji czyszczenia z obsługą błędów, potwierdzeniami, fallbackiem do LLM.

### Moduł-bóg: `cli.py` (1589 linii)

`cli.py` to zdecydowanie największy moduł w projekcie — 1589 linii, 30 funkcji, 1 klasa. Zawiera w sobie logikę, która powinna być rozdzielona na osobne moduły: obsługa komend Click, logika biznesowa dysku, setup providerów, natural language processing, formatowanie wyników. Ten moduł ma CC=37 w najgorszej funkcji i jest głównym źródłem code smelli w projekcie.

### Coupling i architektura

Analiza sprzężeń wykazała dwa poważne problemy:

- **`fixos.agent/` fan-out=29** — moduł agenta importuje zbyt wiele zależności, co czyni go kruchym na zmiany w reszcie kodu
- **`fixos.orchestrator/` fan-out=8** — orkiestrator również ma podwyższone sprzężenie wyjściowe
- **`fixos.utils/` fan-in=20** — hub utilities jest importowany przez prawie wszystko, co jest typowe, ale warto monitorować

Wykryto 1 cykl zależności, który wymaga przerwania.

### Pokrycie dokumentacją

Ogólne pokrycie docstringami wynosi 76.5%, ale rozkład jest nierówny. Klasy mają tylko 48.4% pokrycia (15/31). Najsłabiej udokumentowane moduły to `orchestrator.executor` (25%), `llm_shell` (40%) i `orchestrator.graph` (50%).

## Plan refaktoryzacji — priorytety

### Priorytet 1: Rozbicie `cli.py` (impact: wysoki, effort: średni)

Proponowany podział:

- `fixos/cli/commands.py` — definicje komend Click (scan, fix, orchestrate, token, config)
- `fixos/cli/disk_commands.py` — komendy związane z dyskiem (cleanup_services, handle_disk_cleanup_mode)
- `fixos/cli/provider_setup.py` — interactive_provider_setup, detect_provider_from_key, konfiguracja LLM
- `fixos/cli/nlp.py` — _handle_natural_command i NaturalLanguageGroup
- `fixos/cli/formatters.py` — _print_welcome, _print_quick_issues, formatowanie wyników
- `fixos/cli/__init__.py` — re-export main() i cli group

Każdy nowy moduł powinien mieć CC < 15 w najdłuższej funkcji. Kluczowe: komenda `fix` powinna delegować do dedykowanego modułu `fixos/cli/fix_flow.py` zamiast inline'ować logikę sesji naprawczej.

### Priorytet 2: Rozbicie `run_hitl_session` (impact: wysoki, effort: średni)

Ta funkcja z CC=34 powinna zostać zamieniona w klasę `HITLSession`:

```python
class HITLSession:
    def __init__(self, diagnostics, config, show_data):
        self.diagnostics = diagnostics
        self.config = config
        self.llm = LLMClient(config)

    def run(self):
        self._prepare_data()
        self._show_preview()
        self._main_loop()
        self._summarize()

    def _prepare_data(self):
        """Anonimizacja i formatowanie diagnostyki."""

    def _show_preview(self):
        """Wyświetlenie podglądu danych przed wysłaniem do LLM."""

    def _main_loop(self):
        """Pętla interakcji: LLM → parsuj → pokaż menu → wykonaj."""

    def _handle_user_action(self, fixes, choice):
        """Obsługa wyboru użytkownika z menu akcji."""
```

### Priorytet 3: Rozbicie `_handle_natural_command` (impact: wysoki, effort: niski)

Funkcja CC=37 powinna zostać podzielona na pipeline:

1. `_parse_intent(prompt)` — rozpoznanie intencji (scan, fix, cleanup, status)
2. `_resolve_config(intent)` — ładowanie konfiguracji per intencja
3. `_execute_intent(intent, config, dry_run)` — dispatch do odpowiedniej komendy
4. `_format_nlp_response(result)` — formatowanie wyniku

### Priorytet 4: Eliminacja duplikacji SessionTimeout (impact: niski, effort: niski)

Klasa `SessionTimeout` jest zdefiniowana w trzech miejscach: `autonomous.py`, `hitl.py`, `llm_shell.py`. Powinna istnieć jedna wersja w `fixos/utils/timeout.py`:

```python
# fixos/utils/timeout.py
class SessionTimeout(Exception):
    pass

def setup_timeout(seconds, handler=None):
    """Cross-platform timeout setup."""
```

### Priorytet 5: Poprawa pokrycia docstringami klas (impact: średni, effort: niski)

Dodanie docstringów do 16 nieudokumentowanych klas, ze szczególnym uwzględnieniem: `CommandExecutor`, `Problem`, `ProblemGraph`, `ExecutionResult`, `FixOsConfig`, `NaturalLanguageGroup`.

## Nowe funkcje — propozycje

### 1. Plugin System dla diagnostyki (impact: bardzo wysoki)

Obecnie moduły diagnostyczne (`diagnose_audio`, `diagnose_hardware`, `diagnose_security`, itd.) są zakodowane na sztywno w `system_checks.py`. Proponowany system pluginów pozwoli na:

- Dodawanie własnych modułów diagnostycznych bez modyfikacji kodu źródłowego
- Dystrybucja pluginów jako osobne pakiety PyPI
- Community-driven diagnostyka dla specyficznych środowisk

**Implementacja:**

```python
# fixos/plugins/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class DiagnosticResult:
    module: str
    status: str  # ok | warning | critical
    data: dict
    suggestions: list[str]

class DiagnosticPlugin(ABC):
    name: str
    description: str
    platforms: list[str]  # ["linux", "windows", "macos"]

    @abstractmethod
    def diagnose(self) -> DiagnosticResult:
        ...

    @abstractmethod
    def can_run(self) -> bool:
        """Sprawdza czy plugin może działać na aktualnej platformie."""
        ...

# fixos/plugins/registry.py
import importlib.metadata

class PluginRegistry:
    def __init__(self):
        self._plugins: dict[str, DiagnosticPlugin] = {}

    def discover(self):
        """Odkrywanie pluginów przez entry_points."""
        for ep in importlib.metadata.entry_points(group="fixos.diagnostics"):
            plugin_cls = ep.load()
            plugin = plugin_cls()
            if plugin.can_run():
                self._plugins[plugin.name] = plugin

    def run_all(self, modules=None) -> list[DiagnosticResult]:
        targets = modules or self._plugins.keys()
        return [self._plugins[m].diagnose() for m in targets
                if m in self._plugins]
```

Entry point w `pyproject.toml` pluginu:

```toml
[project.entry-points."fixos.diagnostics"]
nvidia = "fixos_nvidia:NvidiaDiagnosticPlugin"
```

### 2. Structured Output z LLM (impact: wysoki)

Obecny parsing odpowiedzi LLM opiera się na regex i ręcznym ekstrakcji JSON z tekstu (`_parse_agent_json`, `_extract_fixes`). To jest kruche. Proponowane rozwiązanie: użycie structured output / function calling z API LLM.

**Implementacja:**

```python
# fixos/providers/schemas.py
from pydantic import BaseModel

class FixSuggestion(BaseModel):
    command: str
    description: str
    risk_level: str  # safe | moderate | dangerous
    requires_sudo: bool
    idempotent: bool
    rollback_command: str | None = None

class DiagnosticAnalysis(BaseModel):
    summary: str
    problems: list[str]
    suggestions: list[FixSuggestion]
    confidence: float

# W LLMClient:
def chat_structured(self, messages, response_model: type[BaseModel]):
    """Wywołanie LLM z wymuszonym schematem odpowiedzi."""
    schema = response_model.model_json_schema()
    messages[-1]["content"] += f"\n\nRespond ONLY with valid JSON matching: {schema}"
    raw = self.chat(messages)
    return response_model.model_validate_json(raw)
```

### 3. Rollback System (impact: wysoki)

Obecnie fixOS wykonuje komendy naprawcze bez możliwości cofnięcia zmian. Proponowany system:

**Implementacja:**

```python
# fixos/orchestrator/rollback.py
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class RollbackEntry:
    timestamp: str
    command: str
    rollback_command: str | None
    stdout: str
    success: bool

@dataclass
class RollbackLog:
    session_id: str
    entries: list[RollbackEntry] = field(default_factory=list)
    log_path: Path = Path.home() / ".fixos" / "rollback"

    def record(self, command, rollback_cmd, stdout, success):
        self.entries.append(RollbackEntry(
            timestamp=datetime.now().isoformat(),
            command=command,
            rollback_command=rollback_cmd,
            stdout=stdout,
            success=success,
        ))
        self._save()

    def rollback_last(self, n=1):
        """Cofnij ostatnich n operacji."""
        to_rollback = [e for e in reversed(self.entries)
                       if e.success and e.rollback_command][:n]
        for entry in to_rollback:
            # execute entry.rollback_command
            ...

    def _save(self):
        self.log_path.mkdir(parents=True, exist_ok=True)
        path = self.log_path / f"{self.session_id}.json"
        path.write_text(json.dumps(
            [vars(e) for e in self.entries], indent=2
        ))
```

Nowa komenda CLI:

```bash
fixos rollback              # cofnij ostatnią operację
fixos rollback --list       # pokaż historię
fixos rollback --session X  # cofnij całą sesję
```

### 4. Raportowanie w formacie HTML/PDF (impact: średni)

Dodanie możliwości eksportu wyników diagnostyki do czytelnego raportu:

```bash
fixos scan --output-format html -o report.html
fixos scan --output-format pdf -o report.pdf
```

**Implementacja:** Użycie Jinja2 do templatowania HTML + opcjonalnie weasyprint dla PDF. Raport zawierałby sekcje: podsumowanie zdrowia systemu, wykryte problemy z severity, sugestie napraw, metryki systemowe z wykresami (użycie CPU/RAM/disk w czasie).

### 5. Watch Mode z automatyczną re-diagnostyką (impact: średni)

```bash
fixos watch --interval 300 --modules system,security --alert-on critical
```

Monitorowanie systemu w tle z powiadomieniami (desktop notifications via `notify-send` na Linux) gdy pojawią się nowe problemy krytyczne. Przydatne na serwerach i stacjach roboczych, które wymagają ciągłego monitorowania.

### 6. Profiles / Presets (impact: średni)

Predefiniowane zestawy diagnostyk dla różnych scenariuszy:

```bash
fixos scan --profile server     # disk, security, services, network
fixos scan --profile desktop    # audio, thumbnails, hardware, resources
fixos scan --profile developer  # disk, services (docker, conda, npm)
fixos scan --profile minimal    # system only
```

**Implementacja:** YAML-based profile definitions w `fixos/profiles/`:

```yaml
# fixos/profiles/server.yaml
name: server
description: "Diagnostyka serwera produkcyjnego"
modules:
  - system
  - security
  - disk
  - services
  - network
thresholds:
  disk_usage_warning: 80
  disk_usage_critical: 95
```

### 7. Dry-run z symulacją efektów (impact: średni)

Rozszerzenie istniejącego `--dry-run` o symulację: zamiast tylko wyświetlić komendy, pokazać co by się zmieniło (przed/po). Wykorzystanie `check_idempotent` z `CommandExecutor` do weryfikacji stanu przed i po.

## Roadmapa

| Kwartał | Cel | Priorytet |
|---------|-----|-----------|
| Q2 2026 | Rozbicie cli.py, eliminacja duplikacji SessionTimeout | Refaktoring krytyczny |
| Q2 2026 | Rozbicie run_hitl_session na klasę HITLSession | Refaktoring krytyczny |
| Q3 2026 | Plugin system dla diagnostyki | Nowa funkcja |
| Q3 2026 | Structured output z LLM (Pydantic schemas) | Nowa funkcja |
| Q3 2026 | Rollback system | Nowa funkcja |
| Q4 2026 | Profiles/presets, watch mode | Nowe funkcje |
| Q4 2026 | Raportowanie HTML/PDF | Nowa funkcja |

## Podsumowanie

fixOS to obiecujący projekt z solidnym fundamentem architekturalnym — graf problemów z topologicznym sortowaniem, wielopoziomowa anonimizacja danych, bezpieczny executor z blokadą niebezpiecznych komend. Główne wyzwania to nadmierna złożoność funkcji w warstwie CLI i sesji interaktywnych (5 funkcji z CC > 20) oraz brak systemu pluginów, który ułatwiłby rozszerzanie diagnostyki przez społeczność. Plan refaktoryzacji koncentruje się na rozbijaniu god-functions i wprowadzeniu wzorców, które umożliwią dalszy wzrost projektu bez degradacji jakości kodu.
