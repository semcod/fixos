---
title: "fixOS — Nowe funkcje: plugin system, rollback, structured output i więcej"
slug: fixos-new-features-roadmap
date: 2026-03-15
author: wronai
categories:
  - Projekty
  - Rozwój
tags:
  - fixOS
  - Python
  - plugin system
  - rollback
  - LLM
  - structured output
excerpt: "Szczegółowy projekt nowych funkcji fixOS: system pluginów diagnostycznych, rollback operacji, structured output z LLM, profile diagnostyczne, watch mode i raportowanie HTML/PDF."
featured_image: ""
status: publish
---

# fixOS — Nowe funkcje: szczegóły implementacji

> **Archiwalny plan (2026-03-15).** Plugin registry, structured output,
> rollback, profile diagnostyczne i watch mode są już dostępne w kodzie.
> Zakończone prace przeniesiono do [`../CHANGELOG.md`](../CHANGELOG.md);
> bieżące zadania znajdują się w [`../TODO.md`](../TODO.md).

## 1. Plugin System dla diagnostyki

### Problem

Moduły diagnostyczne są zakodowane na sztywno w `fixos/diagnostics/system_checks.py` i `fixos/system_checks.py`. Dodanie nowej diagnostyki wymaga modyfikacji kodu źródłowego fixOS. Społeczność nie może tworzyć własnych modułów diagnostycznych bez forkowania projektu.

### Architektura rozwiązania

Plugin system oparty na `importlib.metadata` entry points — standard Pythona, zero dodatkowych zależności.

```
fixos/
├── plugins/
│   ├── __init__.py
│   ├── base.py          # DiagnosticPlugin ABC + DiagnosticResult
│   ├── registry.py      # PluginRegistry — discover, register, run
│   └── builtin/         # Wbudowane pluginy (migracja z system_checks)
│       ├── __init__.py
│       ├── audio.py
│       ├── hardware.py
│       ├── security.py
│       ├── resources.py
│       ├── disk.py
│       └── thumbnails.py
```

### Interfejs pluginu

```python
# fixos/plugins/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Severity(Enum):
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Finding:
    title: str
    severity: Severity
    description: str
    suggestion: str | None = None
    command: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

@dataclass
class DiagnosticResult:
    plugin_name: str
    status: Severity
    findings: list[Finding] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

class DiagnosticPlugin(ABC):
    """Bazowa klasa dla pluginów diagnostycznych fixOS."""

    name: str = "unnamed"
    description: str = ""
    version: str = "0.1.0"
    platforms: list[str] = ["linux", "windows", "macos"]

    @abstractmethod
    def diagnose(self) -> DiagnosticResult:
        """Wykonaj diagnostykę i zwróć wynik."""
        ...

    def can_run(self) -> bool:
        """Czy plugin może działać na aktualnej platformie?"""
        import platform
        current = platform.system().lower()
        platform_map = {"linux": "linux", "darwin": "macos", "windows": "windows"}
        return platform_map.get(current, current) in self.platforms

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "platforms": self.platforms,
        }
```

### Registry z autodiscovery

```python
# fixos/plugins/registry.py
import importlib.metadata
import time
import logging

logger = logging.getLogger(__name__)

class PluginRegistry:
    ENTRY_POINT_GROUP = "fixos.diagnostics"

    def __init__(self):
        self._plugins: dict[str, DiagnosticPlugin] = {}
        self._results: dict[str, DiagnosticResult] = {}

    def discover(self):
        """Odkrywanie pluginów przez entry_points + builtin."""
        self._register_builtins()
        self._register_external()

    def _register_builtins(self):
        from fixos.plugins.builtin import (
            audio, hardware, security, resources, disk, thumbnails
        )
        for module in [audio, hardware, security, resources, disk, thumbnails]:
            plugin = module.Plugin()
            self._plugins[plugin.name] = plugin

    def _register_external(self):
        for ep in importlib.metadata.entry_points(
            group=self.ENTRY_POINT_GROUP
        ):
            try:
                plugin_cls = ep.load()
                plugin = plugin_cls()
                if plugin.name in self._plugins:
                    logger.warning(f"Plugin {plugin.name} already registered, "
                                   f"skipping external {ep.name}")
                    continue
                self._plugins[plugin.name] = plugin
                logger.info(f"Loaded external plugin: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {ep.name}: {e}")

    def list_plugins(self, runnable_only=True) -> list[dict]:
        plugins = self._plugins.values()
        if runnable_only:
            plugins = [p for p in plugins if p.can_run()]
        return [p.get_metadata() for p in plugins]

    def run(self, modules: list[str] | None = None,
            progress_callback=None) -> list[DiagnosticResult]:
        targets = modules or list(self._plugins.keys())
        results = []

        for name in targets:
            if name not in self._plugins:
                logger.warning(f"Unknown plugin: {name}")
                continue

            plugin = self._plugins[name]
            if not plugin.can_run():
                logger.info(f"Skipping {name} — not available on this platform")
                continue

            if progress_callback:
                progress_callback(name, "running")

            start = time.monotonic()
            try:
                result = plugin.diagnose()
                result.duration_ms = (time.monotonic() - start) * 1000
                results.append(result)
            except Exception as e:
                logger.error(f"Plugin {name} failed: {e}")
                results.append(DiagnosticResult(
                    plugin_name=name,
                    status=Severity.CRITICAL,
                    findings=[Finding(
                        title=f"Plugin {name} crashed",
                        severity=Severity.CRITICAL,
                        description=str(e),
                    )]
                ))

        return results
```

### Migracja istniejącej diagnostyki

Przykład migracji `diagnose_audio()` na plugin:

```python
# fixos/plugins/builtin/audio.py
from fixos.plugins.base import DiagnosticPlugin, DiagnosticResult, Finding, Severity

class Plugin(DiagnosticPlugin):
    name = "audio"
    description = "Diagnostyka dźwięku (ALSA/PipeWire/PulseAudio/SOF)"
    platforms = ["linux"]

    def diagnose(self) -> DiagnosticResult:
        findings = []
        raw_data = {}

        # ALSA cards
        alsa = self._check_alsa()
        raw_data["alsa"] = alsa
        if not alsa.get("cards"):
            findings.append(Finding(
                title="Brak kart ALSA",
                severity=Severity.CRITICAL,
                description="System nie wykrył żadnych kart dźwiękowych ALSA.",
                suggestion="Sprawdź czy moduły jądra snd_* są załadowane.",
                command="sudo modprobe snd_hda_intel",
            ))

        # PipeWire status
        pw = self._check_pipewire()
        raw_data["pipewire"] = pw
        if pw.get("status") == "failed":
            findings.append(Finding(
                title="PipeWire nie działa",
                severity=Severity.CRITICAL,
                description="Usługa PipeWire nie jest aktywna.",
                command="systemctl --user restart pipewire pipewire-pulse",
            ))

        status = Severity.OK
        if any(f.severity == Severity.CRITICAL for f in findings):
            status = Severity.CRITICAL
        elif any(f.severity == Severity.WARNING for f in findings):
            status = Severity.WARNING

        return DiagnosticResult(
            plugin_name=self.name,
            status=status,
            findings=findings,
            raw_data=raw_data,
        )

    def _check_alsa(self) -> dict:
        from fixos.platform_utils import run_command
        output = run_command("cat /proc/asound/cards", timeout=5)
        # parse...
        return {"cards": [...], "raw": output}

    def _check_pipewire(self) -> dict:
        from fixos.platform_utils import run_command
        output = run_command(
            "systemctl --user is-active pipewire", timeout=5
        )
        return {"status": output.strip()}
```

### Tworzenie zewnętrznego pluginu

Deweloper zewnętrzny tworzy pakiet:

```
fixos-nvidia-plugin/
├── pyproject.toml
└── fixos_nvidia/
    └── __init__.py
```

```toml
# pyproject.toml
[project]
name = "fixos-nvidia-plugin"
version = "0.1.0"
dependencies = ["fixos>=0.2.0"]

[project.entry-points."fixos.diagnostics"]
nvidia = "fixos_nvidia:NvidiaPlugin"
```

```python
# fixos_nvidia/__init__.py
from fixos.plugins.base import DiagnosticPlugin, DiagnosticResult, Finding, Severity

class NvidiaPlugin(DiagnosticPlugin):
    name = "nvidia"
    description = "Diagnostyka GPU NVIDIA (sterowniki, CUDA, temperatura)"
    platforms = ["linux", "windows"]

    def diagnose(self) -> DiagnosticResult:
        # nvidia-smi, CUDA check, driver version...
        ...
```

Po `pip install fixos-nvidia-plugin`, plugin jest automatycznie wykrywany.

## 2. Structured Output z LLM

### Problem

Obecny parsing odpowiedzi LLM bazuje na regex (`_extract_fixes`, `_parse_agent_json`). To kruche — LLM zmienia formatowanie, dodaje markdown, owija komendy w backticki różnie. Każda zmiana modelu wymaga aktualizacji regexów.

### Rozwiązanie: Pydantic schemas + prompt engineering

```python
# fixos/providers/schemas.py
from pydantic import BaseModel, Field
from enum import Enum

class RiskLevel(str, Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"

class FixSuggestion(BaseModel):
    """Pojedyncza sugestia naprawy od LLM."""
    command: str = Field(description="Komenda shell do wykonania")
    description: str = Field(description="Co robi ta komenda — po polsku")
    risk_level: RiskLevel = Field(description="Poziom ryzyka")
    requires_sudo: bool = Field(default=False)
    idempotent: bool = Field(
        default=False,
        description="Czy ponowne wykonanie jest bezpieczne"
    )
    check_command: str | None = Field(
        default=None,
        description="Komenda sprawdzająca czy naprawa jest potrzebna"
    )
    rollback_command: str | None = Field(
        default=None,
        description="Komenda cofająca zmianę"
    )

class LLMDiagnosticResponse(BaseModel):
    """Strukturalna odpowiedź LLM na dane diagnostyczne."""
    summary: str = Field(description="Podsumowanie problemów — 2-3 zdania")
    root_causes: list[str] = Field(description="Główne przyczyny problemów")
    suggestions: list[FixSuggestion] = Field(
        description="Lista sugestii napraw, od najbezpieczniejszej"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Pewność diagnozy (0.0 — zgadywanie, 1.0 — pewność)"
    )
    needs_more_info: list[str] = Field(
        default_factory=list,
        description="Jakie dodatkowe dane byłyby pomocne"
    )
```

### Rozszerzenie LLMClient

```python
# fixos/providers/llm.py — rozszerzenie

import json
from pydantic import BaseModel

class LLMClient:
    # ... existing methods ...

    def chat_structured(self, messages: list[dict],
                        response_model: type[BaseModel],
                        max_retries: int = 2) -> BaseModel:
        """Wywołanie LLM z wymuszonym schematem JSON."""
        schema = response_model.model_json_schema()
        schema_prompt = (
            "\n\n---\n"
            "CRITICAL: Respond ONLY with a valid JSON object matching "
            f"this schema:\n```json\n{json.dumps(schema, indent=2)}\n```\n"
            "No markdown, no explanation, no preamble. ONLY the JSON object."
        )

        augmented = messages.copy()
        augmented[-1] = {
            **augmented[-1],
            "content": augmented[-1]["content"] + schema_prompt
        }

        for attempt in range(max_retries + 1):
            raw = self.chat(augmented)
            cleaned = self._extract_json(raw)
            try:
                return response_model.model_validate_json(cleaned)
            except Exception as e:
                if attempt < max_retries:
                    augmented.append({"role": "assistant", "content": raw})
                    augmented.append({
                        "role": "user",
                        "content": f"Invalid JSON. Error: {e}. "
                                   f"Please output ONLY valid JSON."
                    })
                else:
                    raise ValueError(
                        f"LLM failed to produce valid schema after "
                        f"{max_retries + 1} attempts: {e}"
                    )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Wyciągnij JSON z odpowiedzi LLM (obsługa markdown fences)."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # skip first and last line (fences)
            text = "\n".join(lines[1:-1] if lines[-1].startswith("```")
                            else lines[1:])
        return text.strip()
```

## 3. Rollback System

### Architektura

Każda sesja naprawcza generuje log rollback w `~/.fixos/rollback/`. Log zawiera pary (komenda, komenda_cofająca) dla każdej wykonanej operacji.

```python
# fixos/orchestrator/rollback.py
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

@dataclass
class RollbackEntry:
    timestamp: str
    command: str
    rollback_command: Optional[str]
    stdout: str
    stderr: str
    success: bool
    exit_code: int

@dataclass
class RollbackSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    entries: list[RollbackEntry] = field(default_factory=list)

    LOG_DIR = Path.home() / ".fixos" / "rollback"

    def record(self, command: str, rollback_cmd: Optional[str],
               stdout: str, stderr: str, success: bool,
               exit_code: int):
        self.entries.append(RollbackEntry(
            timestamp=datetime.now().isoformat(),
            command=command,
            rollback_command=rollback_cmd,
            stdout=stdout,
            stderr=stderr,
            success=success,
            exit_code=exit_code,
        ))
        self._save()

    def get_rollback_commands(self) -> list[tuple[str, str]]:
        """Zwraca listę (komenda, rollback) w odwróconej kolejności."""
        return [
            (e.command, e.rollback_command)
            for e in reversed(self.entries)
            if e.success and e.rollback_command
        ]

    def _save(self):
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = self.LOG_DIR / f"{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "entries": [asdict(e) for e in self.entries],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, session_id: str) -> "RollbackSession":
        path = cls.LOG_DIR / f"{session_id}.json"
        data = json.loads(path.read_text())
        session = cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
        )
        session.entries = [RollbackEntry(**e) for e in data["entries"]]
        return session

    @classmethod
    def list_sessions(cls, limit: int = 20) -> list[dict]:
        if not cls.LOG_DIR.exists():
            return []
        files = sorted(cls.LOG_DIR.glob("*.json"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        sessions = []
        for f in files[:limit]:
            data = json.loads(f.read_text())
            sessions.append({
                "session_id": data["session_id"],
                "created_at": data["created_at"],
                "operations": len(data["entries"]),
                "rollbackable": sum(
                    1 for e in data["entries"]
                    if e.get("rollback_command") and e.get("success")
                ),
            })
        return sessions
```

### Integracja z CommandExecutor

```python
# W fixos/orchestrator/executor.py — rozszerzenie execute_sync

class CommandExecutor:
    def __init__(self, ..., rollback_session=None):
        # ...
        self.rollback = rollback_session

    def execute_sync(self, command, timeout=None, rollback_cmd=None):
        result = self._do_execute(command, timeout)

        if self.rollback:
            self.rollback.record(
                command=command,
                rollback_cmd=rollback_cmd,
                stdout=result.stdout,
                stderr=result.stderr,
                success=result.success,
                exit_code=result.exit_code,
            )

        return result
```

### Nowe komendy CLI

```python
# fixos/cli/rollback_cmd.py

@click.group()
def rollback():
    """Zarządzanie cofaniem operacji fixOS."""
    pass

@rollback.command("list")
@click.option("--limit", default=20, help="Ile sesji pokazać")
def rollback_list(limit):
    """Pokaż historię sesji naprawczych."""
    sessions = RollbackSession.list_sessions(limit)
    for s in sessions:
        click.echo(
            f"  {s['session_id']}  "
            f"{s['created_at'][:16]}  "
            f"{s['operations']} ops  "
            f"{s['rollbackable']} rollbackable"
        )

@rollback.command("undo")
@click.argument("session_id")
@click.option("--last", default=1, help="Ile ostatnich operacji cofnąć")
@click.option("--dry-run", is_flag=True, help="Tylko pokaż co by się cofnęło")
def rollback_undo(session_id, last, dry_run):
    """Cofnij operacje z podanej sesji."""
    session = RollbackSession.load(session_id)
    commands = session.get_rollback_commands()[:last]

    if not commands:
        click.echo("Brak operacji do cofnięcia w tej sesji.")
        return

    for orig, rollback_cmd in commands:
        click.echo(f"  Cofam: {orig}")
        click.echo(f"  →  {rollback_cmd}")
        if not dry_run:
            result = run_command(rollback_cmd, timeout=30)
            status = "OK" if result.returncode == 0 else "FAIL"
            click.echo(f"  Status: {status}")
```

## 4. Diagnostic Profiles

### Implementacja

```python
# fixos/profiles/__init__.py
import yaml
from pathlib import Path
from dataclasses import dataclass

PROFILES_DIR = Path(__file__).parent

@dataclass
class Profile:
    name: str
    description: str
    modules: list[str]
    thresholds: dict[str, int | float]

    @classmethod
    def load(cls, name: str) -> "Profile":
        # Najpierw szukaj w user config
        user_path = Path.home() / ".fixos" / "profiles" / f"{name}.yaml"
        if user_path.exists():
            path = user_path
        else:
            path = PROFILES_DIR / f"{name}.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found")

        data = yaml.safe_load(path.read_text())
        return cls(**data)

    @classmethod
    def list_available(cls) -> list[str]:
        builtin = [f.stem for f in PROFILES_DIR.glob("*.yaml")]
        user_dir = Path.home() / ".fixos" / "profiles"
        user = [f.stem for f in user_dir.glob("*.yaml")] if user_dir.exists() else []
        return sorted(set(builtin + user))
```

Wbudowane profile:

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
  service_data_threshold_mb: 500
```

```yaml
# fixos/profiles/desktop.yaml
name: desktop
description: "Diagnostyka stacji roboczej"
modules:
  - system
  - audio
  - hardware
  - thumbnails
  - resources
  - disk
thresholds:
  disk_usage_warning: 85
  disk_usage_critical: 95
```

```yaml
# fixos/profiles/developer.yaml
name: developer
description: "Diagnostyka środowiska deweloperskiego"
modules:
  - system
  - disk
  - services
thresholds:
  disk_usage_warning: 75
  service_data_threshold_mb: 200
```

```yaml
# fixos/profiles/minimal.yaml
name: minimal
description: "Szybka diagnostyka — tylko metryki systemowe"
modules:
  - system
thresholds: {}
```

### Integracja z CLI

```python
@click.command()
@click.option("--profile", "-p", help="Profil diagnostyczny (server/desktop/developer/minimal)")
@click.option("--modules", "-m", help="Lista modułów (nadpisuje profil)")
def scan(profile, modules, ...):
    if profile:
        prof = Profile.load(profile)
        modules = modules or prof.modules
        # apply thresholds...
    registry = PluginRegistry()
    registry.discover()
    results = registry.run(modules=modules)
```

## 5. Watch Mode

### Architektura

Daemon działający w tle, wykonujący cykliczną diagnostykę z powiadomieniami:

```python
# fixos/watch.py
import time
import subprocess
from fixos.plugins.registry import PluginRegistry
from fixos.plugins.base import Severity

class WatchDaemon:
    def __init__(self, interval: int, modules: list[str],
                 alert_on: Severity = Severity.CRITICAL):
        self.interval = interval
        self.modules = modules
        self.alert_on = alert_on
        self.registry = PluginRegistry()
        self.registry.discover()
        self._previous_findings: set[str] = set()

    def run(self):
        print(f"fixOS watch: co {self.interval}s, moduły: {self.modules}")
        while True:
            results = self.registry.run(modules=self.modules)
            new_alerts = self._check_for_new_issues(results)

            for alert in new_alerts:
                self._notify(alert)

            time.sleep(self.interval)

    def _check_for_new_issues(self, results) -> list[str]:
        current = set()
        alerts = []
        for r in results:
            for f in r.findings:
                key = f"{r.plugin_name}:{f.title}"
                current.add(key)
                if (key not in self._previous_findings
                    and f.severity.value >= self.alert_on.value):
                    alerts.append(
                        f"[{f.severity.value.upper()}] {r.plugin_name}: "
                        f"{f.title} — {f.description}"
                    )
        self._previous_findings = current
        return alerts

    def _notify(self, message: str):
        """Desktop notification (Linux: notify-send, macOS: osascript)."""
        import platform
        if platform.system() == "Linux":
            subprocess.run(
                ["notify-send", "fixOS Alert", message],
                capture_output=True,
            )
        elif platform.system() == "Darwin":
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{message}" with title "fixOS"'],
                capture_output=True,
            )
        # Zawsze loguj do terminala
        print(f"ALERT: {message}")
```

## Podsumowanie priorytetów implementacji

| Funkcja | Złożoność impl. | Impact na użytkownika | Zależności |
|---------|:---:|:---:|---|
| Plugin System | Wysoka | Bardzo wysoki | Wymaga refaktoryzacji system_checks |
| Structured Output | Średnia | Wysoki | Pydantic (nowa zależność) |
| Rollback System | Średnia | Wysoki | Rozszerzenie CommandExecutor |
| Profiles | Niska | Średni | Plugin System (opcjonalnie) |
| Watch Mode | Średnia | Średni | Plugin System |
| HTML/PDF Reports | Niska | Średni | Jinja2 (nowa zależność) |

Rekomendacja: rozpocząć od Structured Output (szybki zysk, poprawa niezawodności parsowania LLM), następnie Plugin System (fundamentalna zmiana architektury), potem Rollback i reszta.
