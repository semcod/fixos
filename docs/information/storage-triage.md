---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "storage-triage",
  "kind": "information",
  "version": 1,
  "title": "Diagnostyka dużych plików i decyzje bez LLM",
  "status": "proposed",
  "owner": "semcod/fixos",
  "created": "2026-11-04",
  "updated": "2026-11-04",
  "review_after": "2026-12-04",
  "source_revision": "cfeea5b8060082350c185b00e300641a46cc64b3",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/blob/cfeea5b8060082350c185b00e300641a46cc64b3/fixos/diagnostics/large_files.py",
    "https://github.com/semcod/fixos/blob/cfeea5b8060082350c185b00e300641a46cc64b3/tests/unit/test_large_file_triage.py"
  ]
}
---

# Diagnostyka dużych plików i decyzje bez LLM

<!-- docs:section purpose -->
## Cel

`fixos storage` znajduje duże pliki i grupuje je do szybkiego przeglądu.
Wyjaśnia rolę danych i powód proponowanej decyzji. Nie usuwa plików ani nie
uruchamia procedur czyszczenia. Silnik reguł działa lokalnie bez LLM, kluczy API
i wywoływania poleceń zewnętrznych.

<!-- docs:section scope -->
## Zakres

Domyślnie badany jest katalog domowy, jeden system plików, pliki **ściśle
większe niż 500 MB** (500 000 000 B). Podaj konkretne katalogi albo `/` dla
diagnostyki hosta. Dowiązania symboliczne oraz wirtualne `/proc`, `/sys`, `/dev`
i `/run` nie są rekursywnie skanowane jako dane użytkownika. `/proc` jest
osobno odczytywany dla dowodów aktywnego użycia.

<!-- docs:section evidence -->
## Dowody

Źródło: aplikacyjny ticket-124, commit wskazany w metadanych. Nowe testy
zachowania i istniejące testy DiskAnalyzer: **52 PASS**; natywna bramka
governance i Ruff PASS. Dokumentacja należy do integracyjnego ticket-125.
Stan commitu, PR, merge i instalacji należy sprawdzać oddzielnie; dokument
nie jest dowodem wdrożenia tej wersji na komputerze lub urządzeniu IMG.

<!-- docs:section content -->
## Użycie i decyzje

```bash
# Szybki przegląd katalogu domowego
fixos storage

# Wybrane katalogi, największe 100 plików w zaobserwowanym zakresie
fixos storage ~/Downloads ~/github --limit 100 --max-seconds 60

# Raporty w nowych plikach; istniejący plik nie jest nadpisywany
fixos storage ~/Downloads --json --output przeglad.json
fixos storage ~/Downloads --format csv --output przeglad.csv
fixos storage ~/Downloads --format html --output przeglad.html

# Dłuższy, nadal ograniczony skan hosta
fixos storage / --max-seconds 300 --max-entries 5000000 --limit 100
```

Raport HTML ma rozwijane grupy, wyszukiwanie po ścieżce i uzasadnieniu,
filtr decyzji oraz eksport zaznaczonych ścieżek do osobnego JSON. Ten wybór
tworzy listę do dalszego przeglądu; `authorizedDelete` pozostaje `false`.

| Decyzja | Znaczenie | Przykłady i następny krok |
| --- | --- | --- |
| `protected` | Zachowaj na podstawie wykrytego kontekstu lub użycia. | Aktywny swap, otwarty/mapowany plik, baza danych, Git/worktree, historia IDE, kopia zapasowa, trwały stan aplikacji. |
| `manager-review` | Potrzebna kontrola zależności przez właściciela magazynu. | Modele i aliasy, warstwy kontenerów, obrazy VM/IMG, skompresowane obrazy, artefakty wydań. Sprawdź manifesty, piny, backing chain i retencję. |
| `review` | Plik do decyzji człowieka, z niepotwierdzonymi zależnościami. | Duże archiwa, multimedia, logi, dane o nieznanej roli lub przypuszczalny cache. Sprawdź przeznaczenie i odtwarzalność. |

Reguły mają stałe identyfikatory i ustaloną kolejność: pozytywny dowód
ochrony ma pierwszeństwo przed heurystyką cache. Te same fakty dają tę samą
decyzję. To wyjaśnialny system reguł, bez modelu językowego.

JSON `fixos.storage-triage/v1` zawiera m.in.:

- Ścieżkę, typ i źródło rozpoznania typu: sygnatura do 32 B, rozszerzenie
  albo brak rozpoznania; właściciela, mtime i liczbę dni od modyfikacji.
- Bajty logiczne i przydzielone bloki, rozpoznanie plików rzadkich oraz
  hardlinki według pary device/inode. Znane ścieżki hardlinków są podane
  z informacją o możliwej niepełności.
- Dowód aktywnego swapu i PID-y procesów trzymających deskryptor lub mapowanie.
  Niepełny dostęp, limity i znikające procesy są raportowane.
- Grupowanie według decyzji, typu, lokalizacji/repozytorium i właściciela.
- Status skanu, liczbę wpisów, błędy odczytu, pominięcia i limit wyników.
  Największe pliki są wybierane ze wszystkich zaobserwowanych plików,
  bez zatrzymania po pierwszych N trafieniach.

`reclaimable_bytes` pozostaje niepotwierdzone. `reclaim_upper_bound_bytes`
jest co najwyżej górną granicą przydzielonych bloków dla pojedynczego linku
pliku do przeglądu. Nie jest obietnicą odzysku. Dla danych chronionych,
magazynów zależnych i hardlinków nie sugeruje się takiego odzysku.

<!-- docs:section limitations -->
## Ograniczenia

Domyślny budżet to 30 s i 200 000 wpisów, wynik do 50 plików. Część czasu
jest zarezerwowana na aktywne użycie. Limity kooperacyjne nie przerywają
pojedynczego blokującego wywołania systemowego na uszkodzonym lub wolnym FS.
`partial` i `results_truncated` oznaczają różne rzeczy: niepełny zakres skanu
oraz ograniczoną liczbę prezentowanych trafień. Brak trafień w niepełnym
skanie nie jest pełnym rozliczeniem zajętości dysku.

Brak wykrytego procesu nie dowodzi nieużywania danych. Kontrola `/proc`
widzi tylko dostępne przestrzenie nazw i jest ograniczona liczbą odczytów.
mtime nie oznacza ostatniego użycia. Reflinki, snapshoty, kompresja i równoległe
zapisy mogą zmienić faktyczny odzysk względem `st_blocks`. GB=10^9 B,
GiB=2^30 B. Starsze pola DiskAnalyzer zachowują dotychczasowe binarne jednostki.

Same modele, obrazy i kontenery nie są jeszcze analizowane przez natywne API
ich menedżerów. Obecna wersja wskazuje potrzebną kontrolę zależności i nie
przedstawia nieznanych danych jako automatycznie usuwalnych.

<!-- docs:section next_actions -->
## Następne kroki

Otwórz HTML albo porównaj grupy w terminalu, wybierz zakres do dalszego
sprawdzenia i wykonaj wskazane kontrole właściciela danych. Przed ewentualnym
usuwaniem trzeba ponownie odczytać stan dokładnego celu.
[Analiza dalszych usprawnień](../analysis/storage-diagnostics.md).
