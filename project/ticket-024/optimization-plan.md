# Plan działania: autonomia, standardy i szybszy delivery LLM

Data audytu: 2026-09-15
Zakres: FixOS, Subactor Control/Registry/Core/Platform, Planfile, Koru, Goal,
Validator oraz standardy Wellmanifest użyte podczas sesji.

## Cel

Zbudować powtarzalny, mierzalny i fail-closed przepływ od obserwacji problemu do
wdrożonego rezultatu: jedna diagnoza, jeden zakres, jeden ticket, jeden
worktree, exact-head review, chroniony merge, testy i terminalny receipt. Awaria
opcjonalnego kanału (np. IMAP) ma pozostać widoczna, ale nie może blokować
niezależnych kanałów autonomii.

## Ustalenia z audytu sesji

1. Poprawka IMAP była merytorycznie prawidłowa: `inbound-email` jest
   `critical=false`, pozostaje `degraded` i nie obniża `operational_ready`.
   Test regresyjny przeszedł 29/29, a live Control ma 14/15 usług zdrowych,
   `critical_degraded=0` i `operational_ready=true`.
2. Pełna autonomia nadal słusznie pozostaje zamknięta przez konkretne ryzyka:
   strukturalny brak capability, niezaklasyfikowane tickety, zależności
   usługowe i HITL. Te ryzyka trzeba rozwiązywać ticketami, nie rozluźnieniem
   bramek.
3. Wdrożenie może mieć zdrowy kontener bez terminalnego receipt: post-deploy
   project check zwrócił `strategy_binding_missing:dns.management-plane.observe`.
   Potrzebna jest rozdzielona semantyka: health/readiness, reconciliation i
   receipt muszą wskazywać dokładnie, który etap nie przeszedł oraz czy rollback
   był wymagany.
4. Deployment użył lokalnego overlayu, aby zbudować Control z czystego,
   zaakceptowanego worktree, ponieważ główny checkout Core był brudny i opóźniony.
   To sygnał do formalnego pinowania źródła obrazu, a nie do ręcznych overlayów.
5. Kontroler autonomii może przejść w `stalled`, gdy ma pracę, ale wszystkie
   kontrakty są zamknięte. Potrzebuje jawnego receipt cyklu, rozróżnienia
   `waiting_input`/`blocked`/`no_eligible_work` oraz kontrolowanego retry.
6. `fixos cleanuo` rozpoznał literówkę, ale zaproponował szerokie `apt autoremove`;
   komenda została zatrzymana przez interaktywną bramkę. Trzeba utrzymać
   potwierdzenie, zakres pakietów i preflight zależności jako obowiązkowe.
7. Audyt wykazał realną presję zasobów: dysk ponad progiem, wysokie CPU,
   Playwright/cache i ciężki PyCharm. Raport powinien łączyć trend, właściciela,
   koszt i odwracalną propozycję działania, bez wykonywania jej z samej diagnozy.
8. Pełny Core suite miał 7 błędów `knowledge_directory_required`, niezależnych
   od IMAP. FixOS ma podobny znany problem globalnego entrypointu w środowisku
   testowym. Baseline i regresje muszą być zapisywane jawnie, a nie tylko jako
   liczba końcowa.
9. W ekosystemie brakuje jednego produkcyjnego `deliver`: Taskand planuje,
   Koru wykonuje kolejkę, Goal publikuje, Validator scala, ale receipt nie wraca
   jeszcze niezawodnie do planisty.
10. Konfiguracja standardów Wellmanifest wymaga SSOT, pinów, automatycznej
    aktualizacji i dowodu wersji. Rozproszone kopie oraz nieaktualny parser są
    źródłem dryfu i fałszywych blokad.

## Kolejność realizacji

### Faza 0 — higiena i pomiar (XS/S)

- Ustalić wspólny format receiptu: `observed`, `planned`, `executed`,
  `verified`, `blocked`, `rolled_back`, z repository/branch/HEAD/ticket/actor.
- Dodać baseline testów, czasów i kosztu LLM do każdego delivery; oddzielić
  regresje od braków środowiska.
- W Planfile oznaczać ticket jako `blocked` albo `waiting_input`, zamiast
  pozostawiać go `ready/running` bez postępu.
- Naprawić raportowanie literówek i zawsze wymagać podglądu planu, exact targetu,
  wpływu oraz komendy weryfikacyjnej przed remediacją.

### Faza 1 — niezawodny runtime i konfiguracja (S/M)

- Dokończyć `ticket-024`: DNS-backed observation, stale observation, provenance,
  timeout, retry/backoff i bezpieczne odświeżenie po zmianie adresu.
- Uzupełnić katalog strategii o jawne bindingi capability dla obsługiwanych
  management plane; nie mapować `cloudflare` na trasę Plesk bez dowodu.
- Naprawić post-deploy check tak, aby błąd jednego projektu miał identyfikator,
  diagnozę i ticket remediation, a receipt nie był emitowany bez spełnienia
  kryteriów.
- Zapewnić, że opcjonalne usługi są non-critical tylko w katalogu źródłowym,
  propagowanym do Core i obrazu przez digest; dodać test całego łańcucha.

### Faza 2 — autonomia i kolejka (M)

- Rozdzielić gotowość runtime, kwalifikowalność kolejki, execute-ready,
  bounded-autonomy i unattended-autonomy.
- Dodać recovery dla `stalled`: bounded diagnostic, idempotentny retry,
  heartbeat lease oraz automatyczny ticket informacyjny po wygaśnięciu lease.
- Klasyfikować każdy blocker do capability, dependency, human-boundary,
  lifecycle albo unknown; unknown nie może znikać z raportu.
- Izolować ticket zależny od niedostępnego connectora tak, aby inne kompletne
  kontrakty mogły być wykonywane w bounded queue.

### Faza 3 — standardy i artefakty organizacji (M/L)

- Ustanowić Wellmanifest SSOT/dependency standard: wersja, revision, digest,
  źródłowe repo, adopcja, lock, supported migrations i polityka update.
- Wymusić automatyczny bot PR aktualizujący adoptery do najnowszej zgodnej wersji;
  brak aktualizacji ma tworzyć Planfile ticket, nie cichy drift.
- Ustanowić standard raportów: raport repozytoryjny trafia do konkretnego
  `org/repo`, a raport organizacyjny do `[org]/report`; każdy raport ma schema,
  version, generated_at, source HEAD, input digest, scope, evidence links,
  limitations i retention.
- Przenieść raporty z `/tmp` do artefaktów przypiętych do ticketu/receiptu;
  `/tmp` może być tylko buforem roboczym i nie może być źródłem prawdy.

### Faza 4 — zunifikowany delivery z LLM (M/L)

- Zdefiniować interfejs `deliver`: Taskand DSL/intent/twin → Planfile ticket →
  Koru lease/worktree/worker → Goal commit/PR → Validator exact-head merge →
  receipt do Taskand.
- Wymusić idempotency key na każdym etapie i wznowienie po restarcie bez
  duplikacji ticketu, PR, deployu ani merge.
- Dodać preflight wykrywający istniejący worktree, branch, PR i remote HEAD przed
  startem; konflikt zatrzymuje proces i tworzy diagnozę.
- Ujednolicić nazewnictwo wyników `dry-run`, `plan`, `apply`, `merge` i
  `post-merge`, aby UI nie nazywało scalonego wykonania dry-runem.

## Standard pracy LLM

1. Najpierw deterministyczny preflight: governance, zakres, aktywny ticket,
   zależności, dirty worktree, HEAD i dostępne testy.
2. Do modelu przekazywać minimalny, anonimizowany kontekst z digestem; sekrety,
   pełne logi i nieograniczone katalogi pozostają poza promptem.
3. Odpowiedź LLM musi być schematem: diagnoza, hipoteza, proponowany zakres,
   non-goals, pliki, testy, ryzyko, rollback. Parser odrzuca nieznane pola.
4. Małe, deterministyczne zadania obsługiwać bez LLM; LLM używać do diagnozy,
   planu i niejednoznacznych analiz. Wynik modelu jest advisory i digest-bound.
5. Stosować model tani/szybki do triage, model jakościowy do planu i Validatora
   do niezależnej recenzji; fallback ma być jawny i mierzony.
6. Każda tura ma timeout, budżet tokenów, koszt, latency, retry i correlation ID.
   Retry musi być idempotentny oraz nie może ponawiać mutacji bez nowego grantu.
7. Po każdym etapie wykonywać deterministyczny check; model nie może sam
   zatwierdzać zakresu, sekretu, plan_hash ani merge.

## Metryki jakości i wydajności

- lead time: prompt → ticket, ticket → PR, PR → Validator, merge → deploy;
- first-pass rate governance/CI/Validator oraz liczba reworków;
- czas i koszt LLM na diagnozę, plan, implementację i review;
- odsetek ticketów wznowionych bez duplikacji;
- stale worktree/branch/PR age i liczba niepowiązanych artefaktów;
- fresh configuration observation age, DNS resolution latency i false-positive;
- queue throughput, execute-ready ratio, stalled cycles i recovery time;
- raporty z pełnym evidence chain versus raporty bez źródła.

## Optymalizacje techniczne

- Równolegle pobierać niezależne odczyty, ale serializować mutacje i alokację
  ticketów.
- Cache’ować tylko dane z TTL, revision/digest i timestampem; invalidować po
  zmianie DNS, HEAD, manifestu lub obrazu.
- Używać incremental governance/testów dla niezmienionych komponentów, lecz
  przed merge wykonywać pełny wymagany gate.
- Rozdzielić szybki `quick` od głębokiego `scan`; raportować co pominięto.
- Precompute’ować indeks artefaktów i zależności; nie regenerować całego repo przy
  każdej turze LLM.
- Wysyłać do modelu podsumowania i referencje, nie wielokrotnie te same logi.

## Kryteria zakończenia planu

- Każdy punkt ma właściciela, ticket Planfile, zakres ścieżek, zależności,
  acceptance criteria i rollback.
- Wszystkie nowe tickety są zsynchronizowane do właściwego repozytorium GitHub;
  organizacyjne do `org/report`.
- Żaden merge nie następuje bez exact-head trusted Validator review i receiptu.
- Raport końcowy zawiera baseline, wynik, znane ograniczenia i linki do dowodów.
- Testy środowiskowe są oznaczone jako takie; znane błędy nie są maskowane jako
  sukces.

## Proponowane tickety Planfile

Szczegółowe zadania publikuję jako osobne tickety z zależnościami:

- `P1`: fixOS — domknięcie endpoint refresh i testy konfiguracji;
- `P2`: subactor/core — niezależna gotowość kanałów i recovery stalled queue;
- `P3`: subactor/platform — strategy binding oraz terminalny deployment receipt;
- `P4`: wellmanifest — SSOT/dependency/update contract;
- `P5`: subactor/report — standard raportów i artefaktów;
- `P6`: semcod/planfile — idempotentny publish/receipt lifecycle;
- `P7`: semcod/goal — preflight worktree/branch/PR i exact-head delivery;
- `P8`: semcod/koru — lease timeout, takeover i persistent queue;
- `P9`: subactor/validator-agent — nazewnictwo i dowody merge;
- `P10`: fixOS — szybki, bezpieczny triage literówek i package cleanup;
- `P11`: cross-repo — macOS/Windows/integration test matrix;
- `P12`: cross-repo — metryki LLM, latency, koszt i replayable receipts.

Tickety są propozycjami implementacyjnymi; ich status pozostaje `open` do
kwalifikacji przez właściciela repozytorium i nie nadaje automatycznie grantu
na mutacje produkcyjne.

## Rejestr publikacji Planfile — 2026-09-15

Publikacja została wykonana przez Planfile. Każdy wpis ma status `open`; link
GitHub jest dowodem utworzenia issue, nie dowodem implementacji ani zgody na
merge.

| Punkt | Planfile | Repozytorium / issue |
|---|---|---|
| P1 (istniejący zakres ticket-024) | `PLF-002` | [semcod/fixos#45](https://github.com/semcod/fixos/issues/45) |
| P2 | `STARTER-004` | [subactor/core#483](https://github.com/subactor/core/issues/483) |
| P3 | `STARTER-003` | [subactor/platform#625](https://github.com/subactor/platform/issues/625) |
| P4 | `PLF-010` | [wellmanifest/ssot#2](https://github.com/wellmanifest/ssot/issues/2) |
| P5 | `STARTER-128` | [subactor/report#8](https://github.com/subactor/report/issues/8) |
| P6 | `PLF-068` | [semcod/planfile#94](https://github.com/semcod/planfile/issues/94) |
| P7 | `STARTER-023` | [semcod/goal#163](https://github.com/semcod/goal/issues/163) |
| P8 | `STARTER-604` | [semcod/koru#179](https://github.com/semcod/koru/issues/179) |
| P9 | `VA-003` | [subactor/validator-agent#505](https://github.com/subactor/validator-agent/issues/505) |
| P10 | `PLF-003` | [semcod/fixos#47](https://github.com/semcod/fixos/issues/47) |
| P11 | `STARTER-129` | [subactor/report#9](https://github.com/subactor/report/issues/9) |
| P12 | `PLF-069` | [semcod/planfile#95](https://github.com/semcod/planfile/issues/95) |

Zależności lokalne są zapisane w Planfile: `STARTER-129` następuje po
`STARTER-128`, a `PLF-069` po `PLF-068`. P1 pozostaje związany z aktywnym
`ticket-024`, więc nie utworzono drugiego, równoległego ticketu.

### Uwaga o magazynie Planfile

`subactor/report` i `wellmanifest/ssot` nie miały repozytoryjnego katalogu
`.planfile`. Planfile opublikował ich issues poprawnie, ale zapisał lokalne
rekordy odpowiednio w nadrzędnym magazynie `subactor/.planfile` i w magazynie
Planfile poziomu użytkownika. Przed kolejną pracą należy utworzyć repozytoryjne
magazyny, przeprowadzić migrację/import bez zmiany external issue IDs i dopiero
potem włączyć automatyczny sync. Nie wolno tworzyć nowych issues tylko po to,
by skopiować te rekordy.
