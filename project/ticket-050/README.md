# Ticket 050: cleanup docker: szacunek zasobow, tabela, usuwanie + natywne Gemini API

- **ID**: ticket-050
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user request 2026-09-20 ("brak informacji ile
mozna zaoszczedzic miejsca i CPU/RAM; lepsze wyswietlanie w tabeli; dodaj
obsluge API z gemini google" + wybor: natywne API Google, opcja usuwania).

1. `fixos cleanup --docker-stale-services` pokazuje szacunek odzyskiwanych
   zasobow per kandydat: CPU/RAM (docker stats) oraz dysk (warstwa RW +
   rozmiar obrazu, gdy obraz nie jest wspoldzielony).
2. Lista kandydatow renderowana tabela `rich.table.Table` zamiast linii
   tekstowych; podsumowanie potencjalnych oszczednosci.
3. Osobno potwierdzane `docker rm` (+ opcjonalne `docker rmi` dla
   niewspoldzielonych obrazow) dla wybranych uslug.
4. Natywny klient Google Gemini API (`generateContent` /
   `streamGenerateContent`, `x-goog-api-key`) obok istniejacej sciezki
   OpenAI-compatible; wybor transportu przez `GEMINI_TRANSPORT`
   (native|openai, domyslnie native dla providera `gemini`).

## Acceptance criteria

- [ ] AC-01: `scan()` zwraca `resources` (cpu/mem/dysk) i `potential_savings`.
- [ ] AC-02: Lista kandydatow w formacie tabeli + linia szacunku zyskow.
- [ ] AC-03: Usuwanie kontenerow/obrazow tylko po osobnym potwierdzeniu;
      obraz wspoldzielony nigdy nie jest usuwany.
- [ ] AC-04: Provider `gemini` z `GEMINI_TRANSPORT=native` uzywa natywnego
      API Google; `openai` zachowuje dotychczasowa sciezke.
- [ ] AC-05: Testy jednostkowe + `./project/governance-check.sh` przechodza.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
