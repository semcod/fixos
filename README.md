```
  ___  _       ___  ____
 / _(_)_  __  / _ \/ ___|
| |_| \ \/ / | | | \___ \
|  _| |>  <  | |_| |___) |
|_| |_/_/\_\  \___/|____/
AI-powered OS Diagnostics
```

# fixOS v2.2.6 🔧🤖

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/badge/github-wronai%2Ffixos-black?logo=github)](https://github.com/wronai/fixos)
[![Providers](https://img.shields.io/badge/LLM%20providers-12-orange)](https://github.com/wronai/fixos#-dostępni-providerzy-llm-12)
[![Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)](https://github.com/wronai/fixos)
[![Tests](https://img.shields.io/badge/tests-274%20passing-brightgreen)](https://github.com/wronai/fixos/actions)


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-2.2.40-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$4.85-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-38.2h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $4.8451 (147 commits)
- 👤 **Human dev:** ~$3817 (38.2h @ $100/h, 30min dedup)

Generated on 2026-07-23 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---

**AI diagnostyka i naprawa systemów** – Linux, Windows, macOS  
z anonimizacją danych, trybem HITL/Autonomous, grafem problemów i 12 providerami LLM.

> 🔗 **GitHub**: https://github.com/wronai/fixos

---

![img_1.png](img_1.png)

## 🌍 Cross-Platform Support

| System | Package Manager | Audio | Hardware | System |
|:--|:--|:--:|:--:|:--:|
| **Linux** (Fedora, Ubuntu, Arch, Debian) | dnf / apt / pacman | ✅ ALSA/PipeWire/SOF | ✅ DMI/sensors | ✅ systemd/journal |
| **Windows** 10/11 | winget / choco | ✅ WMI Audio | ✅ WMI Hardware | ✅ Event Log |
| **macOS** 12+ | brew | ✅ CoreAudio | ✅ system_profiler | ✅ launchd |

---

## Szybki start (3 kroki)

```bash
# 1. Instalacja
pip install -e ".[dev]"

# 2. Pierwszy lokalny wynik bez LLM
fixos quick                        # CPU/RAM/dysk/cache + początek historii

# 3. Opcjonalnie wybierz provider i uruchom analizę pogłębioną
fixos llm                          # lista 12 providerów z linkami
fixos token set AIzaSy...          # Gemini (darmowy, domyślny)
fixos fix
```

---

## Komendy CLI

```
fixos                   – ekran powitalny z listą komend i statusem
fixos quick             – szybka analiza bez LLM + historia CPU/RAM/dysku
fixos quick --deep      – szybki wynik, potem pełny skan danych usług
fixos fix               – diagnoza + sesja naprawcza z AI (HITL)
fixos scan              – diagnostyka systemu bez AI
fixos cleanup           – skanuj i czyść dane usług (Docker, npm, pip, ...)
fixos cleanup --full    – pełny audit systemu + dev projects
fixos projects          – skanuj projekty dev (venv, node_modules, ~/github/*/*)
fixos orchestrate       – zaawansowana orkiestracja (graf problemów DAG)
fixos llm               – lista 12 providerów LLM + linki do kluczy API
fixos token set KEY     – zapisz klucz API do .env (auto-detekcja providera)
fixos token show        – pokaż aktualny token (zamaskowany)
fixos token clear       – usuń token z .env
fixos config show       – pokaż konfigurację
fixos config init       – utwórz .env z szablonu
fixos config set K V    – ustaw wartość w .env
fixos providers         – skrócona lista providerów
fixos test-llm          – testuj połączenie z LLM
```

### Przykłady użycia

```bash
# Wynik w kilka sekund: presja CPU/RAM/dysku, bezpieczne cache i ostatni przyrost
fixos quick

# JSON do monitoringu; porównanie z próbkami z ostatnich 12 godzin
fixos quick --json --hours 12

# Dopiero na żądanie wykonaj kosztowną inwentaryzację usług
fixos quick --deep

# Tylko diagnostyka audio + zapis do pliku
fixos scan --audio --output /tmp/audio-report.json

# Analiza i interaktywne czyszczenie zajętości dysku
fixos fix --disc

# Pełny audit systemu (DNF, Docker, Flatpak, dev projects)
fixos cleanup --full --dry-run

# Usuń tylko foldery venv z projektów
fixos cleanup --full
> type:venv

# Usuń duże elementy (>1 GB)
fixos cleanup --full
> large

# Interaktywny wybór elementów do usunięcia
fixos cleanup --full
> select
> 1,3,5-10

# Skanuj ~/github/*/* pod kątem venv/.venv, node_modules, cache kompilacji...
fixos projects

# Tylko artefakty nieużywane od >60 dni (bez świeżych venv)
fixos projects --only-stale

# Podgląd bez usuwania
fixos projects --dry-run

# Napraw audio i thumbnails (HITL – pyta o potwierdzenie)
fixos fix --modules audio,thumbnails

# Domyślny szybki zestaw pomija wielokrotny skan całego katalogu domowego.
# Pełną inwentaryzację dużych/zdublowanych plików uruchom jawnie:
fixos fix --modules all

# Tryb autonomiczny (agent sam naprawia, max 5 akcji)
fixos fix --mode autonomous --max-fixes 5

# Zaawansowana orkiestracja z grafem zależności
fixos orchestrate --dry-run

# Pokaż tylko darmowe providery LLM
fixos llm --free

# Ustaw Groq jako provider (ultra-szybki, darmowy)
fixos token set gsk_... --provider groq
fixos fix --provider groq

# Timeout 30 minut
fixos fix --timeout 1800
```

`fixos quick` nie wywołuje LLM ani nie przeszukuje całego katalogu domowego.
Pierwsze uruchomienie zapisuje mały punkt odniesienia w
`~/.local/state/fixos/quick-history.json`; kolejne pokazują zmianę dysku, RAM,
swapu i znanych cache w wybranym oknie oraz od początku bieżącego dnia. Kwota
„bezpieczne cache” obejmuje wyłącznie jawnie odtwarzalne dane. Docker, modele
AI, rozszerzenia i cache IDE są raportowane osobno jako wymagające decyzji.

### Przykładowy widok w terminalu (Czyszczenie dysku)

Wyjście jest zoptymalizowane pod standardowy Markdown bez nadmiernej ilości symboli Unicode, ułatwiając czytelność i wklejanie:

```bash
$ fixos fix --disk --dry-run

  ___  _       ___  ____
 / _(_)_  __  / _ \/ ___|
| |_| \ \/ / | | | \___|
|  _| |>  <  | |_| |___) |
|_| |_/_/\_\  \___/|____/
  AI-powered OS Diagnostics  •  v2.0.0

Konfiguracja:
  Tryb: DRY-RUN (komendy nie będą wykonywane)
  Analiza dysku: Włączona
Analizowanie zajętości dysku...
  Dysk: 93.9% zajęty (1759.0GB / 1873.7GB)
  Można bezpiecznie zwolnić: 0.7GB w 3 akcjach
Diagnostyka gotowa.

Plan czyszczenia dysku:
  🔢 Akcje: 8
  Miejsce: 262255.3 GB
  Bezpieczne: 0.7 GB
  📂 Kategorie: 6

 Cache Files:
  📁 Akcje: 1
  Miejsce: 0.6 GB
      Clear application cache (0.6GB)

 Temporary Files:
  📁 Akcje: 1
  Miejsce: 0.1 GB
      Clean system_temp temporary files (0.1GB)

Rekomendacje:
  🎯 Cache Cleanup Recommended
     Clear application cache to free 0.6 GB
  🎯 Log Files Can Be Cleaned
     Clean old logs to free 0.7 GB

Tryb DRY-RUN - żadne akcje nie zostaną wykonane
```

### `fixos cleanup` – 3 poziomy ryzyka

Każda znaleziona usługa jest klasyfikowana do jednej z trzech grup:

- **bezpieczne** – cache do odtworzenia jednym poleceniem (pip/npm/cargo/conda/nix/brew...).
  Jedyna grupa oferowana do automatycznego usunięcia, z menu wyboru: wszystkie / pojedynczo / pomiń.
- **do rozważenia** – reinstalowalne aplikacje, dane długo nieużywane, nierozpoznane
  foldery (JetBrains, Snap, Flatpak) – pokazywane z podpowiedziami, nigdy nie usuwane automatycznie.
- **chronione lub mieszane** – realne dane aplikacji albo magazyny łączące dane aktywne
  z cache (Ollama, LM Studio, HuggingFace hub, Docker/Podman/containerd, cała biblioteka
  Steam, `.cursor/extensions`/`.vscode/extensions`
  – zainstalowane rozszerzenia edytora, nie ich cache). Osobna sekcja z ostrzeżeniem;
  zbiorcze kasowanie modeli i wolumenów jest wyłączone. Docker pokazuje osobno
  `SIZE` i `RECLAIMABLE`; domyślne czyszczenie ogranicza się do starego cache buildów.

### `fixos projects` – skaner artefaktów w projektach deweloperskich

Osobne narzędzie od `fixos cleanup` – zamiast globalnych ścieżek cache (`~/.cache/...`)
rekurencyjnie skanuje drzewo Twoich projektów (domyślnie `~/github/*/*`, dowolna
ścieżka przez `--path`) i wykrywa usuwalne artefakty per-projekt: `venv`/`.venv`
(zweryfikowane po `pyvenv.cfg`, żeby nie trafić na przypadkowy folder o tej
nazwie), `node_modules`/`.next`/`.turbo` (tylko gdy jest `package.json`),
`target` (tylko gdy jest `Cargo.toml`), `__pycache__`, `.pytest_cache`,
`.mypy_cache`, `.ruff_cache`, `.tox`, `.nox`; `dist`/`build` osobno jako
"do rozważenia" (mogą zawierać coś do opublikowania). Flaguje artefakty
nieużywane od >60 dni (`--stale-days`) oraz projekty ze zduplikowanymi
virtualenvami (np. i `venv`, i `.venv` naraz).

```bash
$ fixos projects --only-stale

Skanowanie projektów w /home/tom/github (próg: 50 MB)...
════════════════════════════════════════════════════════════
Znaleziono 91 artefaktów w 68 projektach:
  Całkowity rozmiar: 91.90 GB
  Bezpieczne: 91.10 GB
  Do rozważenia: 0.80 GB
  Nieużywane od >60 dni: 91.90 GB

  ⚠ 12 projekt(ów) ma więcej niż jeden virtualenv naraz (np. venv + .venv):
    • /home/tom/github/semcod/fixOS

  streamware/venv - 9.27 GB — nieużywany 216 dni
   Python virtualenv
   Ścieżka: /home/tom/github/stream-ware/streamware/venv
   (bezpieczne)
  ...

Co wyczyścić?
  [1] Wszystkie bezpieczne (91.10 GB)
  [2] Tylko dawno nieużywane (91.90 GB, 91 art.)
  [3] Wybierz wg ekosystemu (Python/Node/Rust/...)
  [4] Wybierz wg projektu
  [5] Wybierz pojedyncze artefakty
  [0] Nic — pomiń
Wybór [1]: 4

  [1] stream-ware/streamware — 9.27 GB (1 art.)
  [2] prototypowanie/raport — 8.30 GB (1 art.)
  [3] stream-ware/edge — 7.68 GB (1 art.)
  ...
Numery po przecinku (np. 1,3,5), 'all' dla wszystkich, Enter by pominąć: 1,3
```

Inne opcje: `--list` (tylko podgląd bez interakcji), `--json`, `--max-depth`,
`--threshold`.

---

## 🤖 Dostępni Providerzy LLM (12)

| # | Provider | Tier | Model domyślny | Klucz API |
|:--|:--|:--:|:--|:--|
| 1 | **gemini** | 🟢 FREE | gemini-2.5-flash | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| 2 | **openrouter** | 🟢 FREE | openai/gpt-4o-mini | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) |
| 3 | **mistral** | 🟢 FREE | mistral-small-latest | [console.mistral.ai](https://console.mistral.ai/api-keys/) |
| 4 | **groq** | 🟢 FREE | llama-3.1-8b-instant | [console.groq.com/keys](https://console.groq.com/keys) |
| 5 | **together** | 🟢 FREE | llama-3.2-11B | [api.together.ai](https://api.together.ai/settings/api-keys) |
| 6 | **cohere** | 🟢 FREE | command-r | [dashboard.cohere.com](https://dashboard.cohere.com/api-keys) |
| 7 | **cerebras** | 🟢 FREE | llama3.1-8b | [cloud.cerebras.ai](https://cloud.cerebras.ai/platform/) |
| 8 | **ollama** | 🟢 LOCAL | llama3.2 | [ollama.com/download](https://ollama.com/download) |
| 9 | **openai** | 💰 PAID | gpt-4o-mini | [platform.openai.com](https://platform.openai.com/api-keys) |
| 10 | **anthropic** | 💰 PAID | claude-3-haiku | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| 11 | **xai** | 💰 PAID | grok-beta | [console.x.ai](https://console.x.ai/) |
| 12 | **deepseek** | 💰 PAID | deepseek-chat | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |

```bash
fixos llm          # pełna lista z opisami i gotowymi komendami
fixos llm --free   # tylko darmowe
```

---

## Tryby agenta

### 👤 Human-in-the-Loop (HITL) – domyślny

```
LLM sugeruje → Ty decydujesz → Skrypt wykonuje

fixos [00:58:42] ❯ 1              ← napraw problem nr 1
fixos [00:58:30] ❯ A              ← napraw wszystkie
fixos [00:58:20] ❯ !systemctl status pipewire  ← własna komenda
fixos [00:58:10] ❯ search sof-firmware lenovo  ← szukaj zewnętrznie
fixos [00:57:55] ❯ D              ← opisz własny problem
fixos [00:57:40] ❯ ?              ← zapytaj o szczegóły
fixos [00:57:30] ❯ q              ← zakończ
```

Wyjście koloryzowane: 🔴 krytyczne / 🟡 ważne / 🟢 drobne, bloki kodu z ramkami box-drawing.

### 🤖 Autonomous – agent działa samodzielnie

```bash
fixos fix --mode autonomous --max-fixes 10
```
- Protokół JSON: `{ "action": "EXEC|SEARCH|SKIP|DONE", "command": "...", "reason": "..." }`
- Zabezpieczenia: lista zabronionych komend (`rm -rf /`, `mkfs`, `fdisk`, `dd if=...`)
- Każde `EXEC` logowane z wynikiem i oceną LLM
- Wymaga jawnego `yes` na starcie

### 🎼 Orchestrate – graf problemów (DAG)

```bash
fixos orchestrate
fixos orchestrate --dry-run   # podgląd bez wykonywania
```
- Buduje graf zależności między problemami
- Po każdej naprawie re-diagnozuje i wykrywa nowe problemy
- LLM ocenia wynik każdej komendy (JSON structured output)

---

## 🔒 Anonimizacja danych

Zawsze pokazywana przed wysłaniem do LLM. Maskowane kategorie:

| Kategoria | Przykład | Zamiennik |
|:--|:--|:--|
| Hostname | `moj-laptop` | `[HOSTNAME]` |
| Username | `jan` | `[USER]` |
| Ścieżki /home | `/home/jan/.pyenv/versions/3.12/bin/python` | `/home/[USER]/...` |
| Adresy IPv4 | `192.168.1.100` | `192.168.XXX.XXX` |
| Adresy MAC | `aa:bb:cc:dd:ee:ff` | `XX:XX:XX:XX:XX:XX` |
| Tokeny API | `sk-abc123...` | `[API_TOKEN_REDACTED]` |
| UUID hardware | `a1b2c3d4-...` | `[UUID-REDACTED]` |
| Numery seryjne | `SN: PF1234567` | `Serial: [SERIAL-REDACTED]` |
| Hasła w env | `PASSWORD=secret` | `PASSWORD=[REDACTED]` |

---

## Moduły diagnostyki

| Moduł | Linux | Windows | macOS | Co sprawdza |
|:--|:--:|:--:|:--:|:--|
| `system` | ✅ | ✅ | ✅ | CPU, RAM, dyski, usługi, aktualizacje, SELinux, firewall |
| `audio` | ✅ | ✅ | ✅ | ALSA/PipeWire/SOF (Linux), WMI Audio (Win), CoreAudio (Mac) |
| `thumbnails` | ✅ | ➖ | ➖ | ffmpegthumbnailer, cache, GNOME gsettings |
| `hardware` | ✅ | ✅ | ✅ | DMI/WMI/system_profiler, BIOS, GPU, czujniki, bateria |
| `security` | ✅ | ✅ | ✅ | Firewall, otwarte porty, SELinux/AppArmor, SSH config, fail2ban, SUID |
| `resources` | ✅ | ✅ | ✅ | Co zajmuje dysk, top procesów CPU/RAM, autostart, OOM events |

```bash
# Tylko bezpieczeństwo
fixos scan --modules security

# Zasoby – co zajmuje dysk i pamięć
fixos scan --modules resources

# Pełna diagnostyka z naprawą
fixos fix --modules system,security,resources
```

---

## Zewnętrzne źródła wiedzy (fallback)

Gdy LLM nie zna rozwiązania, fixos szuka automatycznie w:

- **Fedora Bugzilla** – baza zgłoszonych błędów
- **ask.fedoraproject.org** – forum społeczności
- **Arch Wiki** – doskonałe źródło dla ogólnych problemów Linux
- **GitHub Issues** – PipeWire, ALSA, linux-hardware repos
- **DuckDuckGo** – ogólne wyszukiwanie (bez klucza API)
- **Google via SerpAPI** – najlepsze wyniki (opcjonalny klucz `SERPAPI_KEY`)

---

## Konfiguracja (.env)

```bash
fixos config init    # utwórz .env z szablonu
fixos config show    # sprawdź aktualną konfigurację
```

```env
LLM_PROVIDER=gemini           # gemini|openai|openrouter|groq|mistral|...
GEMINI_API_KEY=AIzaSy...      # klucz Gemini (darmowy)
AGENT_MODE=hitl               # hitl|autonomous
SHOW_ANONYMIZED_DATA=true     # pokaż dane przed wysłaniem
ENABLE_WEB_SEARCH=true        # fallback do zewnętrznych źródeł
SESSION_TIMEOUT=3600          # timeout sesji (1h)
SERPAPI_KEY=                  # opcjonalny – lepsze wyniki wyszukiwania

# Opcjonalnie: konkretny model dla danego providera + modele zapasowe.
# Jeśli główny model zostanie odrzucony przez providera jako nieprawidłowy
# (błąd 400 "not a valid model ID"), klient automatycznie przechodzi na
# kolejny z listy – bez żadnej akcji z Twojej strony.
OPENROUTER_MODEL=openrouter/qwen/qwen3.7-plus
OPENROUTER_MODEL_FALLBACKS=minimax/minimax-m3,google/gemini-2.5-flash-lite
```

---

## Testy i Docker

### Uruchomienie testów

```bash
# Wszystkie testy jednostkowe (bez API, szybkie)
pytest tests/unit/ -v

# Testy e2e z mock LLM
pytest tests/e2e/ -v

# Tylko testy z prawdziwym API (wymaga tokena w .env)
pytest tests/e2e/ -v -m real_api

# Pokrycie kodu
pytest --cov=fixos --cov-report=html
make test-coverage
```

### Docker – symulowane środowiska

```bash
# Zbuduj wszystkie obrazy
docker compose -f docker/docker-compose.yml build

# Scenariusze broken
docker compose -f docker/docker-compose.yml run broken-audio
docker compose -f docker/docker-compose.yml run broken-thumbnails
docker compose -f docker/docker-compose.yml run broken-network
docker compose -f docker/docker-compose.yml run broken-full

# Uruchom testy e2e w Dockerze
docker compose -f docker/docker-compose.yml run e2e-tests
```

### Środowiska Docker

| Obraz | Scenariusz |
|:--|:--|
| `fixos-broken-audio` | Brak sof-firmware, PipeWire failed, no ALSA cards |
| `fixos-broken-thumbnails` | Brak thumbnailerów, pusty cache, brak GStreamer |
| `fixos-broken-network` | NetworkManager failed, DNS broken, rfkill blocked |
| `fixos-broken-full` | Wszystkie problemy naraz + pending updates + failed services |

---

## Struktura projektu

```
fixos/
├── fixos/
│   ├── cli.py                  # Komendy CLI (Click) – fixos, fix, scan, llm, ...
│   ├── config.py               # Konfiguracja + 12 providerów LLM
│   ├── platform_utils.py       # Cross-platform (Linux/Win/Mac)
│   ├── agent/
│   │   ├── hitl.py             # HITL z koloryzowanym markdown output
│   │   └── autonomous.py       # Tryb autonomiczny z JSON protokołem
│   ├── diagnostics/
│   │   └── system_checks.py    # Moduły: system, audio, thumbnails, hardware
│   ├── fixes/
│   │   ├── knowledge_base.py   # Baza znanych bugów z heurystykami
│   │   └── heuristics.py       # Matcher diagnostics → known fixes
│   ├── orchestrator/
│   │   ├── graph.py            # Graf problemów (DAG)
│   │   ├── executor.py         # Bezpieczny executor komend
│   │   └── orchestrator.py     # Główna pętla orkiestracji
│   ├── providers/
│   │   └── llm.py              # Multi-provider LLM client
│   └── utils/
│       ├── anonymizer.py       # Anonimizacja z raportem
│       └── web_search.py       # Bugzilla/AskFedora/ArchWiki/GitHub/DDG
├── tests/
│   ├── conftest.py             # Fixtures + mock diagnostics
│   ├── e2e/
│   │   ├── test_audio_broken.py
│   │   ├── test_thumbnails_broken.py
│   │   ├── test_network_broken.py
│   │   ├── test_executor.py
│   │   └── test_cli.py
│   └── unit/
│       ├── test_core.py
│       ├── test_anonymizer.py
│       └── test_executor.py
├── docker/
│   ├── base/Dockerfile
│   ├── broken-audio/Dockerfile
│   ├── broken-thumbnails/Dockerfile
│   ├── broken-network/Dockerfile
│   └── broken-full/Dockerfile
├── .env.example
├── pytest.ini
└── pyproject.toml
```

---

## 📋 Roadmap

Zobacz pełną listę zadań i roadmap w pliku [TODO.md](./TODO.md)

---

## 🚀 Jak używać fixOS (Prosty przewodnik)

### Krok 1: Instalacja
```bash
pip install -e ".[dev]"
```

### Krok 2: Konfiguracja
```bash
# Utwórz plik .env z szablonu
fixos config init

# Ustaw klucz API (darmowy Gemini)
fixos token set AIzaSy...

# Lub wybierz innego providera
fixos llm --free    # pokaż darmowe providery
```

### Krok 3: Użycie
```bash
# Zobacz dostępne komendy
fixos

# Diagnostyka systemu (bez AI)
fixos scan

# Naprawa z AI (pyta o potwierdzenie)
fixos fix

# Naprawa automatyczna (bez pytania)
fixos fix --mode autonomous --max-fixes 5
```

### Przydatne przykłady
```bash
# Tylko audio
fixos fix --modules audio

# Zapisz wynik do pliku
fixos scan --output raport.json

# Timeout 30 minut
fixos fix --timeout 1800

# Podgląd orkiestracji
fixos orchestrate --dry-run
```

### 🔗 Linki
- **GitHub**: https://github.com/wronai/fixos
- **Pełna dokumentacja**: [TODO.md](./TODO.md)
---

## Licencja

Apache License 2.0 – see [LICENSE](LICENSE) for details.

## License

Licensed under Apache-2.0.
## Author

Tom Sapletta
## life is life

![img.png](img.png)
