---
title: "fixOS — Techniczny plan refaktoryzacji: od CC=37 do czystego kodu"
slug: fixos-refactoring-roadmap
date: 2026-03-15
author: wronai
categories:
  - Projekty
  - Refactoring
tags:
  - fixOS
  - Python
  - code quality
  - cyclomatic complexity
  - refactoring
excerpt: "Szczegółowy plan refaktoryzacji projektu fixOS — rozbijanie god-functions, eliminacja duplikacji, poprawa sprzężeń modułów. Krok po kroku z konkretnymi przykładami kodu."
featured_image: ""
status: publish
---

# fixOS — Techniczny plan refaktoryzacji

> **Archiwalny plan (2026-03-15).** Główne kroki opisane w fazach 1, 2 i 4
> zostały wykonane: CLI jest pakietem modułów, HITL korzysta z klasy sesji,
> a `SessionTimeout` ma jedną implementację. Zakończone prace przeniesiono do
> [`../CHANGELOG.md`](../CHANGELOG.md); aktualne zadania są w
> [`../TODO.md`](../TODO.md).

## Diagnoza: 18 funkcji powyżej limitu złożoności

Analiza code2llm wykazała 18 funkcji z cyklomatyczną złożonością powyżej CC=15. To 9% wszystkich funkcji, ale generują one nieproporcjonalną ilość ryzyka — trudniejsze testowanie, wyższe prawdopodobieństwo regresji, gorsza czytelność.

Top 5 najgorszych:

| Funkcja | CC | Fan-out | Linie | Moduł |
|---------|---:|--------:|------:|-------|
| `_handle_natural_command` | 37 | 18 | ~100 | cli.py |
| `run_hitl_session` | 34 | 42 | ~200 | agent/hitl.py |
| `cleanup_services` | 33 | 17 | ~150 | cli.py |
| `interactive_provider_setup` | 24 | 23 | ~120 | config.py |
| `execute_cleanup_actions` | 24 | 21 | ~100 | cli.py |

## Faza 1: Rozbicie cli.py (1589L → 5 modułów po ~300L)

### Obecna struktura cli.py

Moduł `cli.py` to 1589 linii zawierających 30 funkcji i 1 klasę. Łączy w sobie:
- Definicje komend Click (scan, fix, orchestrate, token, config, ask, cleanup_services)
- Logikę biznesową obsługi dysku (_run_disk_analysis, handle_disk_cleanup_mode)
- Interaktywny setup providerów LLM
- Natural language processing (_handle_natural_command)
- Formatowanie i wyświetlanie wyników (_print_welcome, _print_quick_issues)

### Proponowany podział

**`fixos/cli/__init__.py`** — punkt wejścia, re-export `main` i `cli`:

```python
from fixos.cli.main import cli, main
__all__ = ["cli", "main"]
```

**`fixos/cli/main.py`** (~100L) — grupa główna Click i komendy top-level:

```python
import click
from fixos.cli.scan_cmd import scan
from fixos.cli.fix_cmd import fix
from fixos.cli.orchestrate_cmd import orchestrate
from fixos.cli.token_cmd import token
from fixos.cli.config_cmd import config
from fixos.cli.nlp_cmd import ask
from fixos.cli.disk_cmd import cleanup_services

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx, dry_run):
    if ctx.invoked_subcommand is None:
        _print_welcome()

cli.add_command(scan)
cli.add_command(fix)
# ...

def main():
    cli()
```

**`fixos/cli/fix_cmd.py`** (~200L) — komenda `fix` z logiką sesji naprawczej:

```python
@click.command()
@add_shared_options
def fix(provider, token, model, ...):
    cfg = _resolve_config(provider, token, model)
    diagnostics = _run_diagnostics(cfg, modules)
    session = FixSession(cfg, diagnostics, mode)
    session.run()

class FixSession:
    """Orkiestracja sesji naprawczej — deleguje do HITL/autonomous/orchestrator."""

    def __init__(self, config, diagnostics, mode):
        self.config = config
        self.diagnostics = diagnostics
        self.mode = mode

    def run(self):
        if self.mode == "hitl":
            return self._run_hitl()
        elif self.mode == "auto":
            return self._run_autonomous()
        elif self.mode == "orchestrate":
            return self._run_orchestrate()

    def _run_hitl(self):
        from fixos.agent.hitl import HITLSession
        session = HITLSession(self.diagnostics, self.config)
        return session.run()
```

**`fixos/cli/disk_cmd.py`** (~250L) — cleanup_services, handle_disk_cleanup_mode, execute_cleanup_actions

**`fixos/cli/nlp_cmd.py`** (~150L) — ask i rozbity _handle_natural_command

**`fixos/cli/formatters.py`** (~100L) — _print_welcome, _print_quick_issues, banery

### Kroki migracji (backward-compatible)

1. Utworzyć `fixos/cli/` jako pakiet z `__init__.py` re-exportujący `main` i `cli`
2. Przenieść funkcje jedna po drugiej, zachowując import ścieżki w `__init__.py`
3. Każdy przeniesiony moduł natychmiast pokryć testem importu
4. Po przeniesieniu wszystkich funkcji — usunąć stary `cli.py`
5. Sprawdzić czy `setup.py` / `pyproject.toml` console_scripts wskazuje na `fixos.cli:main`

## Faza 2: Rozbicie `run_hitl_session` (CC=34 → klasa z 6 metodami po CC<10)

### Obecny problem

`run_hitl_session` to pojedyncza funkcja o fan-out=42 — wywołuje 42 różnych funkcji. Zarządza pętlą interakcji, anonimizacją, komunikacją z LLM, parsowaniem odpowiedzi, wyświetlaniem menu i wykonywaniem komend.

### Proponowana klasa HITLSession

```python
# fixos/agent/hitl.py

class HITLSession:
    """Interaktywna sesja naprawcza z LLM w pętli Human-in-the-Loop."""

    def __init__(self, diagnostics: dict, config: FixOsConfig,
                 show_data: bool = True):
        self.diagnostics = diagnostics
        self.config = config
        self.show_data = show_data
        self.llm = LLMClient(config)
        self.conversation: list[dict] = []
        self.executed_commands: list[CmdResult] = []
        self.start_time = time.time()

    def run(self) -> SessionResult:
        """Główna pętla sesji."""
        anon_data = self._prepare_data()
        if self.show_data:
            self._show_preview(anon_data)

        self._init_conversation(anon_data)

        while not self._is_timed_out():
            response = self._get_llm_response()
            fixes = self._parse_fixes(response)

            if not fixes:
                break

            action = self._show_menu_and_get_choice(fixes)
            if action == "quit":
                break
            elif action == "skip":
                continue
            else:
                self._execute_fix(action)

        return self._build_result()

    def _prepare_data(self) -> str:
        """Anonimizacja i formatowanie diagnostyki."""
        raw = _format_diagnostics_markdown(str(self.diagnostics))
        return anonymize(raw)

    def _show_preview(self, anon_data: str):
        """Podgląd zanonimizowanych danych."""
        report = AnonymizationReport()
        display_anonymized_preview(anon_data, report)

    def _init_conversation(self, anon_data: str):
        """Inicjalizacja konwersacji z system promptem."""
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": anon_data},
        ]

    def _get_llm_response(self) -> str:
        """Wywołanie LLM i dodanie do historii."""
        response = self.llm.chat(self.conversation)
        self.conversation.append({"role": "assistant", "content": response})
        return response

    def _parse_fixes(self, response: str) -> list[tuple[str, str]]:
        """Ekstrakcja par (komenda, komentarz) z odpowiedzi LLM."""
        return _extract_fixes(response)

    def _show_menu_and_get_choice(self, fixes) -> str | int:
        """Wyświetlenie menu i pobranie wyboru użytkownika."""
        remaining = self._format_remaining_time()
        tokens = self.llm.total_tokens
        _print_action_menu(fixes, remaining, tokens)
        return self._get_user_input(len(fixes))

    def _execute_fix(self, fix_index: int):
        """Wykonanie wybranej komendy i feedback do LLM."""
        cmd, comment = self._current_fixes[fix_index]
        result = _run_cmd(cmd, comment)
        self.executed_commands.append(result)
        self.conversation.append({
            "role": "user",
            "content": f"Executed: {cmd}\nResult: {result.stdout}"
        })
```

### Zysk

Każda metoda ma CC < 10. Testowanie staje się trywialne — można mockować `_get_llm_response` i testować logikę pętli niezależnie. Fan-out rozprasza się na 6 metod zamiast koncentrować w jednej.

## Faza 3: Pipeline dla `_handle_natural_command` (CC=37 → 4 funkcje po CC<10)

```python
# fixos/cli/nlp_cmd.py

@click.command()
@click.argument("prompt")
def ask(prompt, dry_run):
    """Wykonaj polecenie w języku naturalnym."""
    intent = parse_intent(prompt)
    config = resolve_config_for_intent(intent)
    result = dispatch_intent(intent, config, dry_run)
    format_nlp_result(result)

def parse_intent(prompt: str) -> Intent:
    """Rozpoznanie intencji z promptu NLP.

    Intencje: scan, fix, cleanup, status, help, unknown.
    """
    prompt_lower = prompt.lower()
    if any(w in prompt_lower for w in ["skanuj", "sprawdź", "diagnoz"]):
        return Intent(type="scan", raw=prompt)
    elif any(w in prompt_lower for w in ["napraw", "fix", "rozwiąż"]):
        return Intent(type="fix", raw=prompt)
    elif any(w in prompt_lower for w in ["wyczyść", "cleanup", "zwolnij"]):
        return Intent(type="cleanup", raw=prompt)
    else:
        return Intent(type="llm_fallback", raw=prompt)

def resolve_config_for_intent(intent: Intent) -> FixOsConfig:
    """Załadowanie odpowiedniej konfiguracji per intencja."""
    cfg = FixOsConfig.load()
    if intent.type == "llm_fallback" and not cfg.api_key:
        cfg = interactive_provider_setup() or cfg
    return cfg

def dispatch_intent(intent: Intent, config: FixOsConfig,
                    dry_run: bool) -> NLPResult:
    """Dispatch intencji do odpowiedniej komendy."""
    dispatchers = {
        "scan": lambda: _dispatch_scan(intent, config),
        "fix": lambda: _dispatch_fix(intent, config, dry_run),
        "cleanup": lambda: _dispatch_cleanup(intent, config, dry_run),
        "llm_fallback": lambda: _dispatch_llm(intent, config),
    }
    handler = dispatchers.get(intent.type, dispatchers["llm_fallback"])
    return handler()
```

## Faza 4: Eliminacja duplikacji

### SessionTimeout × 3

Trzy identyczne klasy `SessionTimeout` w trzech modułach. Rozwiązanie:

```python
# fixos/utils/timeout.py
class SessionTimeout(Exception):
    """Wyjątek rzucany po przekroczeniu limitu czasu sesji."""
    pass

def timeout_handler(signum, frame):
    raise SessionTimeout("Sesja wygasła")
```

Aktualizacja importów we wszystkich trzech modułach:
```python
from fixos.utils.timeout import SessionTimeout, timeout_handler
```

### Duplikacja `system_checks.py` × 2

Istnieją dwa moduły: `fixos/system_checks.py` (138L, CC=6) i `fixos/diagnostics/system_checks.py` (383L, CC=14). Starszy moduł w `fixos/system_checks.py` wygląda na legacy — powinien zostać zastąpiony re-exportem z diagnostics:

```python
# fixos/system_checks.py (deprecation wrapper)
import warnings
from fixos.diagnostics.system_checks import *

warnings.warn(
    "fixos.system_checks is deprecated, use fixos.diagnostics.system_checks",
    DeprecationWarning,
    stacklevel=2,
)
```

### Duplikacja `anonymizer.py` × 2

Analogicznie: `fixos/anonymizer.py` (64L) vs `fixos/utils/anonymizer.py` (220L). Moduł główny to wrapper, utils to implementacja. Zastosować ten sam wzorzec deprecation.

## Faza 5: Poprawa testów

### Obecny stan

Projekt ma 11 plików testowych (7 e2e, 3 unit, 1 placeholder). Testy e2e dominują, co jest odwrotnie od zalecanej piramidy testów. Brakuje unit testów dla kluczowych modułów:

- `fixos/cli.py` — brak unit testów (tylko e2e przez CliRunner)
- `fixos/agent/hitl.py` — brak unit testów
- `fixos/agent/autonomous.py` — brak unit testów
- `fixos/interactive/cleanup_planner.py` — brak unit testów
- `fixos/providers/llm_analyzer.py` — brak unit testów
- `fixos/diagnostics/disk_analyzer.py` — brak unit testów

### Cele testowe po refaktoryzacji

Po rozbiciu god-functions na mniejsze metody/klasy, każda nowa jednostka powinna mieć co najmniej:

- Test happy path
- Test edge case (pusty input, brak konfiguracji)
- Test error handling (LLM timeout, brak API key, brak uprawnień)

Cel: > 80% pokrycia kodu testami unit po zakończeniu faz 1-4.

## Metryki sukcesu

| Metryka | Przed | Cel po refaktoryzacji |
|---------|------:|-----:|
| Max CC w pojedynczej funkcji | 37 | < 15 |
| Funkcje z CC > 15 | 18 | 0 |
| Największy moduł (linie) | 1589 | < 400 |
| Duplikacje klas | 3 (SessionTimeout) | 0 |
| Pokrycie docstringami klas | 48.4% | > 80% |
| Unit test coverage | ~30% (est.) | > 80% |

## Kolejność wdrażania

Każda faza jest niezależna i backward-compatible. Rekomendowana kolejność (od najwyższego ROI):

1. **Faza 4** (eliminacja duplikacji) — najłatwiejsza, natychmiastowy zysk, 1-2h pracy
2. **Faza 1** (rozbicie cli.py) — największy wpływ na maintainability
3. **Faza 2** (HITLSession) — kluczowe dla testowalności
4. **Faza 3** (NLP pipeline) — ułatwi dodawanie nowych intencji
5. **Faza 5** (testy) — prowadzone równolegle z fazami 1-3
