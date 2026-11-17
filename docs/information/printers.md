---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "printers",
  "kind": "information",
  "version": 1,
  "title": "Diagnostyka i naprawa drukarek: fixos printers",
  "status": "proposed",
  "owner": "semcod/fixos",
  "scope": "repository",
  "created": "2026-11-17",
  "updated": "2026-11-17",
  "review_after": "2026-12-17",
  "source_revision": "2984f88572fbdb7d69fc8461bcd0870b09a0d778",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/blob/2984f88572fbdb7d69fc8461bcd0870b09a0d778/fixos/plugins/builtin/printers.py",
    "https://github.com/semcod/fixos/blob/2984f88572fbdb7d69fc8461bcd0870b09a0d778/fixos/cli/printers_cmd.py",
    "https://github.com/semcod/fixos/blob/2984f88572fbdb7d69fc8461bcd0870b09a0d778/tests/unit/test_printers_plugin.py",
    "https://github.com/semcod/fixos/blob/2984f88572fbdb7d69fc8461bcd0870b09a0d778/tests/twin/printers/README.md"
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
- Wtyczka `printers` jest też uruchamiana przez `fixos quickfix`.

Wykrywane problemy:

| Problem | Ważność | Naprawa |
|---|---|---|
| nazwa drukarki nie rozwiązuje się (np. `BRN…`, `BRW…`, `NPI…`) | CRITICAL | przepięcie kolejki na `ipp://<IP>/ipp/print` z IPP Everywhere (Windows: port TCP/IP na IP) |
| drukarka nie odpowiada na porcie kolejki | CRITICAL | brak automatycznej; wskazówka o zasilaniu, sieci i rezerwacji DHCP |
| kolejka wstrzymana lub odrzuca zadania | WARNING | `cupsenable` + `cupsaccept` (Windows: `Resume-Printer`) |
| zadania w kolejce dłużej niż 5 minut | WARNING | `cancel -a` (Windows: `Remove-PrintJob`) |
| sterownik ogólny albo stara kolejka LPD/9100 dla drukarki obsługującej druk bez sterownika | WARNING | przepięcie na IPP Everywhere |
| drukarka zgłasza `printer-state-reasons` | WARNING | wskazówka (papier, toner, pokrywa) |
| zatrzymany CUPS / Spooler | CRITICAL | `systemctl enable --now cups` (Windows: `Restart-Service Spooler`) |

<!-- docs:section evidence -->
## Dowody

Źródło: ticket-139 (PR 182, commit 8524601) i ticket-140 (PR 184, commit
2984f88). **16 testów jednostkowych PASS**, Ruff PASS, testy CI na Pythonie
3.10–3.12 oraz Alpine, Arch, Debian, Fedora i Ubuntu PASS.

Uruchomienie na rzeczywistym sprzęcie 2026-11-17: Brother HL-L5200DW w LAN po
przepięciu kolejki na IPP Everywhere zwrócił „Brak problemów”, a
`--test-print` wydrukował stronę. Tymczasowa kolejka z dawnym URI
`lpd://BRN3C2AF4E8C6F8/…` została wykryta, drukarka odnaleziona po MAC pod
192.168.188.158 i naprawiona przez `--fix -y`.

Digital twin (`tests/twin/printers`): emulowana drukarka laserowa z nazwą
`BRN3C2AF4000001` (IPP Everywhere, LPD, 9100) i maszyny libvirt. Dziewięć
scenariuszy awarii: **Ubuntu 24.04.5 — 19/19 kontroli PASS, Fedora 43 — 19/19
kontroli PASS**; emulator odebrał stronę testową z obu maszyn.

Ścieżka Windows jest sprawdzona wyłącznie testami jednostkowymi z nagranymi
wynikami PowerShell; nie była uruchomiona na systemie Windows.

<!-- docs:section content -->
## Użycie i decyzje

```bash
fixos printers                     # diagnoza
fixos printers --scan              # odszukaj drukarkę w lokalnej sieci /24 po MAC
fixos printers --fix               # wykonaj proponowane naprawy (z potwierdzeniem)
fixos printers --fix -y --scan     # bez pytań, z wyszukiwaniem w sieci
fixos printers --test-print NAZWA  # strona testowa, czeka na zakończenie zadania
fixos printers --json              # wynik maszynowy
```

Decyzje projektowe:

- **Odszukiwanie po MAC.** Nazwy Brother `BRN`/`BRW` zawierają pełny MAC,
  HP `NPI` jego końcówkę. fixos szuka go w tablicy ARP (`ip neigh`,
  `arp -an`, `arp -a`). `--scan` najpierw łączy się z portem 631 każdego hosta
  lokalnej sieci /24 (maks. 1024 adresy, limit 0,3 s), żeby wypełnić ARP.
- **Brak naprawy na ślepo.** Gdy drukarki nie da się odnaleźć, wynik zawiera
  tylko wskazówkę, bez polecenia.
- **IPP Everywhere zamiast sterownika.** Gdy drukarka ogłasza
  `image/pwg-raster`, `image/urf` lub `application/pdf`, kolejka jest
  przepinana na `-m everywhere`; ogólne sterowniki PCL i kolejki raw są
  oznaczane jako przestarzałe.
- **Kopia konfiguracji.** Na Linuksie naprawa najpierw kopiuje
  `/etc/cups/printers.conf` do `printers.conf.bak-<data>`.

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

- Dodać do twina gościa Windows, gdy na hoście testowym będzie ~20 GB miejsca
  i obraz ewaluacyjny.
- Opublikować wersję 2.5.0 w PyPI po scaleniu wydania.

<!-- docs:section history -->
## Historia

- Wersja 1: polecenie `fixos printers` z ticket-139 (8524601), digital twin z
  ticket-140 (2984f88), dokumentacja i wydanie 2.5.0 w ticket-141. Wyniki
  opisują sprawdzone commity i uruchomienia z 2026-11-17; nie dowodzą
  publikacji pakietu na PyPI.
