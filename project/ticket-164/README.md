# ticket-164: Napraw walidację portów ASCII i zamykanie gniazda UDP w sondzie mesh (#209)

- **ID**: ticket-164
- **Owner**: agent:coding-agent
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

## Goal and scope

Sonda POSIX zwraca poprawne numery portów mimo otaczających spacji, a sonda Pythona zwalnia gniazdo UDP używane do ustalenia adresu źródłowego także po błędzie połączenia.

SESSION_EXECUTION_AUTHORIZATION: validated native ticket PLF-28514; Willman request d76434cc-be65-40b0-a0f3-3308727182d5; protected publication only.

## Acceptance criteria

- [x] AC-01: parse_posix_probe_output usuwa białe znaki z obu stron klucza i wartości oraz przyjmuje dla OPEN i CLOSED wyłącznie cyfry ASCII reprezentujące port od 1 do 65535 włącznie. REMOTE_PYTHON_PROBE obejmuje udp.connect i udp.getsockname blokiem with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:, dzięki czemu gniazdo zamyka się także po OSError.
- [x] AC-02: Deterministyczny test jednostkowy bez pytest.skip i bez połączeń sieciowych sprawdza odczyt OPEN = 631, akceptację portów granicznych 1 i 65535, pominięcie wartości 0, 70000 i ² oraz obecność wymaganego bloku with w REMOTE_PYTHON_PROBE.

## Evidence

- `git diff --check da0ea36a101b3444fd6020c79f0ac0c5527e81be` zakończył się kodem `0`. `delivery.acceptedBaseSha` odpowiada `HEAD` i zamrożonej bazie.
- `test_probe_helpers_validate_ports_and_manage_udp_socket` przeszedł przez zatwierdzony Wellman (`d8c7a0ad558e6edb702a4c6d1a507841b0384000`) z jawnie wskazanym `.venv` głównego checkoutu. Wynik to `1 passed`, kod `0`.
- `tests/unit/test_mesh_plugin.py` uruchomiony tak samo zwrócił `10 passed, 2 failed`, kod `1`. Test POSIX nie mógł otworzyć gniazda TCP, a test zdalnej sondy Pythona nie mógł otworzyć gniazda UDP mDNS. Porównanie sondy z zamrożonej bazy i z bieżącej wersji dało ten sam `PermissionError: [Errno 1] Operation not permitted` przy otwieraniu gniazda mDNS.

## Handoff

- Plan `PLF-28514`, część `1/1`, sesja Willman `d76434cc-be65-40b0-a0f3-3308727182d5`. Gałąź `ticket/164-project-job-d76434cc`, worktree `.worktrees/ticket-164--project-job-d76434cc`, `HEAD` `da0ea36a101b3444fd6020c79f0ac0c5527e81be`, rewizja i token dzierżawy `1/1`.
- Runner wykonuje autorytatywne testy repozytorium w środowisku z dostępem do gniazd i zapisuje nową migawkę lub zatwierdzony commit przed publikacją.
