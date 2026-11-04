---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "storage-diagnostics",
  "kind": "analysis",
  "version": 2,
  "title": "Diagnoza zajętości dysku: wdrożone reguły i dalsze usprawnienia Fixos",
  "status": "proposed",
  "owner": "semcod/fixos",
  "created": "2026-11-04",
  "updated": "2026-11-04",
  "review_after": "2026-12-04",
  "source_revision": "d039c49b4f290657bb7ddcab92bd7c9b30f28e85",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/blob/947a1492906605dd79a33132af871d1a6774cc82/fixos/diagnostics/disk_analyzer.py",
    "https://github.com/semcod/fixos/blob/cfeea5b8060082350c185b00e300641a46cc64b3/fixos/diagnostics/large_files.py",
    "https://github.com/semcod/fixos/blob/cfeea5b8060082350c185b00e300641a46cc64b3/fixos/diagnostics/storage_rules.py",
    "https://github.com/semcod/fixos/blob/d039c49b4f290657bb7ddcab92bd7c9b30f28e85/fixos/diagnostics/large_files.py"
  ]
}
---

# Diagnoza zajętości dysku: reguły i dalsze usprawnienia Fixos

<!-- docs:section question -->
## Pytanie

Jak przedstawiać duże pliki do szybkiej decyzji bez uznawania dużego rozmiaru,
wieku albo nazwy cache za dowód zbędności? Jak uzyskać użyteczną diagnozę
bez LLM i wskazać, czego jeszcze nie wiadomo?

<!-- docs:section scope -->
## Zakres

Porównano stan bazowy 947a149 z implementacją aplikacyjną cfeea5b.
Nowe zachowanie obejmuje kolektor plików i procesów, deterministyczne reguły,
komendę `fixos storage`, lokalne raporty oraz zgodność DiskAnalyzer.
Nie zmieniano procedur usuwania, kontenerów, usług, modeli, swapu ani IMG.
Kontynuacja PLF-21811 analizuje commit aplikacyjny d039c49 oraz naprawę
budowania paczki i wersję 2.3.0 w integracyjnym ticket-128.

<!-- docs:section method -->
## Metoda

Przegląd kodu, testy na małych plikach i plikach rzadkich, test rzeczywistego
deskryptora procesu w Linux oraz ograniczona, odczytowa próba na katalogu
artefaktów. Próba nie była pełnym skanem hosta. Surowy raport pozostaje lokalnie
w ignorowanym recovery; dokument podaje tylko agregaty potrzebne do oceny.

<!-- docs:section evidence -->
## Dowody

52 testy nowych zachowań i zgodności DiskAnalyzer przeszły; governance
0 błędów/ostrzeżeń i Ruff PASS. Pokryto próg 500 MB, późno napotkany największy
plik, hardlinki, sparse, symlinki, brak uprawnień, budżet skanu, ochronę danych,
zmianę pliku podczas skanu, realne deskryptory i otwarte usunięte dane,
brak inicjalizacji konfiguracji LLM oraz eksport/escaping raportów.

Ponowna weryfikacja: 55 testów obszaru PASS; pełny zestaw 1119 PASS,
5 istniejących pominięć, 16 domyślnych wyłączeń, 57,14 s. Ruff i governance
PASS. Osiem nowych przypadków aliasów zawodzi na pierwotnym kolektorze;
po poprawce przechodzi dla obu kolejności korzeni. Testless zebrał pokrycie
55 testów; 53 lokalne propozycje są doradcze, bez usuwania testów.

Próba 2026-11-04 10:26:51 UTC, limit 50 000 wpisów i 5 s: przeskanowano
50 000 wpisów w około 0,536 s po rozgrzaniu cache FS; znaleziono cztery duże
pliki sklasyfikowane jako obrazy do kontroli zależności. Status `partial`
wynikał z limitu wpisów. Procesy: 20 000 odczytów, niepełna widoczność,
32 otwarte usunięte pliki i 565 248 B zaobserwowanych bloków. To obserwacja
tej próby, bez gwarancji pełnego inventory lub trwałości wyniku.

<!-- docs:section facts -->
## Ustalenia

| Poprzednie ograniczenie | Dostarczone zachowanie |
| --- | --- |
| Skan kończył się po pierwszych N dużych plikach i sortował tylko tę partię. | Ograniczony kopiec wybiera największe trafienia w całym zaobserwowanym zakresie; niepełność jest jawna. |
| Duże pliki dostawały ogólny opis i kilka propozycji do ręcznego przeglądu. | Próg 500 MB, metadane roli/właściciela, reguła i uzasadnienie, następny krok oraz grupy decyzji. |
| Rozmiar logiczny mógł sugerować niewłaściwy odzysk. | Oddzielne bloki/logiczne bajty, sparse i deduplikacja hardlinków; brak obietnicy odzysku. |
| Brak pozytywnego dowodu ochrony pliku używanego przez proces. | Kontrola swapu, deskryptorów i mapowań; niepełne uprawnienia nie oznaczają braku użycia. |
| Ograniczone możliwości szybkiego przeglądu poza terminalem. | JSON/CSV i samodzielny HTML z filtrami, grupami i listą wybranych propozycji. |
| Klasyfikacja inode używała tylko pierwszej ścieżki; alias cache mógł zasłonić backup, Git lub bazę. | Ocena każdego zaobserwowanego aliasu, wybór najsilniejszej decyzji i jawny `decision_path`; nieznane aliasy pozostają niezweryfikowane. |
| `make build` wywoływał brakujący `.venv/bin/pip`, aktualizował narzędzie podczas buildu i uruchamiał rekursywne `clean`. | Build przez pełny Wellman i wybrany interpreter, frontend zadeklarowany w dev extras, osobny `BUILD_OUT`, bez automatycznego czyszczenia. |

Wersja 2.3.0 jest zmianą minor: od tagu v2.2.59 (6cf7994) dodano publiczną
komendę `storage`. VERSION pozostaje źródłem wersji; pyproject jest zgodną
projekcją. Kontrola paczki obejmuje wheel i sdist oraz ich metadane i źródła.
Odrębne od tego pozostają chronione scalenie, instalacja i publikacja na PyPI.

Wszystkie decyzje wynikają z jawnych reguł. LLM może kiedyś pomagać opisać
wynik, ale nie jest wymagany do skanu ani decyzji. Nie powinien nadpisywać
ochrony danych i uprawnień ustalonych przez warstwę reguł.

<!-- docs:section hypotheses -->
## Hipotezy

Największy kolejny zysk diagnostyczny powinno dać powiązanie plików z
manifestami menedżerów i resumowalny inventory. Zmniejszy to liczbę wyników
`manager-review` bez rozstrzygnięcia. Nie mierzono jeszcze skuteczności takich
adapterów ani redukcji czasu całkowitego skanu.

<!-- docs:section limitations -->
## Granice wnioskowania

Obecne reguły rozpoznają potrzebę sprawdzenia zależności, ale nie dowodzą
samodzielnie, że konkretny model lub obraz można usunąć. Zebrany stan jest
nieatomowy. Odczyt 32 B i rozszerzenie nie gwarantują poprawności pliku.
Wiele małych plików może zająć więcej miejsca niż duże trafienia; próg
500 MB nie zastępuje agregacji zajętości katalogów. Dokumentacja i testy
lokalne nie stanowią dowodu merge, instalacji ani sprawdzenia urządzenia IMG.

<!-- docs:section recommendations -->
## Priorytety dalszego rozwoju

1. **Dowody zależności menedżerów.** Dla Ollamy: graf alias–manifest–blob,
   aktywne modele i odniesienia w konfiguracji. Dla Dockera: także zatrzymane
   kontenery, współdzielone warstwy i piny. Dla VM/IMG: backing chain,
   kwalifikowane warianty i retencja poprzedniej działającej pary.
2. **Skan przyrostowy i agregacja.** Wznawianie po budżecie, osobne zakresy
   systemów plików, unieważnianie cache po zmianie inode/size/mtime oraz
   sumowanie małych plików w duże pule. Nie przedstawiać starego pomiaru jako
   świeżego lub niepełnego skanu jako pełnego.
3. **Polityki danych aplikacji.** Kontrakt odtwarzalności i retencji dla
   konkretnych producentów cache; jawna ochrona historii IDE, recovery,
   unikalnych źródeł, checkpointów i kopii. Sama nazwa `.cache` nie wystarcza.
4. **Kontrolowane wykonanie po decyzji.** Powiązać wybrane pozycje z tożsamością
   pliku i dowodami, ponownie sprawdzić je przed skutkiem, używać menedżera
   zamiast ręcznie usuwać jego bloby, mierzyć rzeczywistą zmianę miejsca oraz
   zachować dziennik decyzji. Lista z HTML nie jest upoważnieniem do kasowania.

Te rozszerzenia są zaleceniami kolejnego etapu PLF-039, bez deklaracji, że
zostały już zaimplementowane. [Instrukcja użycia](../information/storage-triage.md).

<!-- docs:section history -->
## Historia

- Wersja 1: analiza implementacji cfeea5b i ograniczonej próby hosta, ticket-125.
- Wersja 2: regresje aliasów d039c49, pełna weryfikacja i naprawa buildu z bumpem 2.3.0, ticket-128 / PLF-21811. Pierwotna próba hosta zachowana jako obserwacja historyczna.
