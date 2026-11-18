---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "mesh",
  "kind": "information",
  "version": 2,
  "title": "Diagnostyka wielowęzłowa sieci: fixos mesh",
  "status": "proposed",
  "owner": "semcod/fixos",
  "scope": "repository",
  "created": "2026-11-18",
  "updated": "2026-11-18",
  "review_after": "2026-12-18",
  "source_revision": "0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/fixos/plugins/builtin/mesh.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/fixos/cli/mesh_cmd.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/fixos/cli/printers_cmd.py",
    "https://github.com/semcod/fixos/blob/0927d1434da24c8c3c4d9cfc1d399b29a0a4bb89/tests/unit/test_mesh_plugin.py"
  ]
}
---

# Diagnostyka wielowęzłowa sieci: fixos mesh

<!-- docs:section purpose -->
## Cel

`fixos mesh` (oraz `fixos printers --mesh`) weryfikuje osiągalność wskazanego
adresu hosta z perspektywy każdego interfejsu lokalnego oraz każdego osiągalnego
węzła w sieci LAN / Tailscale / SSH. Powstał, ponieważ test z pojedynczego
interfejsu przewodowego PC raportował drukarkę Brother HL-L5200DW
(`192.168.188.158`) jako w pełni sprawną, mimo że urządzenia na Wi-Fi i w
drugiej podsieci nie mogły się połączyć ani jej wykryć z powodu pustej bramy
domyślnej (`Default Gateway = 0.0.0.0`) w tablicy routingu drukarki oraz
wycinanego multicastu mDNS (`224.0.0.251:5353`).

<!-- docs:section scope -->
## Zakres

- Lokalne interfejsy IPv4 (Linux `ip -j -4 addr`, macOS `ifconfig`, Windows
  `Get-NetIPAddress`): wiązanie źródłowego IP (`source_address`) dla każdego
  interfejsu niekontenerowego.
- Węzły sieciowe mesh: automatyczne wykrywanie sąsiadów z tablicy ARP (`ip neigh`
  / `arp`), mDNS (`_workstation._tcp`, `_services._dns-sd._udp`), `tailscale status --json`
  oraz konkretnych hostów z `~/.ssh/config`, a także jawne węzły `--node`.
- Nieinteraktywne zdalne sondy SSH (`ssh -o BatchMode=yes`): sonda Python 3 oraz
  automatyczny, zwalidowany fallback POSIX `sh` (`uname -n`, `getent`/`nslookup`,
  `ip -4 route get`, `nc -z` lub `ping -c 1`) dla urządzeń bez `python3` (np.
  routery OpenWrt / BusyBox), z przejściem w raport pasywny przy braku dostępu
  SSH.
- Diagnostyka protokołów docelowego hosta: porównanie unicast mDNS i multicast
  mDNS (`224.0.0.251:5353`) oraz odczyt SNMPv1 MIB-II (`sysDescr`, maska
  podsieci, brama domyślna `0.0.0.0`).

Wykrywane problemy:

| Problem | Ważność | Diagnoza / wskazówka |
|---|---|---|
| brak osiągalności ze wszystkich aktywnych węzłów mesh | CRITICAL | kontrola zasilania, IP, podsieci i reguł zapory |
| częściowa osiągalność między interfejsami/węzłami mesh | WARNING / CRITICAL | separacja podsieci Wi-Fi/LAN, podwójny NAT, AP Isolation |
| pusta brama domyślna na urządzeniu (`Gateway = 0.0.0.0` w SNMP) | CRITICAL | włączenie DHCP albo wpisanie IP routera jako bramy domyślnej |
| unicast mDNS działa, ale multicast mDNS `224.0.0.251:5353` nie dociera | WARNING | dodanie po IP na smartfonie/PC, restart karty, wyłączenie IGMP snooping / AP Isolation |
| nazwa hosta nie rozwiązuje się na węzłach mesh | WARNING / CRITICAL | stała rezerwacja DHCP i wpis DNS na routerze |

<!-- docs:section evidence -->
## Dowody

Źródło: ticket-142 (PR 187, commit 3ddd64f), ticket-143 (PR 188, commit af0248c)
oraz ticket-147 (PR 192, commit 0927d14 — fallback POSIX `sh`). **11 testów
jednostkowych w `tests/unit/test_mesh_plugin.py` PASS**, Ruff PASS, testy CI na
Pythonie 3.10–3.12 i obrazach Alpine, Arch, Debian, Fedora i Ubuntu PASS.

Uruchomienie na rzeczywistej sieci LAN 2026-11-18 dla `192.168.188.158`
(Brother HL-L5200DW, 14 węzłów/interfejsów):
- aktywny test z `local:enp90s0@192.168.188.212` oraz zdalnego węzła SSH `minis`
  (`192.168.188.80`): porty `[631, 9100, 515, 80, 443]` otwarte (~1 ms),
  `mDNS(unicast=OK, multicast=brak)`;
- aktywny test z `local:enp90s0@192.168.1.100` i `tailscale0`: brak trasy
  zwrotnej (`brak otwartych portów`);
- odczyt SNMPv1 MIB-II wykrył `Default Gateway = 0.0.0.0` przy masce
  `255.255.255.0`.

<!-- docs:section content -->
## Użycie i decyzje

```bash
fixos mesh 192.168.188.158                    # test hosta z interfejsów i węzłów LAN/SSH
fixos mesh BRN3C2AF4E8C6F8.local --node minis # test nazwy i dodatkowego węzła SSH
fixos mesh --ports 631,9100,80 192.168.188.158
fixos mesh --no-discover --node 192.168.188.80 192.168.188.158
fixos mesh --json 192.168.188.158             # pełna macierz wyników w JSON
fixos printers --mesh                         # diagnostyka CUPS/Spooler + siatka mesh
```

Decyzje projektowe:

- **Brak blokowania na hasłach SSH i bezpieczny fallback POSIX `sh`.** Sondy
  zawsze używają `BatchMode=yes` oraz ścisłej walidacji nazw hostów i portów.
  Błąd połączenia/autoryzacji SSH (`rc=255`) nie wywołuje ponownej próby,
  natomiast brak `python3` na zdalnym węźle (`rc=127`) przełącza sondę na
  pozycyjny skrypt `REMOTE_POSIX_SH_PROBE`.
- **Odróżnienie unicast mDNS od multicast mDNS.** Pozwala oddzielić wyłączoną
  usługę Bonjour na urządzeniu od wycinania pakietów multicast `224.0.0.251` na
  moście Wi-Fi/LAN.
- **Tylko odczyt.** Sondy TCP, mDNS i SNMPv1 MIB-II nie modyfikują konfiguracji
  badanych urządzeń ani zdalnych hostów.

<!-- docs:section limitations -->
## Ograniczenia

- Aktywny test ze smartfona (Android/iOS) nie jest wykonywany bez zainstalowanego
  serwera SSH i klucza; telefon korzysta pośrednio z diagnozy podsieci, bramy
  SNMP i multicastu mDNS.
- Odczyt bramy domyślnej wymaga włączonego SNMPv1 (`public`) na badanym
  urządzeniu (domyślnie aktywnego m.in. w drukarkach sieciowych Brother/HP).
- W trybie fallbacku POSIX `sh` na zdalnym węźle bez `python3` badane są porty
  TCP (`nc -z`) lub ICMP (`ping`), bez zdalnej sondy pakietów UDP mDNS.

<!-- docs:section next_actions -->
## Następne kroki

- Dodać opcjonalną obsługę IPv6 (`AAAA` / `ff02::fb`) dla sondy wielowęzłowej
  w sieciach bez IPv4.

<!-- docs:section history -->
## Historia

- Wersja 1: polecenie `fixos mesh` oraz flaga `fixos printers --mesh` z
  ticket-142 (3ddd64f) i ticket-143 (af0248c), wydane w wersji 2.6.0 (ticket-144).
- Wersja 2: fallback POSIX `sh` dla węzłów SSH bez `python3` w ticket-147
  (0927d14) oraz aktualizacja dokumentacji dla wydania 2.6.1 w ticket-148.
