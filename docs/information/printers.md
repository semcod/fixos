---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "printers",
  "kind": "information",
  "version": 2,
  "title": "Diagnostyka i naprawa drukarek: fixos printers",
  "status": "proposed",
  "owner": "semcod/fixos",
  "scope": "repository",
  "created": "2026-11-17",
  "updated": "2026-11-18",
  "review_after": "2026-12-18",
  "source_revision": "0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/fixos/plugins/builtin/printers.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/fixos/plugins/builtin/printer_repairs.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/fixos/cli/printers_cmd.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/tests/unit/test_printer_repairs.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/tests/twin/printers/job_sink.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/tests/unit/test_printer_twin_sink.py"
  ]
}
---

# Diagnostyka i naprawa drukarek: fixos printers

<!-- docs:section purpose -->
## Cel

`fixos printers` wykrywa i naprawia typowe przyczyny, dla których drukarka
sieciowa „nie drukuje”, choć jest włączona i podłączona do LAN. Bezpośrednim
powodem powstania była drukarka Brother HL-L5200DW, której kolejka CUPS
wskazywała `lpd://BRN3C2AF4E8C6F8/BINARY_P1`: tej nazwy NetBIOS nie
rozwiązywał ani DNS, ani mDNS, więc zadania wisiały, aż CUPS je przerywał.

<!-- docs:section scope -->
## Zakres

- Linux i macOS: CUPS (`lpstat`, `lpoptions`, `ipptool`, `lpadmin`).
- Windows: usługa Spooler przez PowerShell (`Get-Printer`, `Get-PrinterPort`,
  `Get-PrintJob`, `Add-PrinterPort`, `Set-Printer`).
- Opcjonalna wielowęzłowa sonda osiągalności drukarki z interfejsów i węzłów
  LAN/SSH: `fixos printers --mesh`.
- Wtyczka `printers` jest też uruchamiana przez `fixos quickfix`.

Wykrywane problemy:

| Problem | Ważność | Naprawa |
|---|---|---|
| nazwa drukarki nie rozwiązuje się (np. `BRN…`, `BRW…`, `NPI…`) | CRITICAL | przepięcie kolejki na `ipp://<IP>/ipp/print` z IPP Everywhere (Windows: port TCP/IP na IP) |
| drukarka nie odpowiada na porcie kolejki | CRITICAL | brak automatycznej; wskazówka o zasilaniu, sieci i rezerwacji DHCP |
| kolejka wstrzymana lub odrzuca zadania | WARNING | `cupsenable` + `cupsaccept` (Windows: `Resume-Printer`) |
| zadania w kolejce dłużej niż 5 minut | WARNING | `cancel -a` (Windows: `Remove-PrintJob`) |
| sterownik ogólny albo stara kolejka LPD/9100 dla drukarki obsługującej druk bez sterownika | WARNING | przepięcie na IPP Everywhere |
| drukarka zgłasza aktywne błędy/ostrzeżenia w `printer-state-reasons` | WARNING | wskazówka (papier, toner, pokrywa); każdy token oceniany niezależnie |
| zatrzymany CUPS / Spooler | CRITICAL | `systemctl enable --now cups` (Windows: `Restart-Service Spooler`) |

<!-- docs:section evidence -->
## Dowody

Źródło: ticket-139 (PR 182, commit 8524601), ticket-140 (PR 184, commit
2984f88), ticket-145 (PR 190, commit 56da4fa — zamknięcie `#183`) oraz
ticket-146 (PR 191, commit 06636db — zamknięcie `#185`). **39 testów
jednostkowych wtyczki i napraw PASS** oraz **5 testów pętli zwrotnej ujścia
twin sink PASS**, Ruff PASS, testy CI na Pythonie 3.10–3.12 oraz Alpine, Arch,
Debian, Fedora i Ubuntu PASS.

Uruchomienie na rzeczywistym sprzęcie (Brother HL-L5200DW, `192.168.188.158`):
kolejka przepięta na IPP Everywhere poprawnie wydrukowała stronę testową, a przy
pustym podajniku `fixos printers` wykrył `printer-state-reasons = media-empty-warning`.

Digital twin (`tests/twin/printers`): emulowana drukarka laserowa z nazwą
`BRN3C2AF4000001` (IPP Everywhere, LPD, 9100) i maszyny libvirt (Ubuntu 24.04.5
— 19/19 PASS, Fedora 43 — 19/19 PASS). W ticket-146 `LpdHandler` został
wzmocniony tak, aby wymagał pełnych `size + 1` bajtów z końcowym bajtem `NUL`
(`\x00`) przed potwierdzeniem i zapisem zadania w katalogu spoolera.

Ścieżka Windows jest sprawdzona wyłącznie testami jednostkowymi z walidacją
skryptów `-EncodedCommand` UTF-16LE; nie była uruchomiona na systemie Windows.

<!-- docs:section content -->
## Użycie i decyzje

```bash
fixos printers                     # diagnoza
fixos printers --scan              # odszukaj drukarkę w lokalnej sieci /24 po MAC
fixos printers --mesh              # diagnoza CUPS/Spooler + siatka osiągalności mesh
fixos printers --fix               # wykonaj proponowane naprawy (z potwierdzeniem)
fixos printers --fix -y --scan     # bez pytań, z wyszukiwaniem w sieci
fixos printers --test-print NAZWA  # strona testowa, czeka na zakończenie zadania
fixos printers --json              # wynik maszynowy
```

Decyzje projektowe:

- **Niezależna ocena tokenów IPP (`active_fault_reasons`).** Każdy element listy
  `printer-state-reasons` rozdzielanej przecinkami jest analizowany osobno,
  dzięki czemu końcowy token informacyjny `-report` (np.
  `media-empty-error,toner-low-report`) nigdy nie ukrywa rzeczywistych awarii.
- **Naprawy bez powłoki (`shell=False`).** `fixos/plugins/builtin/printer_repairs.py`
  waliduje nazwę kolejki oraz literał IPv4/IPv6 i buduje jawne wektory `argv`
  uruchamiane przez `subprocess.run(..., shell=False)` (na Windows przez
  PowerShell `-EncodedCommand` w UTF-16LE), zachowując potwierdzenie
  interaktywne i raportowanie kodów błędów.
- **Odszukiwanie po MAC i kopia konfiguracji.** Nazwy `BRN`/`BRW`/`NPI` są
  dopasowywane w tablicy ARP (`--scan` pobudza lokalną sieć `/24`), a na
  Linuksie przepięcie kolejki zapisuje kopię `/etc/cups/printers.conf.bak-<data>`.

<!-- docs:section limitations -->
## Ograniczenia

- Przepięcie kolejki na adres IP działa, dopóki drukarka go nie zmieni.
  Trwałym rozwiązaniem jest rezerwacja DHCP albo włączenie Bonjour/mDNS w
  drukarce.
- `--scan` obejmuje tylko sieć /24 interfejsu z trasą domyślną.
- Nie instaluje pakietów sterowników ani nie konfiguruje drukarek USB.
- Na Windows kolejka wstrzymana jest rozpoznawana po `PrinterStatus=Paused`;
  inne stany błędów Spoolera nie są mapowane.

<!-- docs:section next_actions -->
## Następne kroki

- Dodać do twina gościa Windows, gdy na hoście testowym będzie ~20 GB wolnego
  miejsca i obraz ewaluacyjny.
- Rozszerzyć mapowanie kodów błędów Windows Spooler poza stan `Paused`.

<!-- docs:section history -->
## Historia

- Wersja 1: polecenie `fixos printers` z ticket-139 (8524601), digital twin z
  ticket-140 (2984f88), dokumentacja i wydanie 2.5.0 w ticket-141.
- Wersja 2: niezależna ocena powodów IPP i wykonanie napraw bez powłoki w
  ticket-145 (56da4fa), walidacja uciętych zadań LPD w twinie w ticket-146
  (06636db) oraz podbicie pakietu do 2.6.1 w ticket-148.
