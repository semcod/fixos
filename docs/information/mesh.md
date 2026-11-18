---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "mesh",
  "kind": "information",
  "version": 1,
  "title": "Diagnostyka wielowęzłowa sieci: fixos mesh",
  "status": "proposed",
  "owner": "semcod/fixos",
  "scope": "repository",
  "created": "2026-11-18",
  "updated": "2026-11-18",
  "review_after": "2026-12-18",
  "source_revision": "af0248c6beb7dfa4bd0723c2a4500d8f6d01413f",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/blob/af0248c6beb7dfa4bd0723c2a4500d8f6d01413f/fixos/plugins/builtin/mesh.py",
    "https://github.com/semcod/fixos/blob/af0248c6beb7dfa4bd0723c2a4500d8f6d01413f/fixos/cli/mesh_cmd.py",
    "https://github.com/semcod/fixos/blob/af0248c6beb7dfa4bd0723c2a4500d8f6d01413f/fixos/cli/printers_cmd.py",
    "https://github.com/semcod/fixos/blob/af0248c6beb7dfa4bd0723c2a4500d8f6d01413f/tests/unit/test_mesh_plugin.py"
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
- Nieinteraktywne zdalne sondy SSH (`ssh -o BatchMode=yes`) z automatycznym
  przejściem w raport pasywny, gdy węzeł LAN nie udostępnia klucza/usługi SSH.
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

Źródło: ticket-142 (PR 187, commit af0248c6beb7dfa4bd0723c2a4500d8f6d01413f) i
poprawki walidacji argumentów w ticket-143 (PR 188). Testy jednostkowe w
`tests/unit/test_mesh_plugin.py` oraz testy CI na Pythonie 3.10–3.12 i obrazach
Alpine, Arch, Debian, Fedora i Ubuntu zakończone statusem PASS.

Uruchomienie na rzeczywistej sieci LAN 2026-11-18 dla `192.168.188.158`
(Brother HL-L5200DW):
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

- **Brak blokowania na hasłach SSH.** Zdalne sondy zawsze używają
  `BatchMode=yes`, ścisłej walidacji celu SSH (`_SAFE_SSH_TARGET_RE`) i krótkich
  limitów czasu; węzły bez autoryzacji kluczem są raportowane uczciwie jako
  `passive`.
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
- Zdalna sonda SSH zakłada obecność `python3` na zdalnym hoście.

<!-- docs:section next_actions -->
## Następne kroki

- Dodać lekki fallback POSIX `sh`/`nc` dla zdalnych routerów OpenWrt bez
  zainstalowanego `python3`.
- Opublikować wydanie 2.6.0 w PyPI po scaleniu gałęzi wydania.

<!-- docs:section history -->
## Historia

- Wersja 1: polecenie `fixos mesh` oraz flaga `fixos printers --mesh` z
  ticket-142 (3ddd64f) i ticket-143, udokumentowane wraz z podbiciem wersji do
  2.6.0 w ticket-144. Nie dowodzi publikacji pakietu na PyPI.
