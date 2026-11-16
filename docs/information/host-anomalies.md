---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "host-anomalies",
  "kind": "information",
  "version": 1,
  "title": "Wykrywanie anomalii hosta poza zwykłym czyszczeniem cache",
  "status": "proposed",
  "owner": "semcod/fixos",
  "created": "2026-11-16",
  "updated": "2026-11-16",
  "review_after": "2026-12-16",
  "source_revision": "e5947fdc66774dfb41bedbfaeedff4e4248dc67f",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/blob/e5947fdc66774dfb41bedbfaeedff4e4248dc67f/fixos/diagnostics/host_anomalies.py",
    "https://github.com/semcod/fixos/blob/e5947fdc66774dfb41bedbfaeedff4e4248dc67f/fixos/cli/anomalies_cmd.py",
    "https://github.com/semcod/fixos/blob/e5947fdc66774dfb41bedbfaeedff4e4248dc67f/tests/unit/test_host_anomalies.py"
  ]
}
---

# Wykrywanie anomalii hosta poza zwykłym czyszczeniem cache

<!-- docs:section purpose -->
## Cel

`fixos anomalies` wykrywa przyczyny obciążenia i braku miejsca, których nie
widzą `fixos auto` ani `fixos cleanup`: usługi w pętli restartów, logi
kontenerów bez rotacji, duże nieruszane katalogi w magazynach stanu narzędzi,
odtwarzalne indeksy IDE oraz procesy zombie i grupy zawieszonych procesów.
Detektory działają lokalnie, bez LLM i bez zmian w systemie.

<!-- docs:section scope -->
## Zakres

| Kategoria | Co jest zgłaszane | Ważność |
| --- | --- | --- |
| `restart-loop` | jednostki systemd (systemowe i użytkownika) z `NRestarts` ≥ 50 w stanie `auto-restart` albo z ≥ 500 restartami | `high` w pętli, inaczej `medium` |
| `container-logs` | brak `log-opts.max-size` w `/etc/docker/daemon.json`; logi `*-json.log` ≥ 100 MiB | `medium`, `low` |
| `stale-state` | najwyższy katalog w `~/.local/state` lub `~/.local/share` o rozmiarze ≥ progu, w którym nic nie zmieniono od N dni | `review` |
| `ide-index` | katalog `~/.cache/JetBrains/<produkt>/index` ≥ progu | `safe`, a przy działającym IDE `protected` |
| `zombie-processes` | ≥ 10 procesów zombie pod jednym rodzicem | `medium` |
| `idle-process-group` | ≥ 50 uśpionych procesów starszych niż 24 h o identycznym pełnym poleceniu | `medium` |

Katalogi prywatne i magazyny poświadczeń (`Downloads`, `Documents`, `.ssh`,
`.gnupg` i pozostałe z listy `artifact_store.PROTECTED_HOME_DIRS`) nigdy nie są
kandydatami.

<!-- docs:section evidence -->
## Dowody

Źródło: ticket-136, commit e5947fd (PR 179). **10 testów jednostkowych PASS**,
Ruff PASS, natywna bramka governance PASS; testy CI na Pythonie 3.10–3.12 oraz
Alpine, Arch, Debian, Fedora i Ubuntu PASS.

Uruchomienie na hoście budującym 2026-11-16 zwróciło 23 ustalenia: 4 usługi w
pętli restartów (do 63 tys. restartów), 15 katalogów stanu o łącznym rozmiarze
45,7 GiB oraz 4 procesy-rodzice z 10–342 procesami zombie. Pierwsza wersja
błędnie zgłaszała `docker-proxy` i `containerd-shim` jako grupy zawieszonych
procesów; grupowanie po pełnym poleceniu usunęło te fałszywe alarmy i jest
objęte testem.

Dokument nie jest dowodem instalacji wersji 2.4.0 na konkretnym komputerze.

<!-- docs:section content -->
## Użycie i decyzje

```bash
# Raport czytelny dla człowieka
fixos anomalies

# Raport maszynowy (schemat fixos.host-anomalies/v1)
fixos anomalies --json

# Inne progi katalogów stanu i indeksów IDE
fixos anomalies --min-size-gb 5 --min-age-days 30

# Usuń indeksy IDE, które nie są w tej chwili używane
fixos anomalies --remove-safe

# Podgląd usunięcia wskazanego katalogu stanu
fixos anomalies --remove ~/.local/state/narzedzie/backups --dry-run
```

`--remove` i `--remove-safe` usuwają wyłącznie katalogi, które bieżący skan
nadal oznacza jako usuwalne (`stale-state` albo `ide-index` bez działającego
IDE), położone w katalogu domowym, niebędące dowiązaniem symbolicznym ani
katalogiem chronionym. Każde usunięcie zapisuje pokwitowanie
`fixos.host-anomaly-removal/v1` w `~/.local/state/fixos/receipts/`.

Pozostałe kategorie mają tylko podpowiedziane polecenia (`systemctl disable
--now`, wpis `log-opts` do `daemon.json`, `truncate`, `pgrep`). fixOS ich nie
wykonuje, bo zmieniają usługi i procesy należące do innych właścicieli.

`stale-state` ma zawsze ważność `review`: magazyny stanu zawierają zarówno
odtwarzalne kopie i obrazy, jak i pokwitowania oraz dowody. Przed usunięciem
sprawdź zawartość katalogu.

<!-- docs:section limitations -->
## Ograniczenia

Pomiar katalogów stanu używa `du` z limitem 30 minut na korzeń; na obciążonym
hoście z magazynem rzędu 100 GiB skan trwa kilkadziesiąt minut. Po
przekroczeniu limitu dany korzeń nie zwraca kandydatów, a raport tego nie
sygnalizuje.

„Bez zmian od N dni” opiera się na mtime plików, a nie na faktycznym użyciu;
dane tylko czytane wyglądają jak nieużywane. Otwarte uchwyty plików nie są
sprawdzane dla katalogów stanu.

Logi kontenerów wymagają uprawnień do odczytu `/var/lib/docker/containers`;
bez nich zgłaszany jest tylko brak rotacji. Detektor indeksów IDE obejmuje
wyłącznie produkty JetBrains. Procesy widoczne są tylko w bieżącej przestrzeni
nazw PID.

<!-- docs:section next_actions -->
## Następne kroki

Zasygnalizować w raporcie korzeń, którego pomiar przekroczył limit czasu.
Dodać kontrolę otwartych uchwytów przed oznaczeniem katalogu stanu jako
kandydata. Rozważyć dołączenie raportu do `fixos auto --dry-run`.
[Diagnostyka dużych plików](storage-triage.md).

<!-- docs:section history -->
## Historia

- Wersja 1: polecenie `fixos anomalies` z ticket-136 (e5947fd), dokumentacja i wydanie 2.4.0 w ticket-137. Liczby opisują sprawdzony commit i jedno uruchomienie na hoście budującym; nie dowodzą publikacji pakietu na PyPI.
