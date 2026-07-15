## [2.2.0] - 2026-04-04

### Summary

feat(pyqual): auto-kalibracja progów metryk, wymagany publish

### Added

- Skrypt `scripts/pyqual-calibrate.py` do auto-kalibracji progów metryk
- Target `publish` w Makefile dla PyPI

### Changed

- Progi metryk w `pyqual.yaml` dostosowane do aktualnych wartości
- `publish` w pyqual pipeline jest teraz wymagany (nie opcjonalny)
- Ujednolicenie wersji do 2.2.0 we wszystkich plikach

## [2.1.23] - 2026-02-26

### Summary

refactor(goal): CLI interface improvements

### Other

- update fixos/cli.py
- update fixos/interactive/cleanup_planner.py


## [2.1.22] - 2026-02-26

### Summary

refactor(docs): code analysis engine

### Docs

- docs: update README
- docs: update TODO.md

### Other

- update fixos/cli.py
- update fixos/diagnostics/disk_analyzer.py
- update fixos/diagnostics/system_checks.py


## [2.1.21] - 2026-02-26

### Summary

refactor(goal): CLI interface improvements

### Other

- update fixos/cli.py
- update fixos/interactive/cleanup_planner.py
- update fixos/orchestrator/orchestrator.py
- update fixos/utils/terminal.py


## [2.1.20] - 2026-02-26

### Summary

fix(goal): CLI interface improvements

### Test

- update test_kwarg.py

### Other

- update fixos/cli.py
- update img.png


## [2.1.19] - 2026-02-26

### Summary

fix(goal): CLI interface improvements

### Other

- update fixos/cli.py


## [2.1.18] - 2026-02-26

### Summary

refactor(goal): code analysis engine

### Test

- update test_click.py
- update test_click2.py

### Other

- update fixos/diagnostics/disk_analyzer.py
- update fixos/interactive/cleanup_planner.py
- update patch_cli.py
- update patch_cli2.py
- update patch_cli3.py
- update patch_cli4.py
- update patch_docs.py
- update patch_parser.py


## [2.1.17] - 2026-02-26

### Summary

fix(goal): code analysis engine

### Docs

- docs: update README

### Test

- update test_click.py
- update test_click2.py

### Other

- update TICKET
- update fixos/cli.py
- update fixos/diagnostics/disk_analyzer.py
- update fixos/interactive/__init__.py
- update fixos/interactive/cleanup_planner.py
- update fixos/providers/llm_analyzer.py
- update patch_cli.py
- update patch_cli2.py
- update patch_cli3.py
- update patch_cli4.py
- ... and 2 more


## [Unreleased]

### Added

- **feat(disk):** Nowa funkcja `--disc` (`--disk`) dla poleceń `fix` i `scan` do analizy zajętości dysku.
- **feat(interactive):** Kreator czyszczenia dysku (CleanupPlanner) z priorytetami (🔴/🟡/🟢).
- **feat(llm):** Fallback LLM dla błędów podczas czyszczenia dysku.
- **fix(cli):** Naprawa parsera grupowego (NaturalLanguageGroup) w celu poprawnego działania komend.
- **refactor(cli):** Usunięto zduplikowany kod ujednolicając funkcje analizy dysku do wspólnego helpera `_run_disk_analysis`.
- **refactor(ui):** Usunięto ikony Unicode z CLI i sformatowano wyjście `stderr` oraz standardowego logowania na czysty kod Markdown dla poprawy czytelności w oknach terminalowych.

## [2.2.36] - 2026-07-15

### Docs
- Update project/README.md
- Update project/context.md

### Test
- Update tests/unit/test_service_cleanup.py
- Update tests/unit/test_service_scanner.py

### Other
- Update fixos/cli/cleanup_cmd.py
- Update fixos/diagnostics/cache_discovery.py
- Update fixos/diagnostics/service_cleanup.py
- Update fixos/diagnostics/service_scanner.py
- Update project.sh
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- ... and 13 more files

## [2.2.35] - 2026-06-16

### Other
- Update uv.lock

## [2.2.34] - 2026-06-16

### Test
- Update tests/unit/test_cache_discovery.py

### Other
- Update fixos/cli/cleanup_cmd.py
- Update fixos/constants.py
- Update fixos/diagnostics/cache_discovery.py
- Update fixos/diagnostics/service_cleanup.py
- Update fixos/diagnostics/service_scanner.py
- Update uv.lock

## [2.2.33] - 2026-06-16

### Other
- Update uv.lock

## [2.2.32] - 2026-06-16

### Test
- Update tests/unit/test_service_cleanup.py
- Update tests/unit/test_service_scanner.py

### Other
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/main.py
- Update fixos/cli/output_formatter.py
- Update fixos/cli/shared.py
- Update fixos/diagnostics/service_cleanup.py
- Update fixos/diagnostics/service_scanner.py
- Update uv.lock

## [2.2.31] - 2026-06-16

### Other
- Update uv.lock

## [2.2.30] - 2026-06-16

### Docs
- Update README.md

### Other
- Update nlp2uri.yaml
- Update uv.lock

## [2.2.29] - 2026-05-08

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/e2e/test_diagnostics_integration.py
- Update tests/unit/test_core.py

### Other
- Update app.doql.less
- Update fixos/agent/session_core.py
- Update fixos/cli/_cleanup_flatpak.py
- Update fixos/cli/_cleanup_home.py
- Update fixos/cli/_cleanup_snap.py
- Update fixos/cli/_cleanup_system.py
- Update fixos/cli/_cleanup_utils.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/config_cmd.py
- Update fixos/cli/scan_cmd.py
- ... and 36 more files

## [2.2.28] - 2026-05-06

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update project/README.md
- Update project/context.md

### Test
- Update tests/unit/test_core.py

### Other
- Update app.doql.less
- Update docker/docker-compose.yml
- Update fixos/agent/session_core.py
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- ... and 10 more files

## [2.2.27] - 2026-05-04

### Docs
- Update README.md

### Other
- Update docker/docker-compose.yml
- Update docker/test-scenarios.sh
- Update docker/validate-scenario.py
- Update fixos/cli/fix_cmd.py
- Update fixos/cli/output_formatter.py
- Update fixos/cli/report_cmd.py
- Update fixos/cli/scan_cmd.py
- Update fixos/cli/shared.py
- Update uv.lock

## [2.2.26] - 2026-05-04

### Docs
- Update README.md

### Test
- Update tests/e2e/test_anonymization_layers.py

### Other
- Update uv.lock

## [2.2.25] - 2026-05-04

### Docs
- Update README.md
- Update REFACTORING_PROGRESS.md

### Test
- Update tests/unit/test_core.py

### Other
- Update fixos/agent/autonomous_session.py
- Update fixos/agent/hitl_session.py
- Update fixos/agent/session_handlers.py
- Update fixos/platform_utils.py
- Update fixos/utils/__init__.py
- Update fixos/utils/anonymizer.py
- Update uv.lock

## [2.2.24] - 2026-05-04

### Docs
- Update README.md
- Update REFACTORING_PROGRESS.md

### Other
- Update fixos/agent/session_handlers.py
- Update fixos/cli/ask_cmd.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/config_cmd.py
- Update fixos/cli/report_cmd.py
- Update fixos/cli/scan_cmd.py
- Update fixos/constants.py
- Update fixos/diagnostics/checks/_shared.py
- Update fixos/diagnostics/checks/audio.py
- Update fixos/diagnostics/checks/resources.py
- ... and 9 more files

## [2.2.23] - 2026-05-04

### Docs
- Update README.md
- Update REFACTORING_PROGRESS.md
- Update SUMD.md
- Update SUMR.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update fixos/agent/autonomous_session.py
- Update fixos/agent/hitl_session.py
- Update fixos/agent/session_core.py
- Update fixos/agent/session_handlers.py
- Update fixos/agent/session_io.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/config_cmd.py
- Update fixos/cli/features_cmd.py
- Update fixos/cli/fix_cmd.py
- ... and 23 more files

## [2.2.22] - 2026-05-04

### Docs
- Update README.md
- Update REFACTORING_PROGRESS.md

### Other
- Update fixos/agent/session_core.py
- Update fixos/agent/session_handlers.py
- Update fixos/agent/session_io.py
- Update fixos/cli/ask_cmd.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/platform_utils.py
- Update uv.lock

## [2.2.21] - 2026-05-04

### Docs
- Update README.md

### Other
- Update uv.lock

## [2.2.20] - 2026-05-04

### Docs
- Update README.md

### Other
- Update fixos/cli/ask_cmd.py
- Update fixos/cli/features_cmd.py
- Update fixos/cli/fix_cmd.py
- Update fixos/cli/main.py
- Update fixos/cli/quickfix_cmd.py
- Update fixos/cli/report_cmd.py
- Update fixos/cli/rollback_cmd.py
- Update fixos/cli/scan_cmd.py
- Update fixos/cli/shared.py
- Update fixos/cli/token_cmd.py
- ... and 3 more files

## [2.2.19] - 2026-05-04

### Docs
- Update README.md

### Other
- Update fixos/cli/config_cmd.py
- Update fixos/config.py
- Update uv.lock

## [2.2.18] - 2026-05-04

### Docs
- Update README.md

### Other
- Update uv.lock

## [2.2.17] - 2026-05-04

### Docs
- Update README.md
- Update project/README.md
- Update project/context.md

### Other
- Update fixos/orchestrator/executor.py
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- ... and 8 more files

## [2.2.16] - 2026-05-04

### Docs
- Update README.md

### Test
- Update test-results/alpine-build.log
- Update test-results/alpine-scan-help.log
- Update test-results/alpine-unit-tests.log
- Update test-results/alpine-version.log
- Update test-results/arch-build.log
- Update test-results/arch-scan-help.log
- Update test-results/arch-unit-tests.log
- Update test-results/arch-version.log
- Update test-results/debian-build.log
- Update test-results/debian-scan-help.log
- ... and 10 more files

### Other
- Update Makefile
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/fix_cmd.py
- Update fixos/diagnostics/storage_analyzer.py
- Update fixos/interactive/cleanup_planner.py
- Update fixos/llm_shell.py
- Update fixos/providers/llm.py
- Update fixos/utils/anonymizer.py
- Update uv.lock

## [2.2.15] - 2026-05-04

### Docs
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update fixos/agent/autonomous_session.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/config_cmd.py
- Update fixos/cli/features_cmd.py
- Update fixos/cli/main.py
- Update fixos/cli/profile_cmd.py
- Update fixos/diagnostics/flatpak_analyzer.py
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- ... and 15 more files

## [2.2.14] - 2026-05-04

### Docs
- Update README.md
- Update REFACTORING_PROGRESS.md
- Update SUMD.md
- Update SUMR.md
- Update project/README.md
- Update project/context.md

### Other
- Update app.doql.less
- Update fixos/agent/__init__.py
- Update fixos/agent/hitl_session.py
- Update fixos/agent/session_core.py
- Update fixos/agent/session_handlers.py
- Update fixos/agent/session_io.py
- Update fixos/cli/ask_cmd.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/config_cmd.py
- Update fixos/cli/fix_cmd.py
- ... and 33 more files

## [2.2.13] - 2026-05-04

### Docs
- Update OPTIMIZATION.md
- Update README.md
- Update SUMD.md
- Update SUMR.md
- Update project/README.md
- Update project/context.md

### Test
- Update test_timeout_fix.py
- Update testql-scenarios/generated-cli-tests.testql.toon.yaml
- Update testql-scenarios/generated-from-pytests.testql.toon.yaml

### Other
- Update Makefile
- Update app.doql.less
- Update fixos/agent/hitl_session.py
- Update fixos/agent/session_io.py
- Update project.sh
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/calls.toon.yaml
- Update project/calls.yaml
- ... and 13 more files

## [2.2.12] - 2026-04-09

### Docs
- Update docs/README.md
- Update project/README.md
- Update project/context.md

### Other
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- Update project/flow.png
- Update project/index.html
- Update project/map.toon.yaml
- ... and 2 more files

## [2.2.11] - 2026-04-09

### Docs
- Update docs/README.md
- Update project/README.md
- Update project/context.md

### Other
- Update project/analysis.toon.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/duplication.toon.yaml
- Update project/evolution.toon.yaml
- Update project/flow.mmd
- Update project/flow.png
- Update project/index.html
- ... and 4 more files

## [2.2.10] - 2026-04-09

### Other
- Update No changes needed for /home/tom/github/wronai/fixOS/agent/__init__.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/config.py
- Update fixos/diagnostics/flatpak_analyzer.py
- Update fixos/diagnostics/storage_analyzer.py

## [2.2.9] - 2026-04-04

### Docs
- Update .pyqual/report.md

### Other
- Update .pyqual/pipeline.db
- Update VERSION
- Update fixos/__init__.py

## [2.2.7] - 2026-04-04

### Docs
- Update CHANGELOG.md
- Update README.md
- Update docs/modules.md

### Other
- Update fixos/cli/fix_cmd.py

## [2.2.6] - 2026-04-04

### Added
- **StorageAnalyzer** - pełny audit systemu z wykrywaniem:
  - DNF cache, stare kernele, journal logs
  - Docker/Podman (dangling images, build cache)
  - Btrfs snapshots, Timeshift backups
  - Coredumps, orphaned packages, debug symbols
  - Browser profiles, Flatpak user data, OSTree repo
- **DevProjectAnalyzer** - wykrywanie folderów zależności w projektach prywatnych:
  - `node_modules`, `venv`, `.venv`, `target` (Rust/Maven)
  - `build`, `dist`, `__pycache__`, `.tox`, `.pytest_cache`
  - `vendor` (PHP), `.gradle`, `bin/obj` (.NET)
  - Automatyczne wykrywanie możliwości odtworzenia
- **Zaawansowane opcje filtrowania** w `fixos cleanup --full`:
  - `type:NAME` - usuń wybrany typ (np. `type:venv`)
  - `type:A,B,C` - usuń wiele typów (np. `type:venv,node_modules`)
  - `category:NAME` - usuń kategorię (np. `category:dev_projects`)
  - `large` - tylko duże (>1 GB)
  - `huge` - tylko bardzo duże (>5 GB)
  - `old` - stare (>30 dni)
  - `stale` - bardzo stare (>90 dni)
  - `top:N` - N największych
  - `select` - interaktywny wybór po numerach

### Fixed
- **FlatpakAnalyzer** - poprawione obliczanie rozmiaru z użyciem `du` zamiast sum logicznych
- Eliminacja fałszywych alarmów o "80 GB śmieci w Flatpak"
- Realne szacunki odzyskiwania miejsca (ratio > 2.5x dla bloat)

### Changed
- `cleanup --full` pokazuje ranking typów zależności z rozmiarami
- Lepsze kategoryzowanie elementów do czyszczenia (risk: none/low/medium)

## [2.2.5] - 2026-04-04

### Other
- Update fixos/cli/cleanup_cmd.py

## [2.2.4] - 2026-04-04

### Other
- Update fixos/diagnostics/dev_project_analyzer.py
- Update fixos/diagnostics/storage_analyzer.py

## [2.2.3] - 2026-04-04

### Other
- Update fixos/cli/cleanup_cmd.py
- Update fixos/diagnostics/flatpak_analyzer.py
- Update fixos/diagnostics/storage_analyzer.py

## [2.2.2] - 2026-04-04

### Docs
- Update .pyqual/report.md

### Other
- Update .pyqual/pipeline.db
- Update fixos/cli/cleanup_cmd.py
- Update fixos/diagnostics/flatpak_analyzer.py
- Update fixos/diagnostics/service_cleanup.py

## [2.2.1] - 2026-04-04

### Docs
- Update .pyqual/report.md

### Other
- Update .pyqual/pipeline.db

## [2.1.32] - 2026-04-04

### Docs
- Update .pyqual/report.md

### Other
- Update .pyqual/pipeline.db

## [2.1.31] - 2026-03-15

### Docs
- Update docs/README.md
- Update docs/api-changelog.md
- Update docs/architecture.md
- Update project/context.md

### Other
- Update project/analysis.toon
- Update project/analysis.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/dashboard.html
- Update project/flow.mmd
- Update project/flow.png
- Update project/flow.toon
- Update project/map.toon
- Update project/project.yaml

## [2.1.30] - 2026-03-15

### Docs
- Update docs/README.md
- Update docs/api-changelog.md
- Update docs/api.md
- Update docs/architecture.md
- Update docs/coverage.md
- Update docs/dependency-graph.md
- Update docs/index.html
- Update docs/modules.md
- Update project/README.md
- Update project/context.md

### Test
- Update test-results/alpine-build.log
- Update test-results/arch-build.log
- Update test-results/arch-unit-tests.log
- Update test-results/debian-build.log
- Update test-results/debian-unit-tests.log
- Update test-results/fedora-build.log
- Update test-results/ubuntu-build.log
- Update tests/e2e/test_cli.py

### Other
- Update fixos/agent/__init__.py
- Update fixos/agent/autonomous.py
- Update fixos/agent/autonomous_session.py
- Update fixos/agent/hitl.py
- Update fixos/agent/hitl_session.py
- Update fixos/cli/features_cmd.py
- Update fixos/cli/main.py
- Update fixos/diagnostics/service_cleanup.py
- Update fixos/diagnostics/service_details.py
- Update fixos/diagnostics/service_scanner.py
- ... and 25 more files

## [2.1.29] - 2026-03-15

### Docs
- Update docker/TEST_RESULTS_V2.md

### Test
- Update test-results/alpine-build.log
- Update test-results/alpine-version.log
- Update test-results/arch-build.log
- Update test-results/arch-unit-tests.log
- Update test-results/arch-version.log
- Update test-results/debian-build.log
- Update test-results/debian-unit-tests.log
- Update test-results/debian-version.log

### Other
- Update fixos/cli.py
- Update fixos/cli/__init__.py
- Update fixos/cli/ask_cmd.py
- Update fixos/cli/cleanup_cmd.py
- Update fixos/cli/config_cmd.py
- Update fixos/cli/fix_cmd.py
- Update fixos/cli/history_cmd.py
- Update fixos/cli/main.py
- Update fixos/cli/orchestrate_cmd.py
- Update fixos/cli/profile_cmd.py
- ... and 8 more files

## [2.1.28] - 2026-03-15

### Docs
- Update docs/README.md
- Update docs/api-changelog.md
- Update docs/api.md
- Update docs/architecture.md
- Update docs/coverage.md
- Update docs/dependency-graph.md
- Update docs/getting-started.md
- Update docs/modules.md
- Update project/README.md
- Update project/context.md

### Test
- Update test-results/alpine-build.log
- Update test-results/alpine-scan-help.log
- Update test-results/arch-build.log
- Update test-results/arch-scan-help.log
- Update test-results/debian-build.log
- Update test-results/debian-scan-help.log
- Update test-results/fedora-build.log
- Update test-results/fedora-version.log
- Update test-results/ubuntu-build.log
- Update test-results/ubuntu-scan-help.log
- ... and 1 more files

### Other
- Update fixos/cli.py
- Update fixos/diagnostics/service_scanner.py
- Update project/analysis.toon
- Update project/analysis.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/dashboard.html
- Update project/evolution.toon
- ... and 7 more files

## [2.1.27] - 2026-03-15

### Docs
- Update docs/README.md
- Update docs/api-changelog.md
- Update docs/api.md
- Update docs/architecture.md
- Update docs/coverage.md
- Update docs/dependency-graph.md
- Update docs/modules.md
- Update project/README.md
- Update project/context.md

### Test
- Update test-results/fedora-build.log
- Update test-results/fedora-scan-help.log
- Update test-results/ubuntu-build.log

### Other
- Update fixos/diagnostics/flatpak_analyzer.py
- Update project/analysis.toon
- Update project/analysis.yaml
- Update project/calls.mmd
- Update project/calls.png
- Update project/compact_flow.mmd
- Update project/compact_flow.png
- Update project/dashboard.html
- Update project/evolution.toon
- Update project/flow.mmd
- ... and 6 more files

## [2.1.26] - 2026-03-15

### Docs
- Update docker/TEST_RESULTS.md
- Update docs/README.md
- Update docs/architecture.md
- Update docs/modules.md
- Update project/context.md

### Test
- Update test-results/alpine-build.log
- Update test-results/alpine-scan-help.log
- Update test-results/alpine-unit-tests.log
- Update test-results/alpine-version.log
- Update test-results/arch-build.log
- Update test-results/arch-unit-tests.log
- Update test-results/debian-build.log
- Update test-results/fedora-build.log
- Update test-results/fedora-unit-tests.log
- Update test-results/ubuntu-build.log

### Other
- Update docker/test-multi-system.sh
- Update fixos/agent/autonomous.py
- Update fixos/agent/hitl.py
- Update fixos/cli.py
- Update fixos/llm_shell.py
- Update fixos/orchestrator/rollback.py
- Update fixos/plugins/__init__.py
- Update fixos/plugins/base.py
- Update fixos/plugins/builtin/__init__.py
- Update fixos/plugins/builtin/audio.py
- ... and 27 more files

## [2.1.25] - 2026-03-15

### Test
- Update test-results/alpine-build.log
- Update test-results/arch-build.log
- Update test-results/arch-scan-help.log
- Update test-results/arch-unit-tests.log
- Update test-results/arch-version.log
- Update test-results/debian-build.log
- Update test-results/debian-scan-help.log
- Update test-results/debian-unit-tests.log
- Update test-results/debian-version.log
- Update test-results/ubuntu-build.log
- ... and 2 more files

### Other
- Update .env.example
- Update docker/debian/Dockerfile
- Update docker/test-multi-system.sh
- Update docker/ubuntu/Dockerfile
- Update fixos/utils/anonymizer.py

## [2.1.24] - 2026-03-15

### Docs
- Update docker/README.md
- Update docs/CONTRIBUTING.md
- Update docs/README.md
- Update docs/api-changelog.md
- Update docs/api.md
- Update docs/architecture.md
- Update docs/configuration.md
- Update docs/coverage.md
- Update docs/dependency-graph.md
- Update docs/examples/advanced_usage.py
- ... and 6 more files

### Test
- Update test-results/debian-build.log
- Update test-results/debian-scan-help.log
- Update test-results/fedora-build.log
- Update test-results/fedora-scan-help.log
- Update test-results/fedora-unit-tests.log
- Update test-results/fedora-version.log
- Update test-results/ubuntu-build.log
- Update test-results/ubuntu-scan-help.log
- Update test-results/ubuntu-unit-tests.log
- Update test-results/ubuntu-version.log
- ... and 1 more files

### Other
- Update Makefile
- Update docker/alpine/Dockerfile
- Update docker/arch/Dockerfile
- Update docker/debian/Dockerfile
- Update docker/docker-compose.multi-system.yml
- Update docker/fedora/Dockerfile
- Update docker/test-multi-system.sh
- Update docker/ubuntu/Dockerfile
- Update fixos/cli.py
- Update fixos/diagnostics/service_scanner.py
- ... and 17 more files

## [2.1.16] - 2026-02-26

### Summary

feat(build): deep code analysis engine with 2 supporting modules

### Ci

- config: update ci.yml


## [2.1.15] - 2026-02-22

### Summary

fix(goal): CLI interface improvements

### Other

- update fixos/cli.py


## [2.1.14] - 2026-02-22

### Summary

fix(goal): CLI interface improvements

### Other

- update fixos/cli.py


## [2.1.13] - 2026-02-22

### Summary

fix(goal): CLI interface improvements

### Build

- update pyproject.toml

### Other

- update fixos/cli.py


## [2.1.12] - 2026-02-22

### Summary

feat(config): core module improvements

### Build

- update setup.py


## [2.1.11] - 2026-02-22

### Summary

fix(docs): CLI interface improvements

### Docs

- docs: update README
- docs: update TODO.md

### Other

- update fixos/cli.py


## [2.1.10] - 2026-02-22

### Summary

docs(docs): deep code analysis engine with 3 supporting modules

### Docs

- docs: update README
- docs: update TODO.md


## [2.1.9] - 2026-02-18

### Summary

refactor(goal): CLI interface improvements

### Other

- update fixos/agent/hitl.py
- update fixos/cli.py
- update fixos/orchestrator/orchestrator.py
- update fixos/utils/terminal.py
- update requirements.txt


## [2.1.8] - 2026-02-18

### Summary

feat(tests): CLI interface improvements

### Docs

- docs: update README

### Test

- update tests/conftest.py
- update tests/e2e/test_executor.py
- update tests/unit/test_executor.py

### Other

- docker: update docker-compose.yml
- update fixos/agent/hitl.py
- update fixos/cli.py
- update fixos/config.py
- update fixos/diagnostics/system_checks.py
- update fixos/orchestrator/orchestrator.py
- update fixos/utils/anonymizer.py
- update fixos/utils/terminal.py


## [2.1.7] - 2026-02-18

### Summary

fix(tests): CLI interface improvements

### Docs

- docs: update README

### Test

- update tests/e2e/test_cli.py
- update tests/e2e/test_executor.py
- update tests/e2e/test_network_broken.py
- update tests/unit/test_anonymizer.py
- update tests/unit/test_executor.py

### Other

- docker: update Dockerfile


## [2.1.6] - 2026-02-18

### Summary

feat(goal): CLI interface improvements

### Other

- update fixos/agent/hitl.py
- update fixos/cli.py
- update fixos/config.py


## [2.2.0] - 2026-02-18

### Naprawione błędy (Bug Fixes)

- **fix(diagnostics):** `NameError: name '_IS_LINUX' is not defined` w `diagnose_system()` –
  dodano brakujący import `IS_LINUX/IS_WINDOWS/IS_MAC/SYSTEM` z `platform_utils`
- **fix(anonymizer):** ścieżki `/home/user/.pyenv/versions/...` nie były anonimizowane –
  regex `/home/[^\s/\"']+` dopasowywał tylko jeden segment; naprawiono na pełną ścieżkę;
  zmieniono kolejność zastąpień (home path → regex → username)
- **fix(executor):** `apt-get install` bez flagi `-y` powodował interaktywny prompt i abort –
  dodano metodę `_make_noninteractive()` automatycznie wstrzykującą `-y` dla apt/apt-get/dnf/yum
- **fix(executor):** `sudo systemctl --user` powodował błąd DBUS (`$DBUS_SESSION_BUS_ADDRESS not defined`) –
  `needs_sudo()` teraz pomija `systemctl --user` (user-scope nie wymaga sudo)

### Dodane (Added)

- **feat(cli):** `fixos` bez argumentów wyświetla stylizowany ekran powitalny z listą komend,
  aktualnym statusem (provider, API key, .env) i kontekstowymi wskazówkami
- **feat(cli):** nowa komenda `fixos llm` – lista 12 providerów LLM z:
  - opisem, modelem domyślnym, zmienną env
  - klikalnym URL do strony generowania klucza API
  - oznaczeniami FREE/PAID i aktywnym providerem (`◀ aktywny`)
  - gotowymi komendami do skopiowania
  - flagą `--free` filtrującą tylko darmowe providery
- **feat(config):** rozszerzono `PROVIDER_DEFAULTS` z 5 do 12 providerów:
  anthropic, mistral, groq, together, cohere, deepseek, cerebras
- **feat(token):** auto-detekcja providera po prefiksie klucza rozszerzona o `sk-ant-` (Anthropic) i `gsk_` (Groq)
- **feat(hitl):** koloryzowany markdown output odpowiedzi LLM (ANSI):
  - 🔴/🟡/🟢 severity z kolorami
  - `` `inline code` `` → cyan, `**bold**` → biały bold
  - bloki kodu z ramkami box-drawing (`┌─ bash ─┐` / `│` / `└─┘`)
  - stdout/stderr z kolorowymi ramkami i tłem
- **feat(cli):** nowe logo ASCII fixOS zastępuje stare `fixfedora`
- **feat(providers):** `fixos providers` zaktualizowany do nowego formatu z FREE/PAID badge

### Testy (Tests)

- Dodano testy jednostkowe dla nowych funkcji anonymizera (pyenv paths, kolejność zastąpień)
- Dodano testy jednostkowe dla `CommandExecutor._make_noninteractive()` i `needs_sudo()`
- Dodano testy e2e dla scenariusza broken-network
- Dodano testy e2e dla CLI (welcome screen, llm command, token set)
- Dodano testy e2e dla executora (apt-get -y injection, systemctl --user bez sudo)
- Dodano Docker environment `broken-network`

## [2.1.5] - 2026-02-18

### Summary

fix(build): configuration management system

### Docs

- docs: update README

### Test

- update tests/test_fixos.py

### Build

- update setup.py

### Other

- update .gitignore
- update LICENSE
- update MANIFEST.in
- build: update Makefile
- docker: update Dockerfile
- docker: update Dockerfile
- docker: update Dockerfile
- docker: update Dockerfile
- docker: update docker-compose.yml
- update fixos.conf.example
- ... and 6 more


## [2.1.4] - 2026-02-18

### Summary

fix(goal): CLI interface improvements

### Other

- update fixos/cli.py
- update fixos/llm_shell.py


## [2.1.3] - 2026-02-18

### Summary

refactor(docs): CLI interface improvements

### Docs

- docs: update CONTRIBUTING.md
- docs: update INSTALL.md
- docs: update README

### Other

- update LICENSE
- update fixos/agent/autonomous.py
- update fixos/cli.py
- update fixos/diagnostics/system_checks.py
- update fixos/llm_shell.py
- update fixos/system_checks.py
- update fixos/utils/web_search.py


## [2.1.1] - 2026-02-18

### Breaking Changes

- **Package renamed**: `fixfedora` → `fixos`
- **Cross-platform support**: Linux, Windows, macOS

### Added

- **Cross-platform diagnostics** for Linux/Windows/macOS
- **platform_utils.py** module with OS detection, elevation commands, package manager detection
- **Interactive action menu** in HITL mode: `[D]` describe problem, `[1-N]` select fix, `[A]` all, `[S]` skip, `[!cmd]` run command
- **Markdown-formatted output** for command results (stdout/stderr in code blocks)
- **OS-specific diagnostics**: WMI (Windows), system_profiler (macOS), systemd/journal (Linux)

### Changed

- Class `FixFedoraConfig` → `FixOsConfig`
- CLI command `fixfedora` → `fixos`
- All imports updated from `fixfedora` to `fixos`
- Documentation updated for cross-platform support
- LLM exception handling now mock-safe (type-name matching instead of hardcoded classes)

### Removed

- Duplicate `fixfedora/` package directory
- Duplicate `fixfedora.egg-info/`
- Old `.venv/` (keeping `venv/`)

---

# Changelog

Wszystkie istentne zmiany projektu fixos.
Format oparty na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] – 2025-06

### Dodane
- Moduł diagnostyki **audio** (ALSA, PipeWire, SOF firmware, mikrofon)
- Moduł diagnostyki **thumbnails** (ffmpegthumbnailer, totem-nautilus, cache ~/.cache/thumbnails)
- Moduł diagnostyki **hardware** (DMI, BIOS, GPU, touchpad, ACPI, czujniki)
- Tryb agenta **Human-in-the-Loop** (HITL) – użytkownik zatwierdza każdą akcję
- Tryb agenta **Autonomous** – protokół JSON (`EXEC`/`SEARCH`/`SKIP`/`DONE`), lista zabronionych komend
- Obsługa wielu **providerów LLM**: Google Gemini (domyślny), OpenAI, xAI, OpenRouter, Ollama
- Domyślny model: **gemini-2.5-flash-preview-04-17**
- **Zewnętrzne źródła wiedzy** jako fallback: Bugzilla, fora, Arch Wiki, GitHub Issues, DuckDuckGo, SerpAPI
- Podgląd **zanonimizowanych danych** dla użytkownika przed wysłaniem do LLM + raport co zamaskowano
- Nowe komendy CLI: `token set/show/clear`, `config show/init/set`, `providers`, `test-llm`, `scan`, `fix`
- Konfiguracja przez **plik .env** (python-dotenv)
- **3 środowiska Docker** dla testów: `broken-audio`, `broken-thumbnails`, `broken-full`
- **Testy e2e i unit** z fixtures i mock LLM (pytest + pytest-mock)
- `pyproject.toml` jako standard pakietowania

### Zmienione
- Przepisana architektura na moduły: `agent/`, `diagnostics/`, `providers/`, `utils/`
- Anonimizacja teraz zwraca `tuple(anon_str, AnonymizationReport)` z kategoryzacją
- LLMClient z retry logic (3 próby), obsługą rate limit, streamingiem
- Timeout sesji przez `signal.SIGALRM` z graceful shutdown (Linux/macOS)

### Usunięte
- Monolityczny `diagnose.py` i `llm_shell.py` z v1.0
- Zależność od `tabulate` (zbędna)

---

## [1.0.0] – 2025-05

### Dodane
- Podstawowa diagnostyka systemu (CPU, RAM, dyski, usługi)
- Anonimizacja IP, hostname, ścieżek
- Interaktywny shell LLM z timeoutem 1h
- CLI: `fixos --token sk-...`
- Obsługa OpenAI API
- `setup.py`, `requirements.txt`
