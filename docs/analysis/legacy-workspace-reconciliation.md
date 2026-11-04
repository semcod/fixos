---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "legacy-workspace-reconciliation",
  "kind": "analysis",
  "version": 2,
  "title": "Uzgodnienie starej kwarantanny i gałęzi backupowej Fixos",
  "status": "proposed",
  "owner": "semcod/fixos",
  "created": "2026-11-04",
  "updated": "2026-11-04",
  "review_after": "2026-12-04",
  "source_revision": "ff91710a60a19ba3aab96f87c506aa5a806e4aeb",
  "affected_repositories": ["semcod/fixos"],
  "evidence": [
    "https://github.com/semcod/fixos/pull/141",
    "https://github.com/semcod/fixos/pull/144",
    "https://github.com/semcod/fixos/issues/133",
    "https://github.com/subactor/autonom/pull/203",
    "https://github.com/subactor/autonom/blob/f1f9018f38ecb5ddf65e3502772efdef2a53d883/autonom/worktree_observer.py",
    "https://github.com/semcod/fixos/blob/ff91710a60a19ba3aab96f87c506aa5a806e4aeb/project/ticket-109/intent.json",
    "https://github.com/semcod/fixos/blob/ff91710a60a19ba3aab96f87c506aa5a806e4aeb/project/ticket-110/intent.json"
  ]
}
---

# Uzgodnienie starej kwarantanny i gałęzi backupowej Fixos

<!-- docs:section question -->
## Pytanie

Czy kwarantanna PLF-20296 oraz gałąź `ticket/110-sync-standard-requirements-backup`
zawierają jeszcze potrzebną pracę? Jak wyjaśnić trzy ustalenia audytu workspace
bez utraty niescalonych danych lub przejęcia cudzego lease?

<!-- docs:section scope -->
## Zakres

Kontynuacja PLF-21812, dokumentacyjny ticket-129. Punkt odniesienia:
`main` w `ff91710a60a19ba3aab96f87c506aa5a806e4aeb`, Fixos 2.3.0.
Źródło gałęzi backupowej: `1e4d4d364c613aeabc8b3c7ab0c229e5cc008d60`.
Kwarantanna pozostaje odłączonym worktree na
`f787fa4192b39fffd79aa781469dff405f640406`, z czterema zmienionymi lub
nieśledzonymi plikami. Jej położenie to
`/home/tom/github/subactor/.worktrees/.quarantine/PLF-20296-20261026T113356Z`.
Właścicielem repozytorium według Git jest `semcod/fixos`.

<!-- docs:section method -->
## Metoda

Odczytano komplet obu wersji intentów i kryteriów, źródła na przypiętych
commitach, rejestr terminalnych receiptów, stary lease oraz bieżące odpowiedzi
GitHub. Porównano treść, historię i patch-id. Prywatne kopie zostały faktycznie
odtworzone i sprawdzone. Testy kopii uruchamia się przeciw bieżącemu kodowi,
poza kwarantanną. Katalog kwarantanny i jego lease pozostają tylko do odczytu.

<!-- docs:section evidence -->
## Dowody i odzyskiwanie

- GitHub potwierdza scalenie PR141: źródło `2a2287d7bd5241a59604ceb3d0231afc058076b8`,
  merge `a2930fc33536f7c3339e07c00933a94b6fefc129`. Issue133 jest zamknięte.
- GitHub potwierdza scalenie PR144: źródło `5a59ecca1355a91c4cd00193cd687a9d2b083277`,
  merge `da980fac5189756b29d6c987c293c8e793014ad9`. Oba rezultaty są osiągalne
  z badanego `main`. Fakt scalenia jest odrębny od historycznej oceny review.
- Plik `.governance/standard-requirements.json` z backupu i badanego `main`
  jest identyczny: SHA-256
  `ed470a723ba2d5e1545211f8f308d75dfd63a74a9086d65eee2a02fe936f196d`.
  Patch-id samej zmiany wymagań wynosi w obu historiach
  `0e1708f56226018e8882e8e3999f2557341d99c8`.
- Bundle o rozmiarze 21 587 371 B zachowuje dokładne źródło backupu i badany
  `main`. SHA-256:
  `f0513d1699829c325fc2fbe8649939f131f7a9a7112e5b5cdc34312270680dd5`.
  W osobnym prywatnym magazynie Git odtworzono oba refy, sprawdzono ich SHA
  oraz łączność obiektów. Samo istnienie pliku bundle nie byłoby wystarczające.
- Snapshot czterech brudnych plików ma SHA-256
  `43b030fad87a3009deebac93359af81ee0fa84b0adca34f6d586edbc3cad8ab7`.
  Wszystkie bajty odtworzono i porównano z manifestem; ponownie sprawdzono
  niezmienność źródłowego statusu i skrótów. Lokalny ograniczony skan znanych
  wzorców tokenów i kluczy nie zgłosił trafień; nie jest to niezależna atestacja.
- 15 bieżących testów `test_quick_snapshot.py` PASS na badanym `main` oraz
  15 zachowanych testów PASS przeciw temu samemu kodowi produktu. Żaden test
  nie był uruchamiany w kwarantannie. Governance analizy: PASS, 0 błędów i
  ostrzeżeń. To dwa sprawdzone zestawy, a nie 30 różnych przypadków.

Surowe kopie, logi i manifesty przechowywane są prywatnie w
`.subactor/recovery/legacy-reconciliation-20261104/`. Dokument publikuje ich
skróty i zakres, bez surowych snapshotów. Lokalny dowód wymaga osobnego
pozyskania i weryfikacji przez chroniony kontroler przed dyspozycją.

<!-- docs:section facts -->
## Uzgodnienie kryteriów

| Źródło i kryterium | Ocena na badanym main | Dowód lub granica |
| --- | --- | --- |
| Backup ticket-110, jedyne AC-01: synchronizacja wymagań baseline i zależności przechodnich. | Implemented, kandydat do przeglądu właściciela. | Identyczne bajty wymagań, ten sam patch-id, scalone PR144; wpisy lifecycle S4, modularity S3 i priority S3 są obecne. |
| Właściwy ticket-109, AC-01: zakres zatwierdzony przez właściciela, issue133 / PLF-20296. | Zrealizowany zakres produktu. | Powiązany intent jest w main; issue133 zamknięte, PR141 scalone. Nie ustala to właściciela późniejszej brudnej kopii. |
| Właściwy ticket-109, AC-02: warning zamiast critical przy co najmniej 50 GiB i informacja o wolnym miejscu. | Implemented dla badanego kontraktu. | Bieżący kod i testy progu, obu stron granicy oraz małych i wielkich systemów plików. |
| Właściwy ticket-109, AC-03: testy zachowania i komunikatu. | Implemented. | 15 testów aktualnego zestawu i 15 zachowanych testów PASS. |
| Nieśledzony scaffold ticket-109 w kwarantannie, jedyne AC-01: human-approved scope. | Unknown. | README nadal podaje unresolved:human i niewypełniony zakres; intent deklaruje wyłącznie nośniki ticketu, chociaż zmieniono też kod i testy. Brak potwierdzonego przekazania. |

Lista `allowedPaths` backupowego intentu dopuszcza także
`.governance/local-ci-publication.json`; samo dopuszczenie ścieżki nie stanowi
dodatkowego kryterium zmiany. Odtworzono pełne znane AC, bez zawężania ich do
samego podobieństwa nazw commitów.

Kod aplikacyjny kwarantanny różni się od main w dwóch miejscach: brzmieniu
komunikatu i wyrażeniu wartości wolnego miejsca (`get(...) or 0` wobec
`get(..., 0)`). Dla jawnego `None` te wyrażenia mają inne zachowanie.
To wyklucza twierdzenie o identyczności wszystkich bajtów lub wszystkich
możliwych wejść. Oryginalne kryteria nie określają kontraktu `None`;
ewentualne utwardzenie wymaga osobnego rozstrzygnięcia tego wejścia.

<!-- docs:section limitations -->
## Pierwotna blokada kontrolera

Stary plik `ticket-109--coding-agent-plf-20296.json` ma schemat
`wellmanifest.worktree-lease/v1`, właściciela `antigravity` i stan `active`.
Nie zawiera ownerSession, fencingToken, leaseRevision ani terminu wygaśnięcia;
wskazuje wcześniejszą ścieżkę worktree. Nie wolno traktować go jak aktualnego,
wygasłego lease v5 ani dopisywać brakujących wartości.

W lokalnym magazynie ChangeLeaseStore nie znaleziono powiązanej tożsamości
lub lease dla ticket-109 / PLF-20296. Pusta mapa aktywnych wpisów nie dowodzi
zakończenia pracy starego właściciela. Brak nowych zapisów plików też nie jest
potwierdzeniem oddania pracy.

Zarejestrowany proces lifecycle został sprawdzony w trybie `apply=false`.
Adapter Dockuri odrzucił wygenerowany adres, a jego alias nie rozwiązał trasy.
Bezpośrednie wywołanie tego samego zadeklarowanego endpointu Control
`/api/tickets/lifecycle/reconcile` zwróciło
`{"ok": false, "error": "ticket_not_found", "ticket_id": "PLF-20296"}`.
Lokalna kolejka Planfile również nie odnalazła starego identyfikatora.
Nie wykonano mutacji lifecycle.

<!-- docs:section recommendations -->
## Kontynuacja po uzyskaniu nowych danych

Użytkownik odpowiedział: **„Tak, praca została zakończona”** na pytanie o
pracę `antigravity` nad PLF-20296 / ticket-109. Jest to rzeczywiste wejście od
właściciela, przechowywane z odniesieniem do pytania. Nie zawiera zgody na
usunięcie danych i nie uzupełnia nieznanych parametrów starego lease.

W `subactor/autonom` powstał osobny protokół obserwacji historycznych katalogów.
Źródło `f1f9018f38ecb5ddf65e3502772efdef2a53d883` uzyskało niezależne review i
zostało scalone w PR203, merge `1c6ea02713596e9146da30fde655ff6884cb55d6`.
67 testów i 112 podprzypadków PASS, governance i Ruff PASS.

Na hoście wdrożono dokładny moduł o SHA-256
`e3ff084eb8e11f08ef3b4b05b4ff73a361a2a1d13d00dcab14ccb154955ea761`
oraz pojedynczą politykę UID0, wiążącą dokładną ścieżkę, device/inode i skrót
pliku `.git`. Rzeczywisty klient sprawdził root peer, nonce i czas ważności.
Odczyt 2026-11-04 17:44:54 UTC był pełny i wskazał pustą listę procesów.
Kanoniczny klient zobaczył własny nieuprzywilejowany PID, a żądanie z błędną
tożsamością zostało odrzucone. To obserwacja historyczna o TTL 10 s; przed nową
decyzją konieczny jest świeży odczyt.

Odpowiedź usługi nadal jawnie zawiera `owner_liveness="unknown"` i
`cleanup_authorized=false`. Potwierdzenie właściciela i obserwacja użycia
pozostają osobnymi dowodami. Przygotowywana instrukcja produktu ma kanoniczny adres
`subactor/autonom/docs/information/legacy-worktree-observation.md`.

### Zachowanie historii backupu

Ticket-131 uzgadnia status backupu
`1e4d4d364c613aeabc8b3c7ab0c229e5cc008d60`. Całe znane AC-01 ma już
pełną realizację w identycznym pliku wymagań w `main` (wprowadzonym w
commit `5a59ecc` / PR #144). Intent ticket-110 w `main` jest pełną
wersją zawierającą wszystkie wymagane sekcje. Pozostałe pliki konfiguracji,
produktu i ticket-110 są w `main` aktualne i identyczne z intencją backupu.

Materialna aktualizacja tej analizy oraz uzgodnienie są publikowane
atomowo, przez niezależne testy i review. Unikalna historia backupu
pozostaje zachowana w repozytorium i odtworzonym bundle.

<!-- docs:section next_actions -->
## Następne kroki operatora

Uzgodnienie artefaktów zakończonej pracy opiera się na historii Git, kopiach
odzyskiwania, potwierdzeniu właściciela i świeżej obserwacji usługi.
Nie wznawia starego zadania i nie tworzy fikcyjnego lease v5.

1. Opublikować i zweryfikować pełną integrację historii backupu, następnie
   sprawdzić źródłowy SHA i osiągalność przed porządkowaniem scalonego refa.
2. Dla kwarantanny sprawdzić także wszystkie ignorowane pliki i metadane Git.
   Początkowy snapshot czterech zmian nie zastępuje kompletnego archiwum
   katalogu. Odtworzyć pełną kopię przed przedstawieniem dokładnej dyspozycji.
3. Uzyskać decyzję dla archiwalnego katalogu o niepełnym historycznym intencie.
   Przed operacją ponownie sprawdzić tożsamość, HEAD, status, procesy i skróty
   odzyskiwania. Zachować oryginalne metadane lease oraz osobny receipt operacji.
4. Jeżeli rozważane byłoby odrzucenie nadal niescalonego refa, wymaga ono
   przyjętej niezależnej obserwacji i `branch_intent_reconciliation.py`.
   Ten checker zwraca `authority=none`; wynik nie stanowi zgody na usuwanie.

Przygotowany lokalnie `branch110-report-proposal.json` oraz dwa węzły dowodów
przeszły walidację schematu przyjętego w repozytorium. Skrót propozycji:
`34d1d0218838d1090bba1d14db156c6a202c57e88a9e34199d4404bf51255450`.
Nie dołączono autorskiej listy jako rzekomo niezależnej obserwacji kontrolera.
`controller-request.json` wiąże dokładne SHA, snapshot, lease i błąd endpointu;
wnioskuje o ustalenie tożsamości i ocenę dyspozycji. Nie zawiera zgody na usuwanie.
Zależność zarejestrowano w kolejce właściciela jako
`subactor/autonom:STARTER-029`; kontynuacja dostarczyła kwalifikowany obserwator.
Osobny writer pracował w kanonicznym ticket-113. Istniejąca obca zmiana
`autonom/coding_agent.py` w głównym checkout pozostała zachowana.

Funkcjonalny zakres dwóch starych zmian znajduje się w main. Ticket-129
dostarczył pierwszą analizę i dowody; ticket-131 zachowuje historię i aktualizuje
ustalenia. PLF-21812 przechowuje dalszy stan dyspozycji archiwalnej kopii.

<!-- docs:section history -->
## Historia

- Wersja1: analiza przy bazie9510293, ticket-129, pełne AC i odtworzone kopie.
- Wersja2: potwierdzenie zakończenia pracy przez użytkownika, wdrożony obserwator
  z PR203 oraz normalna integracja zweryfikowanej historii w ticket-131.
