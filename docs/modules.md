# fixos — Module Reference

> 188 modules | 938 functions | 110 classes

## Module Overview

| Module | Lines | Functions | Classes | CC avg | Description | Source |
|--------|-------|-----------|---------|--------|-------------|--------|
| `docker.test-multi-system` | 128 | 1 | 0 | — | — | [source](https://github.com/semcod/fixos/blob/main/docker/test-multi-system.sh) |
| `docker.test-scenarios` | 147 | 3 | 0 | — | — | [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh) |
| `docker.validate-scenario` | 169 | 3 | 0 | 7.3 | Validates fixOS scan YAML output against expected scenario c | [source](https://github.com/semcod/fixos/blob/main/docker/validate-scenario.py) |
| `docs.examples.quickstart` | 5 | 1 | 0 | 1.0 | — | [source](https://github.com/semcod/fixos/blob/main/docs/examples/quickstart.py) |
| `fixos.agent` | 39 | 1 | 0 | 2.0 | Agent module for fixOS - HITL and Autonomous session managem | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/__init__.py) |
| `fixos.agent.autonomous` | 49 | 1 | 0 | 1.0 | Tryb autonomiczny – agent sam diagnozuje i naprawia system. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous.py) |
| `fixos.agent.autonomous_session` | 473 | 1 | 3 | 2.8 | Autonomous Session for fixOS Agent | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py) |
| `fixos.agent.hitl` | 36 | 1 | 0 | 1.0 | Tryb Human-in-the-Loop (HITL) – użytkownik zatwierdza każdą  | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl.py) |
| `fixos.agent.hitl_session` | 379 | 1 | 1 | 4.2 | Human-in-the-Loop (HITL) Session for fixOS Agent | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py) |
| `fixos.agent.session_core` | 722 | 22 | 3 | 5.7 | Core session types and constants for HITL agent. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py) |
| `fixos.agent.session_handlers` | 572 | 18 | 0 | 4.5 | Command handlers for HITL session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py) |
| `fixos.agent.session_io` | 404 | 27 | 0 | 2.2 | UI/IO operations for HITL session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py) |
| `fixos.anonymizer` | 18 | 2 | 0 | 1.0 | Compatibility facade for the shared context-preserving anony | [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py) |
| `fixos.cli._cleanup_flatpak` | 292 | 3 | 0 | 9.0 | Flatpak-specific cleanup CLI handlers. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/_cleanup_flatpak.py) |
| `fixos.cli._cleanup_home` | 181 | 5 | 0 | 6.4 | Home directory analysis and cleanup CLI handlers. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/_cleanup_home.py) |
| `fixos.cli._cleanup_snap` | 170 | 6 | 0 | 5.3 | Snap package management CLI handlers. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/_cleanup_snap.py) |
| `fixos.cli._cleanup_system` | 603 | 17 | 0 | 6.7 | Full-system storage analysis and cleanup CLI handlers. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/_cleanup_system.py) |
| `fixos.cli._cleanup_utils` | 128 | 6 | 0 | 5.2 | Shared utilities for cleanup CLI commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/_cleanup_utils.py) |
| `fixos.cli.ask_cmd` | 496 | 8 | 0 | 10.2 | Natural language command (ask) for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/ask_cmd.py) |
| `fixos.cli.cleanup_cmd` | 1662 | 30 | 0 | 11.2 | Cleanup command for fixOS CLI - service data cleanup with de | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/cleanup_cmd.py) |
| `fixos.cli.config_cmd` | 274 | 11 | 0 | 4.4 | Config management commands for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py) |
| `fixos.cli.features_cmd` | 188 | 8 | 0 | 4.8 | Features CLI command for fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py) |
| `fixos.cli.fix_cmd` | 416 | 6 | 0 | 7.7 | Fix command for fixOS CLI - diagnostics and repair session w | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py) |
| `fixos.cli.history_cmd` | 52 | 1 | 0 | 5.0 | History command for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/history_cmd.py) |
| `fixos.cli.jetbrains_cmd` | 358 | 7 | 0 | 9.7 | JetBrains JVM diagnosis and window-preserving recovery CLI. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py) |
| `fixos.cli.main` | 285 | 4 | 0 | 4.0 | Main CLI entry point for fixOS | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py) |
| `fixos.cli.orchestrate_cmd` | 163 | 1 | 0 | 13.0 | Orchestrate command for fixOS CLI - advanced repair with pro | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/orchestrate_cmd.py) |
| `fixos.cli.output_formatter` | 161 | 1 | 2 | 1.9 | Centralized output formatter for fixOS CLI. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py) |
| `fixos.cli.profile_cmd` | 59 | 3 | 0 | 3.0 | Profile commands for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py) |
| `fixos.cli.projects_cmd` | 490 | 13 | 0 | 7.0 | Projects command for fixOS CLI - developer project artifact  | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/projects_cmd.py) |
| `fixos.cli.provider_cmd` | 271 | 3 | 0 | 6.3 | Provider management commands for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py) |
| `fixos.cli.quick_cmd` | 224 | 6 | 0 | 8.2 | Fast heuristic diagnostics command. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py) |
| `fixos.cli.quickfix_cmd` | 82 | 1 | 0 | 12.0 | Quickfix command for fixOS CLI - heuristic fixes without LLM | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quickfix_cmd.py) |
| `fixos.cli.report_cmd` | 144 | 5 | 0 | 3.8 | Report command for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/report_cmd.py) |
| `fixos.cli.rollback_cmd` | 97 | 4 | 0 | 4.0 | Rollback commands for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py) |
| `fixos.cli.scan_cmd` | 334 | 6 | 0 | 9.2 | Scan command for fixOS CLI - system diagnostics | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/scan_cmd.py) |
| `fixos.cli.shared` | 202 | 3 | 1 | 5.5 | Shared utilities for fixOS CLI commands | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py) |
| `fixos.cli.shell_cmd` | 199 | 4 | 0 | 5.0 | Interactive shell (REPL) and menu for fixOS CLI. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py) |
| `fixos.cli.token_cmd` | 141 | 4 | 0 | 3.2 | Token management commands for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py) |
| `fixos.cli.watch_cmd` | 67 | 1 | 0 | 2.0 | Watch daemon command for fixOS CLI | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/watch_cmd.py) |
| `fixos.config` | 530 | 7 | 1 | 5.9 | Zarządzanie konfiguracją fixos. | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py) |
| `fixos.config_interactive` | 153 | 5 | 0 | 6.4 | Interactive provider setup module. | [source](https://github.com/semcod/fixos/blob/main/fixos/config_interactive.py) |
| `fixos.diagnostics._flatpak_analysis_mixin` | 319 | 0 | 1 | 7.3 | Analysis methods for FlatpakAnalyzer (load refs, find unused | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/_flatpak_analysis_mixin.py) |
| `fixos.diagnostics._flatpak_execution_mixin` | 240 | 0 | 1 | 5.4 | Cleanup execution methods for FlatpakAnalyzer. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/_flatpak_execution_mixin.py) |
| `fixos.diagnostics._flatpak_recommendations_mixin` | 299 | 0 | 1 | 4.7 | Recommendation generation methods for FlatpakAnalyzer. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/_flatpak_recommendations_mixin.py) |
| `fixos.diagnostics._storage_container_mixin` | 176 | 0 | 1 | 4.1 | Container storage analyzers (Docker, Podman). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/_storage_container_mixin.py) |
| `fixos.diagnostics._storage_system_mixin` | 286 | 0 | 1 | 4.9 | System-level storage analyzers (DNF, kernels, journal, orpha | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/_storage_system_mixin.py) |
| `fixos.diagnostics._storage_user_mixin` | 395 | 0 | 1 | 6.3 | User-level storage analyzers (cache, browsers, flatpak, dev  | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/_storage_user_mixin.py) |
| `fixos.diagnostics.cache_discovery` | 256 | 7 | 0 | 5.0 | Generic cache discovery for fixOS cleanup. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py) |
| `fixos.diagnostics.checks._shared` | 49 | 2 | 0 | 4.0 | Shared utilities for diagnostic check modules. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/_shared.py) |
| `fixos.diagnostics.checks.audio` | 77 | 1 | 0 | 1.0 | Audio diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/audio.py) |
| `fixos.diagnostics.checks.file_analysis` | 320 | 6 | 0 | 1.5 | File analysis diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/file_analysis.py) |
| `fixos.diagnostics.checks.hardware` | 51 | 1 | 0 | 1.0 | Hardware diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/hardware.py) |
| `fixos.diagnostics.checks.packages` | 203 | 6 | 0 | 1.5 | Package environment diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/packages.py) |
| `fixos.diagnostics.checks.resources` | 165 | 1 | 0 | 13.0 | Resources diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/resources.py) |
| `fixos.diagnostics.checks.security` | 144 | 1 | 0 | 4.0 | Security diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/security.py) |
| `fixos.diagnostics.checks.storage_optimization` | 201 | 6 | 0 | 1.5 | Storage optimization diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/storage_optimization.py) |
| `fixos.diagnostics.checks.system_core` | 154 | 3 | 0 | 5.7 | System core diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/system_core.py) |
| `fixos.diagnostics.checks.thumbnails` | 78 | 1 | 0 | 1.0 | Thumbnails diagnostics module. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/thumbnails.py) |
| `fixos.diagnostics.dev_project_analyzer` | 459 | 0 | 2 | 4.5 | Dev Project Analyzer for FixOS - analyze developer project d | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py) |
| `fixos.diagnostics.disk_analyzer` | 495 | 1 | 1 | 6.2 | Disk Analyzer Module for fixOS | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py) |
| `fixos.diagnostics.docker_network_cleanup` | 282 | 0 | 1 | 12.2 | Bezpieczne zwalnianie nieużywanych sieci Docker i kontrola p | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_network_cleanup.py) |
| `fixos.diagnostics.docker_startup_optimizer` | 560 | 0 | 1 | 9.3 | Conservative optimization of stale Docker startup workloads. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_startup_optimizer.py) |
| `fixos.diagnostics.flatpak_analyzer` | 166 | 1 | 3 | 3.1 | Advanced Flatpak analyzer for fixOS | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py) |
| `fixos.diagnostics.jetbrains_ai` | 294 | 0 | 2 | 6.1 | Exact, window-preserving control of JetBrains AI plugins and | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py) |
| `fixos.diagnostics.jetbrains_recovery` | 638 | 8 | 8 | 7.9 | Diagnose and recover a shared JetBrains JVM without closing  | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py) |
| `fixos.diagnostics.orphaned_workloads` | 731 | 0 | 2 | 7.6 | Evidence-led cleanup for workloads whose development project | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py) |
| `fixos.diagnostics.process_chains` | 594 | 6 | 6 | 7.0 | Evidence-led diagnostics for fresh process chains. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py) |
| `fixos.diagnostics.project_scanner` | 258 | 9 | 1 | 5.0 | Developer Project Scanner for fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py) |
| `fixos.diagnostics.quick_snapshot` | 845 | 20 | 1 | 7.3 | Fast, local system snapshot used before the full fixOS analy | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py) |
| `fixos.diagnostics.service_cleanup` | 1609 | 0 | 1 | 7.3 | Service Cleanup for fixOS | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_cleanup.py) |
| `fixos.diagnostics.service_details` | 249 | 0 | 1 | 5.4 | Service Details Provider for fixOS | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_details.py) |
| `fixos.diagnostics.service_scanner` | 701 | 1 | 4 | 4.7 | Service Data Scanner for fixOS | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py) |
| `fixos.diagnostics.storage_analyzer` | 287 | 0 | 2 | 3.9 | Storage Analyzer for FixOS - comprehensive disk space analys | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py) |
| `fixos.diagnostics.system_checks` | 114 | 2 | 0 | 7.0 | System diagnostics aggregator. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/system_checks.py) |
| `fixos.diagnostics.utils` | 12 | 1 | 0 | 3.0 | Shared utilities for diagnostic modules. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/utils.py) |
| `fixos.endpoint_refresh` | 200 | 5 | 1 | 9.8 | Safe, DNS-backed observation of configured service endpoints | [source](https://github.com/semcod/fixos/blob/main/fixos/endpoint_refresh.py) |
| `fixos.features` | 273 | 0 | 2 | 5.0 | System detection module for fixOS features. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py) |
| `fixos.features.auditor` | 128 | 0 | 2 | 5.0 | Feature auditor - compares system state with desired profile | [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py) |
| `fixos.features.catalog` | 128 | 0 | 3 | 3.0 | Package catalog - loads and manages package database from YA | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py) |
| `fixos.features.installer` | 176 | 0 | 1 | 3.2 | Feature installer - safely installs missing packages. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/installer.py) |
| `fixos.features.profiles` | 93 | 0 | 1 | 4.0 | User profile management for fixOS features. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/profiles.py) |
| `fixos.features.renderer` | 142 | 0 | 1 | 5.0 | Feature renderer - displays audit results in terminal. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/renderer.py) |
| `fixos.interactive.cleanup_planner` | 469 | 1 | 4 | 4.8 | Interactive Cleanup Planner for fixOS | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py) |
| `fixos.llm_shell` | 260 | 6 | 0 | 5.3 | Interaktywny shell LLM do diagnostyki i naprawy systemu syst | [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py) |
| `fixos.orchestrator.executor` | 309 | 0 | 4 | 3.8 | CommandExecutor – bezpieczne wykonywanie komend systemowych. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py) |
| `fixos.orchestrator.graph` | 165 | 0 | 2 | 3.5 | Problem Graph – model danych dla kaskadowych problemów syste | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py) |
| `fixos.orchestrator.orchestrator` | 431 | 0 | 2 | 4.5 | FixOrchestrator – główna pętla egzekucji napraw. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/orchestrator.py) |
| `fixos.orchestrator.rollback` | 175 | 0 | 2 | 3.7 | Rollback system for fixOS — tracks executed operations and a | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py) |
| `fixos.orphan_pins` | 155 | 2 | 2 | 4.0 | Persistent protection for intentionally retained orphan proj | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py) |
| `fixos.platform_utils` | 251 | 11 | 0 | 3.5 | Cross-platform utilities for fixos. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py) |
| `fixos.plugins.base` | 103 | 0 | 4 | 1.2 | Base classes for fixOS diagnostic plugins. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py) |
| `fixos.plugins.builtin.audio` | 117 | 0 | 1 | 4.4 | Audio diagnostic plugin — ALSA, PipeWire, PulseAudio, SOF fi | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py) |
| `fixos.plugins.builtin.disk` | 133 | 0 | 1 | 7.2 | Disk diagnostic plugin — usage, partitions, SMART health. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py) |
| `fixos.plugins.builtin.hardware` | 142 | 0 | 1 | 5.2 | Hardware diagnostic plugin — DMI, GPU, touchpad, camera, bat | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py) |
| `fixos.plugins.builtin.resources` | 148 | 0 | 1 | 4.7 | Resources diagnostic plugin — CPU, RAM, processes, autostart | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py) |
| `fixos.plugins.builtin.security` | 212 | 0 | 1 | 5.4 | Security diagnostic plugin — firewall, ports, SELinux, SSH,  | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py) |
| `fixos.plugins.builtin.thumbnails` | 134 | 0 | 1 | 4.6 | Thumbnails diagnostic plugin — cache, GStreamer, thumbnailer | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py) |
| `fixos.plugins.registry` | 137 | 0 | 1 | 2.9 | Plugin registry with autodiscovery for fixOS diagnostic plug | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/registry.py) |
| `fixos.profiles` | 66 | 0 | 1 | 2.7 | Diagnostic profiles for fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/profiles/__init__.py) |
| `fixos.providers.llm` | 343 | 0 | 4 | 5.3 | Ujednolicony klient LLM obsługujący wiele providerów przez O | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py) |
| `fixos.providers.llm_analyzer` | 358 | 1 | 2 | 5.2 | LLM Analyzer for fixOS - Fallback analysis when heuristics a | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py) |
| `fixos.providers.schemas` | 80 | 0 | 5 | — | Pydantic schemas for structured LLM output. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py) |
| `fixos.system_checks` | 168 | 8 | 0 | 2.6 | Moduł zbierający dane diagnostyczne z systemu system. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py) |
| `fixos.utils.anonymizer` | 560 | 21 | 3 | 3.7 | Anonimizacja wrażliwych danych systemowych z podglądem dla u | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py) |
| `fixos.utils.terminal` | 342 | 12 | 1 | 3.4 | Terminal rendering utilities – shared between hitl, orchestr | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py) |
| `fixos.utils.timeout` | 18 | 1 | 1 | 1.0 | Shared SessionTimeout exception and timeout handler for fixO | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py) |
| `fixos.utils.web_search` | 276 | 9 | 1 | 4.9 | Zewnętrzne źródła wiedzy – fallback gdy LLM nie zna rozwiąza | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py) |
| `fixos.watch` | 156 | 0 | 1 | 4.5 | Watch mode daemon for fixOS — periodic diagnostics with desk | [source](https://github.com/semcod/fixos/blob/main/fixos/watch.py) |
| `scripts.pyqual-calibrate` | 290 | 7 | 0 | 5.4 | Auto-kalibracja progów metryk dla pyqual. | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py) |
| `scripts.runtime` | 858 | 24 | 0 | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh) |

## docker

### `docker.test-multi-system` [source](https://github.com/semcod/fixos/blob/main/docker/test-multi-system.sh)

- `test_system()` [source](https://github.com/semcod/fixos/blob/main/docker/test-multi-system.sh#L33)

### `docker.test-scenarios` [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh)

- `build_base()` [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh#L46)
- `main()` [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh#L105)
- `run_scenario()` [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh#L53)

### `docker.validate-scenario` [source](https://github.com/semcod/fixos/blob/main/docker/validate-scenario.py)

Validates fixOS scan YAML output against expected scenario conditions.

- `main()` [source](https://github.com/semcod/fixos/blob/main/docker/validate-scenario.py#L127)
- `validate(data, scenario)` — Validate data against scenario expectations. Returns list of failures. [source](https://github.com/semcod/fixos/blob/main/docker/validate-scenario.py#L84)

## docs

### `docs.examples.quickstart` [source](https://github.com/semcod/fixos/blob/main/docs/examples/quickstart.py)

- `run_autonomous_session()` [source](https://github.com/semcod/fixos/blob/main/docs/examples/quickstart.py#L4)

## fixos

### `fixos.agent` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/__init__.py)

Agent module for fixOS - HITL and Autonomous session management.

- `get_remaining_time(session)` — Calculate remaining session time in seconds. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/__init__.py#L22)

### `fixos.agent.autonomous` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous.py)

Tryb autonomiczny – agent sam diagnozuje i naprawia system.

- `run_autonomous_session(diagnostics, config, show_data, max_fixes)` — Uruchamia autonomiczny tryb agenta. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous.py#L31)

### `fixos.agent.autonomous_session` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py)

Autonomous Session for fixOS Agent

**`AgentReport`** [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L90)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `summary` | `` | `—` | 4 |

**`AutonomousSession`** [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L113)
: Self-directed autonomous diagnostic and repair session.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `run` | `` | `—` | 6 |

**`FixAction`** [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L81)

- `run_autonomous_session(diagnostics, config, show_data, max_fixes)` — Run autonomous session (backward compatible wrapper). [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L460)

### `fixos.agent.hitl` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl.py)

Tryb Human-in-the-Loop (HITL) – użytkownik zatwierdza każdą akcję.

- `run_hitl_session(diagnostics, config, show_data)` — Run interactive HITL session with full transparency. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl.py#L24)

### `fixos.agent.hitl_session` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py)

Human-in-the-Loop (HITL) Session for fixOS Agent

**`HITLSession`** [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L36)
: Interactive Human-in-the-Loop diagnostic and repair session.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `remaining` | `` | `—` | 1 |
| `run` | `` | `—` | 5 |

- `run_hitl_session(diagnostics, config, show_data)` — Run interactive HITL session (backward compatible wrapper). [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L359)

### `fixos.agent.session_core` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py)

Core session types and constants for HITL agent.

**`CmdResult`** [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L19)
: Result of executed command.

**`DiagnosticChoice`** [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L76)
: A diagnosed problem that is selectable but has no executable plan yet.

**`RemediationAction`** [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L43)
: One policy-labelled strategy for resolving a diagnostic finding.

- `extract_diagnostic_choices(reply)` — Extract non-executable choices from numbered diagnosis headings. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L628)
- `extract_fixes(reply)` — Extract (command, comment) pairs from LLM reply. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L380)
- `extract_remediation_actions(reply)` — Parse a closed remediation plan, falling back to legacy command syntax. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L603)
- `extract_search_topic(llm_reply)` — Extract search keywords from LLM reply. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L710)
- `select_recommended_actions(actions)` — Return at most one recommended strategy for each finding. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L697)
- `strip_remediation_plan(reply)` — Hide the machine plan block from the human-readable diagnosis. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L617)
- `transform_remediation_commands(action, transform)` — Apply anonymization reversal to executable fields only. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L674)

### `fixos.agent.session_handlers` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py)

Command handlers for HITL session.

- `handle_cleanup_intent(messages)` — Ask for a cleanup plan without authorizing or executing any command. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L111)
- `handle_describe_problem(messages, ask_fn)` — Handle [D] Describe own problem command. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L86)
- `handle_direct_command(user_in, messages, executed, run_cmd_fn)` — Handle [!cmd] Direct command execution. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L408)
- `handle_execute_all(fixes, messages, executed, run_cmd_fn)` — Handle [A] Execute all commands. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L283)
- `handle_fix_by_number(user_in, fixes, messages, executed, run_cmd_fn)` — Handle [N] Execute specific fix by number. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L344)
- `handle_free_text(user_in, messages)` — Handle free text input → send to LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L443)
- `handle_quit()` — Handle [Q] Quit command. Returns False to exit loop. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L72)
- `handle_search(user_in, messages, serpapi_key)` — Handle [search <q>] Web search command. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L425)
- `handle_skip_all(messages)` — Handle [S] Skip all command. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L78)
- `is_cleanup_intent(user_in)` — Recognize a bounded single-word spelling variant of ``cleanup``. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L103)
- `parse_user_input(user_in, fixes, messages, executed, serpapi_key)` — Parse user input and execute appropriate handler. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L515)
- `run_single_command(cmd, comment)` — Run a command with full transparency and safety checks. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L449)

### `fixos.agent.session_io` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py)

UI/IO operations for HITL session.

- `ask_execute_prompt()` — Ask user if they want to execute a command. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L375)
- `ask_low_confidence_search()` — Ask user if they want to search when LLM is uncertain. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L381)
- `ask_send_data()` — Ask user if they want to send data to LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L389)
- `ask_user_problem()` — Interactively asks the user to describe their problem. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L222)
- `clear_thinking()` — Clear the 'Analyzing...' indicator. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L300)
- `fmt_time(s)` — Format seconds as HH:MM:SS. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L81)
- `get_user_input(remaining)` — Get user input with prompt. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L396)
- `print_action_menu(fixes, remaining, total_tokens, completed_count)` — Print the refreshed interactive menu of remaining choices. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L86)
- `print_blocked_command(cmd, reason)` — Print blocked dangerous command warning. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L317)
- `print_cmd_preview(cmd, comment)` — Shows command in a clear block before execution. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L254)
- `print_cmd_result(result)` — Shows command result with colorized markdown. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L259)
- `print_executing_all(count)` — Print executing all recommended command sets message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L338)
- `print_invalid_option(user_in, max_option)` — Print invalid option message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L358)
- `print_llm_error(e)` — Print LLM error message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L312)
- `print_llm_reply(reply)` — Render LLM reply with markdown formatting. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L305)
- `print_no_commands()` — Print no commands available message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L345)
- `print_no_results()` — Print no search results message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L365)
- `print_searching()` — Print searching message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L370)
- `print_select_one()` — Explain that diagnosis-only choices must be focused individually. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L350)
- `print_session_ended()` — Print session ended message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L328)
- `print_session_header(os_info, pkg_manager, model, timeout, remaining_fn)` — Print session header with system info. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L64)
- `print_session_interrupted()` — Print session interrupted message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L333)
- `print_session_summary(messages_count, elapsed, total_tokens, executed)` — Print session summary. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L284)
- `print_thinking()` — Print 'Analyzing...' indicator. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L295)
- `print_timeout()` — Print session timeout message. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L323)
- `suspend_timeout()` — Context manager to temporarily suspend session timeout during user input. [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L39)

### `fixos.anonymizer` [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py)

Compatibility facade for the shared context-preserving anonymizer.

- `anonymize(data_str)` — Keep the original string-only return shape used by ``llm_shell``. [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py#L16)
- `get_sensitive_values()` — Return legacy key names without maintaining a second privacy policy. [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py#L6)

### `fixos.cli.ask_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/ask_cmd.py)

Natural language command (ask) for fixOS CLI

- `ask(prompt, dry_run)` — Wykonaj polecenie w języku naturalnym. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/ask_cmd.py#L13)

### `fixos.cli.cleanup_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/cleanup_cmd.py)

Cleanup command for fixOS CLI - service data cleanup with detailed flatpak support.

- `cleanup_services(threshold, services, json_output, cleanup, docker_old, docker_all, docker_networks, docker_stale_services, orphaned_projects, pin_orphan_project, unpin_orphan_project, list_orphan_pins, process_hours, ollama_old, days, dry_run, list_only, full_analysis)` — Skanuje i czyści dane usług przekraczające próg. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/cleanup_cmd.py#L1416)

### `fixos.cli.config_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py)

Config management commands for fixOS CLI

- `config()` — Zarządzanie konfiguracją fixOS. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L41)
- `config_init(force)` — Zainicjalizuj plik konfiguracyjny .env. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L77)
- `config_model(provider)` — Interaktywnie wybierz model LLM z listy. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L133)
- `config_provider()` — Interaktywnie wybierz providera LLM z listy. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L262)
- `config_set(key, value)` — Ustaw wartość konfiguracyjną w .env. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L112)
- `config_show()` — Pokaż aktualną konfigurację. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L47)

### `fixos.cli.features_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py)

Features CLI command for fixOS.

- `features()` — Zarządzanie pakietami komfortu systemu. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L20)
- `features_audit(profile, json_output)` — Sprawdź brakujące pakiety dla profilu. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L30)
- `features_install(profile, dry_run, yes, category)` — Zainstaluj brakujące pakiety dla profilu. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L91)
- `features_profiles()` — Lista dostępnych profili. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L122)
- `features_system()` — Pokaż wykryty system. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L143)

### `fixos.cli.fix_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py)

Fix command for fixOS CLI - diagnostics and repair session with LLM

- `execute_cleanup_actions(actions, cfg, llm_fallback)` — Execute cleanup actions with safety checks [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L349)
- `fix(provider, token, model, no_banner, mode, timeout, modules, no_show_data, output, max_fixes, disc, dry_run, interactive, json_output, yaml_output, llm_fallback, show_raw)` — Przeprowadza pełną diagnostykę i uruchamia sesję naprawczą z LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L130)
- `handle_disk_cleanup_mode(disk_analysis, cfg, dry_run, interactive, json_output, llm_fallback)` — Handle disk cleanup mode with interactive planning [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L245)
- `try_llm_fallback_for_failures(failed_actions, cfg)` — Try to fix failed actions using LLM [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L390)

### `fixos.cli.history_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/history_cmd.py)

History command for fixOS CLI

- `history(limit, json_output)` — Historia napraw fixOS. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/history_cmd.py#L11)

### `fixos.cli.jetbrains_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py)

JetBrains JVM diagnosis and window-preserving recovery CLI.

- `ai_control(config_dir, disable_plugins, stop_qoder, apply, yes, json_output)` — Diagnozuj i ogranicz dodatki AI bez zamykania okien IDE. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L283)
- `doctor(pid, minutes, no_thread_dump, json_output, apply_gc, yes)` — Zbierz metryki JVM, stan EDT i sygnały z idea.log. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L162)
- `jetbrains()` — Diagnozuj współdzieloną JVM JetBrains bez zamykania okien. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L137)

### `fixos.cli.main` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py)

Main CLI entry point for fixOS

- `cli(ctx, dry_run, interactive_mode, version)` — fixos – AI-powered diagnostyka i naprawa Linux, Windows, macOS. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L28)
- `main()` — Entry point for fixOS CLI. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L239)

### `fixos.cli.orchestrate_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/orchestrate_cmd.py)

Orchestrate command for fixOS CLI - advanced repair with problem graph

- `orchestrate(provider, token, model, no_banner, mode, modules, dry_run, max_iterations, output)` — Zaawansowana orkiestracja napraw z grafem problemów. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/orchestrate_cmd.py#L30)

### `fixos.cli.output_formatter` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py)

Centralized output formatter for fixOS CLI.

**`OutputFormat`** (Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L24)
: Supported output formats.

**`OutputFormatter`** [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L43)
: Centralized output formatter for fixOS CLI commands.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `from_flags` | `cls, yaml_output, json_output` | `—` | 3 |
| `status` | `msg, fg, bold` | `—` | 3 |
| `progress` | `name, desc` | `—` | 1 |
| `banner` | `text` | `—` | 2 |
| `emit` | `data, stream` | `—` | 1 |
| `format_data` | `data` | `—` | 3 |
| `format_diagnostics` | `data` | `—` | 3 |
| `format_scan_result` | `data` | `—` | 2 |

### `fixos.cli.profile_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py)

Profile commands for fixOS CLI

- `profile()` — Zarządzanie profilami diagnostycznymi. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L9)
- `profile_list()` — Pokaż dostępne profile diagnostyczne. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L15)
- `profile_show(name)` — Pokaż szczegóły profilu diagnostycznego. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L42)

### `fixos.cli.projects_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/projects_cmd.py)

Projects command for fixOS CLI - developer project artifact scanner.

- `projects_cmd(path, threshold, stale_days, only_stale, max_depth, json_output, list_only, dry_run, docker_networks)` — Skanuje projekty deweloperskie (np. ~/github/*/*) w poszukiwaniu [source](https://github.com/semcod/fixos/blob/main/fixos/cli/projects_cmd.py#L384)

### `fixos.cli.provider_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py)

Provider management commands for fixOS CLI

- `llm_providers(free)` — Lista dostępnych providerów LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L110)
- `providers()` — Lista providerów LLM z oznaczeniem FREE/PAID. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L159)
- `test_llm(provider, token, model, no_banner)` — Test połączenia z LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L201)

### `fixos.cli.quick_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py)

Fast heuristic diagnostics command.

- `quick(hours, json_output, deep, no_save)` — Natychmiastowa analiza CPU, RAM, dysku, cache i ostatnich przyrostów. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L179)
- `render_quick_snapshot(snapshot)` — Render the quick snapshot in a stable, readable form. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L26)

### `fixos.cli.quickfix_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quickfix_cmd.py)

Quickfix command for fixOS CLI - heuristic fixes without LLM

- `quickfix(dry_run, modules)` — Natychmiastowe naprawy bez API — baza znanych bugów. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quickfix_cmd.py#L13)

### `fixos.cli.report_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/report_cmd.py)

Report command for fixOS CLI

- `report(output_format, output, modules, profile)` — Eksport wyników diagnostyki do raportu HTML/Markdown/JSON. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/report_cmd.py#L97)

### `fixos.cli.rollback_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py)

Rollback commands for fixOS CLI

- `rollback()` — Zarządzanie cofaniem operacji fixOS. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L10)
- `rollback_list(limit)` — Pokaż historię sesji naprawczych. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L17)
- `rollback_show(session_id)` — Pokaż szczegóły sesji rollback. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L38)
- `rollback_undo(session_id, last, dry_run)` — Cofnij operacje z podanej sesji. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L70)

### `fixos.cli.scan_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/scan_cmd.py)

Scan command for fixOS CLI - system diagnostics

- `scan(modules, output, show_raw, no_banner, disc, dry_run, interactive, json_output, yaml_output, llm_fallback, profile, modules_csv)` — Przeprowadza diagnostykę systemu. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/scan_cmd.py#L70)

### `fixos.cli.shared` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py)

Shared utilities for fixOS CLI commands

**`NaturalLanguageGroup`** (click.Group) [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L107)
: Click group that intelligently handles typos and routes natural language commands to 'ask'.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `resolve_command` | `ctx, args` | `—` | 18 |

- `add_common_options(fn)` — Decorator adding common LLM options to a Click command. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L45)
- `add_shared_options(func)` — Shared options for both scan and fix commands. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L52)
- `get_banner()` — Return the CLI banner with the installed package version. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L19)

### `fixos.cli.shell_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py)

Interactive shell (REPL) and menu for fixOS CLI.

- `get_command_completer()` — Build a nested completer for all fixOS commands and common options. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L20)
- `print_interactive_menu()` — Display the interactive quick menu. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L69)
- `run_interactive_shell(ctx)` — Run the main interactive prompt loop. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L127)
- `shell_cmd(ctx)` — Uruchom interaktywny shell fixOS z menu i autouzupełnianiem TAB. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L122)

### `fixos.cli.token_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py)

Token management commands for fixOS CLI

- `token()` — Zarządzanie tokenem API. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L11)
- `token_clear(env_file)` — Usuń token z pliku .env. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L113)
- `token_set(key, provider, env_file)` — Zapisz token API do pliku .env. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L22)
- `token_show()` — Pokaż obecny token (masked). [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L97)

### `fixos.cli.watch_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/watch_cmd.py)

Watch daemon command for fixOS CLI

- `watch(interval, modules, alert_on, max_iterations)` — Monitorowanie systemu w tle z powiadomieniami. [source](https://github.com/semcod/fixos/blob/main/fixos/cli/watch_cmd.py#L36)

### `fixos.config` [source](https://github.com/semcod/fixos/blob/main/fixos/config.py)

Zarządzanie konfiguracją fixos.

**`FixOsConfig`** [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L199)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `load` | `cls` | `—` | 21 |
| `validate` | `` | `—` | 4 |
| `summary` | `` | `—` | 6 |

- `detect_provider_from_key(key)` — Wykrywa provider na podstawie prefiksu klucza API. [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L497)
- `get_providers_list()` — Zwraca listę providerów jako listę słowników. [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L516)
- `interactive_provider_setup()` — Interaktywny wybór providera gdy brak konfiguracji. [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L505)

### `fixos.config_interactive` [source](https://github.com/semcod/fixos/blob/main/fixos/config_interactive.py)

Interactive provider setup module.

- `interactive_provider_setup()` — Interaktywny wybór providera gdy brak konfiguracji. [source](https://github.com/semcod/fixos/blob/main/fixos/config_interactive.py#L121)

### `fixos.diagnostics.cache_discovery` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py)

Generic cache discovery for fixOS cleanup.

- `discover_additional_caches(get_size_mb, threshold_mb, covered_paths)` — Discover large caches not already covered by known service scanners. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L109)
- `is_generic_cache_safe(path)` — Heuristic safety check for unknown cache directories. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L103)
- `normalize_path(path)` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L85)
- `path_is_covered(path, covered_paths)` — Return True when path is already represented by a known service scan. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L89)

### `fixos.diagnostics.checks.audio` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/audio.py)

Audio diagnostics module.

- `diagnose_audio()` — Diagnostyka dźwięku (ALSA/PipeWire/PulseAudio/SOF). [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/audio.py#L11)

### `fixos.diagnostics.checks.file_analysis` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/file_analysis.py)

File analysis diagnostics module.

- `diagnose_files()` — Diagnostyka plików użytkownika. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/file_analysis.py#L17)

### `fixos.diagnostics.checks.hardware` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/hardware.py)

Hardware diagnostics module.

- `diagnose_hardware()` — Diagnostyka sprzętu laptopa/desktopa (ACPI, kamera, touchpad, DMI). [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/hardware.py#L10)

### `fixos.diagnostics.checks.packages` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/packages.py)

Package environment diagnostics module.

- `diagnose_packages()` — Diagnostyka zainstalowanych pakietów i środowiska. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/packages.py#L18)

### `fixos.diagnostics.checks.resources` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/resources.py)

Resources diagnostics module.

- `diagnose_resources()` — Diagnostyka zasobów systemowych. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/resources.py#L24)

### `fixos.diagnostics.checks.security` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/security.py)

Security diagnostics module.

- `diagnose_security()` — Diagnostyka bezpieczeństwa systemu i sieci. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/security.py#L18)

### `fixos.diagnostics.checks.storage_optimization` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/storage_optimization.py)

Storage optimization diagnostics module.

- `diagnose_storage()` — Diagnostyka optymalizacji dysków i partycji. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/storage_optimization.py#L11)

### `fixos.diagnostics.checks.system_core` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/system_core.py)

System core diagnostics module.

- `diagnose_system()` — System metrics – cross-platform: CPU, RAM, disks, processes. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/system_core.py#L96)

### `fixos.diagnostics.checks.thumbnails` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/thumbnails.py)

Thumbnails diagnostics module.

- `diagnose_thumbnails()` — Diagnostyka podglądów plików (thumbnails) w system. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/thumbnails.py#L10)

### `fixos.diagnostics.dev_project_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py)

Dev Project Analyzer for FixOS - analyze developer project dependencies.

**`DevProjectAnalyzer`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L69)
: Analyze developer projects for dependency folders that can be cleaned.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `analyze` | `max_depth` | `—` | 9 |
| `get_old_dependencies` | `days` | `—` | 4 |
| `get_large_dependencies` | `min_size_mb` | `—` | 3 |
| `get_summary` | `` | `—` | 11 |
| `get_cleanup_commands` | `` | `—` | 2 |

**`ProjectDependency`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L32)
: Represents a dependency folder that can be cleaned

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `to_dict` | `` | `—` | 3 |

### `fixos.diagnostics.disk_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py)

Disk Analyzer Module for fixOS

**`DiskAnalyzer`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L27)
: Analyzes disk usage and provides cleanup suggestions

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `analyze_disk_usage` | `path` | `—` | 4 |
| `get_large_files` | `path, min_size_mb, max_files` | `—` | 7 |
| `get_cache_dirs` | `path, max_dirs` | `—` | 10 |
| `get_log_dirs` | `path, max_dirs` | `—` | 9 |
| `get_temp_dirs` | `path, max_dirs` | `—` | 9 |
| `suggest_cleanup_actions` | `path` | `—` | 13 |

- `main()` — Test the disk analyzer [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L487)

### `fixos.diagnostics.docker_network_cleanup` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_network_cleanup.py)

Bezpieczne zwalnianie nieużywanych sieci Docker i kontrola puli adresowej.

**`DockerNetworkCleaner`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_network_cleanup.py#L19)
: Usuwa wyłącznie sieci bez endpointów i testuje pulę adresową.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `list_unused` | `min_age_days` | `—` | 40 |
| `probe_address_pool` | `` | `—` | 7 |
| `cleanup` | `` | `—` | 20 |

### `fixos.diagnostics.docker_startup_optimizer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_startup_optimizer.py)

Conservative optimization of stale Docker startup workloads.

**`DockerStartupOptimizer`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_startup_optimizer.py#L31)
: Find and explicitly disable stale repository-backed Docker autostart.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `scan` | `min_inactive_days` | `—` | 31 |
| `optimize` | `container_ids` | `—` | 19 |

### `fixos.diagnostics.flatpak_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py)

Advanced Flatpak analyzer for fixOS

**`FlatpakAnalyzer`** (_FlatpakAnalysisMixin, _FlatpakRecommendationsMixin, _FlatpakExecutionMixin) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L76)
: Advanced analyzer for Flatpak cleanup decisions

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `analyze` | `` | `—` | 10 |

**`FlatpakItemInfo`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L34)
: Detailed info about a Flatpak item (app, runtime, or data)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `to_dict` | `` | `—` | 1 |

**`FlatpakItemType`** (Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L27)

- `analyze_flatpak_for_cleanup()` — Convenience function to run full Flatpak analysis [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L163)

### `fixos.diagnostics.jetbrains_ai` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py)

Exact, window-preserving control of JetBrains AI plugins and Qoder helpers.

**`JetBrainsAiControl`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L29)
: Inspect or explicitly disable AI plugins and stop exact Qoder helpers.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `find_qoder_helpers` | `records` | `—` | 5 |
| `find_config_dirs` | `records, explicit` | `—` | 9 |
| `status` | `` | `—` | 5 |
| `disable_plugins` | `config_dir` | `—` | 7 |
| `stop_qoder_helpers` | `identities` | `—` | 20 |

**`JetBrainsAiSafetyError`** (RuntimeError) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L25)
: Raised when an AI-control target cannot be proven exact and safe.

### `fixos.diagnostics.jetbrains_recovery` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py)

Diagnose and recover a shared JetBrains JVM without closing IDE windows.

**`EdtThreadState`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L83)

**`JetBrainsDiagnosis`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L118)

**`JetBrainsLogSignals`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L98)

**`JetBrainsMetrics`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L61)

**`JetBrainsRecovery`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L315)
: Correlate JetBrains evidence and optionally run a bounded JVM GC.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `find_main_processes` | `records` | `—` | 4 |
| `diagnose` | `pid` | `—` | 37 |
| `recover` | `diagnosis` | `—` | 24 |

**`JetBrainsRecoveryResult`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L133)

**`JetBrainsRecoverySafetyError`** (RuntimeError) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L56)
: Raised when a recovery request cannot be proven safe and applicable.

**`JvmHeapInfo`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L71)

- `analyze_idea_log(text)` — Extract bounded, explainable stall signals from JetBrains log text. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L171)
- `collect_jetbrains_metrics(pid)` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L294)
- `is_main_jetbrains_process(process)` — Return true only for a main IDE process, never a helper/server. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L148)
- `jetbrains_product_marker(process)` — Identify a product only from its launcher, never arbitrary arguments. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L154)
- `parse_edt_thread(text)` — Extract the AWT event-dispatch thread from a ``Thread.print`` result. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L246)
- `parse_heap_info(text)` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L236)
- `read_log_since(path, offset)` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L283)
- `read_log_tail(path)` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L273)

### `fixos.diagnostics.orphaned_workloads` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py)

Evidence-led cleanup for workloads whose development project disappeared.

**`OrphanedWorkloadCleaner`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L45)
: Find and explicitly clean missing-project Docker and process workloads.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `scan` | `` | `—` | 11 |
| `cleanup` | `` | `—` | 13 |

**`OrphanedWorkloadSafetyError`** (RuntimeError) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L41)
: Raised when an exact cleanup target no longer satisfies safety checks.

### `fixos.diagnostics.process_chains` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py)

Evidence-led diagnostics for fresh process chains.

**`FileLockWait`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L74)
: One kernel-reported file-lock dependency.

**`ProcessChainFinding`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L84)
: A fresh process subtree and the evidence associated with it.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `to_dict` | `` | `—` | 5 |

**`ProcessChainInspector`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L261)
: List, analyse and explicitly terminate recent process subtrees.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `snapshot` | `` | `—` | 1 |
| `list_recent` | `` | `—` | 5 |
| `find_suspicious_chains` | `` | `—` | 40 |
| `terminate_chain` | `finding` | `—` | 22 |

**`ProcessChainSafetyError`** (RuntimeError) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L29)
: Raised when a requested process-tree action fails a safety check.

**`ProcessRecord`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L34)
: Stable process metadata captured at one point in time.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `age_seconds` | `now` | `—` | 1 |
| `to_dict` | `` | `—` | 2 |

**`TerminationResult`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L119)
: Result of a dry run or an attempted tree termination.

- `collect_processes()` — Collect a best-effort process snapshot using the existing psutil dependency. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L135)
- `parse_proc_locks(text)` — Parse blocked lock requests from Linux ``/proc/locks`` content. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L172)
- `read_linux_lock_waits(path)` — Read Linux lock dependencies; return no evidence on other/denied systems. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L210)

### `fixos.diagnostics.project_scanner` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py)

Developer Project Scanner for fixOS.

**`ProjectArtifact`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L82)
: A single removable artifact directory found inside a project.

- `discover_project_roots(base, max_depth)` — Find developer project roots under `base` (dirs carrying a known [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L143)
- `find_duplicate_venvs(artifacts)` — Project paths that carry more than one virtualenv-type artifact at [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L235)
- `scan_all(base, threshold_mb, stale_days, max_depth)` — Scan every project under `base` for removable artifacts, largest first. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L221)
- `scan_project_artifacts(project_root, threshold_mb, stale_days)` — Find removable artifacts directly under a single project root. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L174)
- `summarize(artifacts)` — Aggregate stats used for the CLI summary header. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L245)

### `fixos.diagnostics.quick_snapshot` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py)

Fast, local system snapshot used before the full fixOS analysis.

**`CacheRule`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L30)

- `collect_quick_snapshot()` — Collect a bounded, heuristic snapshot without using an LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L784)

### `fixos.diagnostics.service_cleanup` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_cleanup.py)

Service Cleanup for fixOS

**`ServiceCleaner`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_cleanup.py#L29)
: Plans and executes cleanup of service data.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `docker_old_unused_until_hours` | `days` | `—` | 2 |
| `get_docker_old_unused_command` | `days` | `—` | 1 |
| `list_ollama_models` | `` | `—` | 7 |
| `list_running_ollama_models` | `` | `—` | 6 |
| `select_old_ollama_models` | `models, days` | `—` | 7 |
| `cleanup_ollama_old_unused` | `days, dry_run` | `—` | 20 |
| `get_docker_unused_command` | `` | `—` | 1 |
| `cleanup_docker_unused` | `dry_run` | `—` | 16 |
| `cleanup_docker_networks` | `days, dry_run` | `—` | 1 |
| `cleanup_docker_old_unused` | `days, dry_run` | `—` | 15 |
| `build_safe_age_actions` | `selected_services` | `—` | 30 |
| `get_cleanup_plan` | `selected_services` | `—` | 21 |
| `cleanup_service` | `service_type, dry_run, planned_service` | `—` | 17 |
| `get_risk_level` | `service_type, path` | `—` | 21 |
| `is_safe_cleanup` | `service_type, path` | `—` | 1 |
| `get_cleanup_hints` | `service_type, size_gb` | `—` | 10 |
| `get_service_description` | `service_type` | `—` | 1 |
| `get_cleanup_command` | `service_type, path` | `—` | 6 |
| `get_preview_command` | `service_type, path` | `—` | 1 |

### `fixos.diagnostics.service_details` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_details.py)

Service Details Provider for fixOS

**`ServiceDetailsProvider`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_details.py#L19)
: Provides detailed information about service data.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `get_details` | `service_type, path` | `—` | 3 |

### `fixos.diagnostics.service_scanner` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py)

Service Data Scanner for fixOS

**`RiskLevel`** (str, Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L98)
: How risky it is to delete a scanned service's data.

**`ServiceDataInfo`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L116)
: Information about service data.

**`ServiceDataScanner`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L135)
: Scans for large service data directories and allows cleanup.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `scan_all_services` | `` | `—` | 3 |
| `scan_service` | `service_type` | `—` | 8 |
| `measure_service_size_mb` | `service_type, path` | `—` | 5 |
| `get_cleanup_plan` | `selected_services` | `—` | 1 |
| `cleanup_service` | `service_type, dry_run, planned_service` | `—` | 1 |

**`ServiceType`** (Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L26)
: Service types that can be scanned and cleaned.

- `main()` — Test the service data scanner. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L693)

### `fixos.diagnostics.storage_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py)

Storage Analyzer for FixOS - comprehensive disk space analysis.

**`StorageAnalyzer`** (_SystemAnalyzerMixin, _ContainerAnalyzerMixin, _UserAnalyzerMixin) [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L59)
: Comprehensive storage analyzer for Linux systems.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `analyze_full` | `` | `—` | 5 |
| `get_summary` | `` | `—` | 8 |

**`StorageItem`** [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L25)
: Represents a storage item that can be cleaned

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `to_dict` | `` | `—` | 1 |

### `fixos.diagnostics.system_checks` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/system_checks.py)

System diagnostics aggregator.

- `get_full_diagnostics(modules, progress_callback)` — Zbiera diagnostykę z wybranych modułów. [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/system_checks.py#L49)

### `fixos.diagnostics.utils` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/utils.py)

Shared utilities for diagnostic modules.

- `format_size(size_bytes)` — Format bytes to human-readable string (B/KB/MB/GB/TB/PB). [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/utils.py#L6)

### `fixos.endpoint_refresh` [source](https://github.com/semcod/fixos/blob/main/fixos/endpoint_refresh.py)

Safe, DNS-backed observation of configured service endpoints.

**`EndpointStatus`** [source](https://github.com/semcod/fixos/blob/main/fixos/endpoint_refresh.py#L26)
: Permission-safe result of one endpoint observation.

- `refresh_endpoint(name, url)` — Observe one endpoint and retain the last good result on DNS failure. [source](https://github.com/semcod/fixos/blob/main/fixos/endpoint_refresh.py#L100)

### `fixos.features` [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py)

System detection module for fixOS features.

**`SystemDetector`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py#L51)
: Detects system parameters.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `detect` | `` | `—` | 3 |

**`SystemInfo`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py#L16)
: Complete system information snapshot.

### `fixos.features.auditor` [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py)

Feature auditor - compares system state with desired profile.

**`AuditResult`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L15)
: Result of feature audit - what's installed, what's missing.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `to_dict` | `` | `—` | 4 |

**`FeatureAuditor`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L53)
: Compares installed packages with profile requirements.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `audit` | `profile` | `—` | 5 |

### `fixos.features.catalog` [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py)

Package catalog - loads and manages package database from YAML.

**`PackageCatalog`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L57)
: Manages the package database.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `load` | `cls, data_dir` | `—` | 7 |
| `get_package` | `pkg_id` | `—` | 1 |
| `get_packages_by_category` | `category` | `—` | 3 |
| `list_categories` | `` | `—` | 1 |

**`PackageCategory`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L48)
: A category of packages (e.g., core_utils, dev_tools).

**`PackageInfo`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L12)
: Information about a single package.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `get_distro_name` | `distro` | `—` | 2 |
| `is_available_on` | `distro` | `—` | 6 |

### `fixos.features.installer` [source](https://github.com/semcod/fixos/blob/main/fixos/features/installer.py)

Feature installer - safely installs missing packages.

**`FeatureInstaller`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/installer.py#L13)
: Safely installs packages using native package manager or other backends.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `install` | `packages` | `—` | 5 |
| `get_rollback_commands` | `installed_packages` | `—` | 3 |

### `fixos.features.profiles` [source](https://github.com/semcod/fixos/blob/main/fixos/features/profiles.py)

User profile management for fixOS features.

**`UserProfile`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/profiles.py#L14)
: A user profile defining what packages/features they want.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `load` | `cls, profile_name, data_dir` | `—` | 3 |
| `list_available` | `cls, data_dir` | `—` | 4 |
| `resolve_packages` | `catalog, system_info` | `—` | 8 |
| `to_dict` | `` | `—` | 1 |

### `fixos.features.renderer` [source](https://github.com/semcod/fixos/blob/main/fixos/features/renderer.py)

Feature renderer - displays audit results in terminal.

**`FeatureRenderer`** [source](https://github.com/semcod/fixos/blob/main/fixos/features/renderer.py#L17)
: Renders audit results for terminal display.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `render_audit` | `result` | `—` | 8 |
| `render_package_list` | `packages, title` | `—` | 3 |
| `render_system_info` | `system` | `—` | 2 |

### `fixos.interactive.cleanup_planner` [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py)

Interactive Cleanup Planner for fixOS

**`CleanupAction`** [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L32)
: Represents a cleanup action

**`CleanupPlanner`** [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L53)
: Interactive cleanup planning and grouping system

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `group_by_category` | `suggestions` | `—` | 5 |
| `prioritize_actions` | `grouped_actions` | `—` | 11 |
| `create_cleanup_plan` | `suggestions` | `—` | 12 |
| `interactive_selection` | `plan` | `—` | 5 |

**`CleanupType`** (Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L20)

**`Priority`** (Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L13)

- `main()` — Test the cleanup planner [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L437)

### `fixos.llm_shell` [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py)

Interaktywny shell LLM do diagnostyki i naprawy systemu system.

- `execute_command(cmd)` — Wykonuje komendę systemową z potwierdzeniem użytkownika. [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L67)
- `format_time(seconds)` [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L59)
- `run_llm_shell(diagnostics_data, token, model, timeout, verbose, base_url)` — Uruchamia interaktywny shell LLM z przekazanymi danymi diagnostycznymi. [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L175)

### `fixos.orchestrator.executor` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py)

CommandExecutor – bezpieczne wykonywanie komend systemowych.

**`CommandExecutor`** [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L113)
: Bezpieczny executor komend z:

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `is_dangerous` | `command` | `—` | 3 |
| `needs_sudo` | `command` | `—` | 5 |
| `add_sudo` | `command` | `—` | 2 |
| `check_idempotent` | `command` | `—` | 4 |
| `execute_sync` | `command, timeout, add_sudo` | `—` | 10 |
| `execute` | `command, timeout, add_sudo` | `—` | 8 |

**`CommandTimeoutError`** (Exception) [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L24)

**`DangerousCommandError`** (Exception) [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L15)

**`ExecutionResult`** [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L32)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `to_context` | `` | `—` | 1 |

### `fixos.orchestrator.graph` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py)

Problem Graph – model danych dla kaskadowych problemów systemowych.

**`Problem`** [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L19)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `is_actionable` | `` | `—` | 2 |
| `to_summary` | `` | `—` | 1 |

**`ProblemGraph`** [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L46)
: DAG problemów systemowych z topological sort do wyznaczania kolejności napraw.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `add` | `problem` | `—` | 1 |
| `get` | `problem_id` | `—` | 1 |
| `next_actionable` | `` | `—` | 6 |
| `all_done` | `` | `—` | 2 |
| `pending_count` | `` | `—` | 3 |
| `summary` | `` | `—` | 2 |
| `render_tree` | `` | `—` | 7 |

### `fixos.orchestrator.orchestrator` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/orchestrator.py)

FixOrchestrator – główna pętla egzekucji napraw.

**`FixOrchestrator`** [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/orchestrator.py#L91)
: Orkiestrator napraw systemowych.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `load_from_diagnostics` | `diagnostics` | `—` | 5 |
| `load_from_dict` | `problems_data` | `—` | 3 |
| `run_sync` | `confirm_fn, progress_fn` | `—` | 7 |
| `run_async` | `confirm_fn, progress_fn` | `—` | 1 |

### `fixos.orchestrator.rollback` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py)

Rollback system for fixOS — tracks executed operations and allows undoing them.

**`RollbackEntry`** [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L20)
: Single recorded operation with its rollback command.

**`RollbackSession`** [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L33)
: A session of recorded operations that can be rolled back.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `record` | `command, rollback_cmd, stdout` | `—` | 1 |
| `get_rollback_commands` | `` | `—` | 4 |
| `rollback_last` | `n, dry_run` | `—` | 5 |
| `load` | `cls, session_id` | `—` | 3 |
| `list_sessions` | `cls, limit` | `—` | 7 |

### `fixos.orphan_pins` [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py)

Persistent protection for intentionally retained orphan project workloads.

**`OrphanProjectPinError`** (RuntimeError) [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L18)
: Raised when persistent pin state cannot be trusted.

**`OrphanProjectPins`** [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L42)
: Read and atomically update exact Compose working-directory pins.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `list` | `` | `—` | 10 |
| `paths` | `` | `—` | 2 |
| `pin` | `value` | `—` | 4 |
| `unpin` | `value` | `—` | 4 |

- `default_pin_path()` — Return the XDG-compliant per-user pin store path. [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L34)
- `normalize_project_path(value)` — Return a stable absolute path without requiring the path to exist. [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L22)

### `fixos.platform_utils` [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py)

Cross-platform utilities for fixos.

- `cancel_signal_timeout()` — Cancels the timeout signal (POSIX only). [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L246)
- `elevate_cmd(cmd)` — Adds sudo (Linux/Mac) or wraps in PowerShell -Verb RunAs (Windows). [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L93)
- `get_os_info()` — Returns basic OS information. [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L21)
- `get_package_manager()` — Detects the system package manager. [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L187)
- `install_package_cmd(package)` — Returns the install command for the detected package manager. [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L205)
- `is_dangerous(cmd)` — Returns reason string if command is dangerous, None if safe. [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L104)
- `is_interactive_blocker(cmd)` — Returns reason string if command is likely to hang in non-interactive session. [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L127)
- `needs_elevation(cmd)` — Returns True if command likely needs admin/sudo. [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L44)
- `run_command(cmd, timeout, shell)` — Runs a command cross-platform. [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L149)
- `setup_signal_timeout(seconds, handler)` — Sets up a timeout signal. Returns True if supported (POSIX only). [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L232)

### `fixos.plugins.base` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py)

Base classes for fixOS diagnostic plugins.

**`DiagnosticPlugin`** (ABC) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L67)
: Bazowa klasa dla pluginów diagnostycznych fixOS.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `diagnose` | `` | `—` | 1 |
| `can_run` | `` | `—` | 1 |
| `get_metadata` | `` | `—` | 1 |

**`DiagnosticResult`** [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L38)
: Result of a diagnostic plugin run.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `to_dict` | `` | `—` | 2 |

**`Finding`** [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L26)
: Single finding from a diagnostic plugin.

**`Severity`** (Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L16)
: Severity level for diagnostic findings.

### `fixos.plugins.builtin.audio` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py)

Audio diagnostic plugin — ALSA, PipeWire, PulseAudio, SOF firmware.

**`Plugin`** (DiagnosticPlugin) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py#L9)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `diagnose` | `` | `—` | 10 |

### `fixos.plugins.builtin.disk` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py)

Disk diagnostic plugin — usage, partitions, SMART health.

**`Plugin`** (DiagnosticPlugin) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py#L9)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `diagnose` | `` | `—` | 12 |

### `fixos.plugins.builtin.hardware` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py)

Hardware diagnostic plugin — DMI, GPU, touchpad, camera, battery.

**`Plugin`** (DiagnosticPlugin) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py#L9)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `diagnose` | `` | `—` | 12 |

### `fixos.plugins.builtin.resources` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py)

Resources diagnostic plugin — CPU, RAM, processes, autostart.

**`Plugin`** (DiagnosticPlugin) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py#L9)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `diagnose` | `` | `—` | 14 |

### `fixos.plugins.builtin.security` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py)

Security diagnostic plugin — firewall, ports, SELinux, SSH, fail2ban.

**`Plugin`** (DiagnosticPlugin) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py#L9)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `diagnose` | `` | `—` | 8 |

### `fixos.plugins.builtin.thumbnails` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py)

Thumbnails diagnostic plugin — cache, GStreamer, thumbnailers.

**`Plugin`** (DiagnosticPlugin) [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py#L9)

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `diagnose` | `` | `—` | 10 |

### `fixos.plugins.registry` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/registry.py)

Plugin registry with autodiscovery for fixOS diagnostic plugins.

**`PluginRegistry`** [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/registry.py#L21)
: Registry for diagnostic plugins with autodiscovery.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `discover` | `` | `—` | 1 |
| `register` | `plugin` | `—` | 1 |
| `list_plugins` | `runnable_only` | `—` | 5 |
| `get_plugin` | `name` | `—` | 1 |
| `run` | `modules, progress_callback` | `—` | 7 |

### `fixos.profiles` [source](https://github.com/semcod/fixos/blob/main/fixos/profiles/__init__.py)

Diagnostic profiles for fixOS.

**`Profile`** [source](https://github.com/semcod/fixos/blob/main/fixos/profiles/__init__.py#L21)
: Profil diagnostyczny z zestawem modułów i progów.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `load` | `cls, name` | `—` | 3 |
| `list_available` | `cls` | `—` | 4 |
| `to_dict` | `` | `—` | 1 |

### `fixos.providers.llm` [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py)

Ujednolicony klient LLM obsługujący wiele providerów przez OpenAI-compatible API.

**`LLMClient`** [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L38)
: Wrapper nad openai.OpenAI kompatybilny z wieloma providerami.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `chat` | `messages` | `—` | 5 |
| `chat_stream` | `messages` | `—` | 9 |
| `chat_structured` | `messages, response_model` | `—` | 5 |
| `ping` | `` | `—` | 2 |

**`LLMError`** (Exception) [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L22)
: Błąd komunikacji z LLM.

### `fixos.providers.llm_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py)

LLM Analyzer for fixOS - Fallback analysis when heuristics aren't sufficient

**`LLMAnalysis`** [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L12)
: Result of LLM analysis

**`LLMAnalyzer`** [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L21)
: Uses LLM to analyze disk issues when heuristics aren't sufficient

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `analyze_disk_issues` | `disk_data` | `—` | 5 |
| `analyze_failed_action` | `action, error` | `—` | 4 |
| `analyze_complex_pattern` | `pattern_data` | `—` | 5 |
| `enhance_heuristics_with_llm` | `heuristic_suggestions, disk_data` | `—` | 13 |

- `main()` — Test the LLM analyzer [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L351)

### `fixos.providers.schemas` [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py)

Pydantic schemas for structured LLM output.

**`CommandValidation`** (BaseModel) [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L74)
: Wynik walidacji komendy przez LLM.

**`FixSuggestion`** (BaseModel) [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L21)
: Pojedyncza sugestia naprawy od LLM.

**`LLMDiagnosticResponse`** (BaseModel) [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L42)
: Strukturalna odpowiedź LLM na dane diagnostyczne.

**`NLPIntent`** (BaseModel) [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L61)
: Rozpoznana intencja z polecenia NLP.

**`RiskLevel`** (str, Enum) [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L15)

### `fixos.system_checks` [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py)

Moduł zbierający dane diagnostyczne z systemu system.

- `get_cpu_info()` — Metryki CPU. [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L28)
- `get_disk_info()` — Metryki dysków dla wszystkich partycji. [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L56)
- `get_fedora_specific()` — Komendy specyficzne dla system: dnf, journalctl, systemctl. [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L105)
- `get_full_diagnostics()` — Zbiera kompletne dane diagnostyczne systemu system. [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L140)
- `get_memory_info()` — Metryki RAM i SWAP. [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L41)
- `get_network_info()` — Statystyki sieciowe (bez wrażliwych danych - anonimizacja jest osobno). [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L75)
- `get_top_processes(n)` — Lista TOP N procesów według zużycia CPU. [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L91)
- `run_cmd(cmd, timeout)` — Uruchamia komendę shell i zwraca output. Bezpieczny fallback przy błędzie. [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L12)

### `fixos.utils.anonymizer` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py)

Anonimizacja wrażliwych danych systemowych z podglądem dla użytkownika.

**`AnonymizationContext`** [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L72)
: Memory-only alias state. Never include this object in LLM payloads.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `bind` | `category, original, token` | `—` | 3 |
| `numbered_alias` | `category, original` | `—` | 2 |
| `user_alias` | `username` | `—` | 3 |

**`AnonymizationReport`** [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L112)
: Raport anonimizacji – co zostało zmaskowane.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `add` | `category, count` | `—` | 1 |
| `summary` | `` | `—` | 3 |

**`ResolutionError`** (ValueError) [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L63)
: Raised when an anonymized alias cannot be resolved safely.

- `anonymize(data_str, context)` — Anonimizuje wrażliwe dane. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L272)
- `deanonymize(text, context, allowed_aliases)` — Resolve aliases locally while preserving the legacy primary tokens. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L360)
- `display_anonymized_preview(data_str, report, max_lines)` — Wyświetla użytkownikowi zanonimizowane dane przed wysłaniem do LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L373)

### `fixos.utils.terminal` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py)

Terminal rendering utilities – shared between hitl, orchestrator, cli.

- `colorize(line)` — Return line unchanged – rich handles markup in render_md(). [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L60)
- `print_cmd_block(cmd, comment, dry_run)` — Print a framed command preview panel. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L188)
- `print_problem_header(problem_id, description, severity, status, attempts, max_attempts)` — Print a colored problem header panel. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L255)
- `print_stderr_box(stderr, max_lines)` — Print stderr in a rich Panel. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L228)
- `print_stdout_box(stdout, max_lines)` — Print stdout in a rich Panel. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L223)
- `render_md(text)` — Print LLM markdown reply to terminal via rich. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L101)
- `render_tree_colored(nodes, execution_order)` — Render a ProblemGraph as a rich-markup string. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L283)

### `fixos.utils.timeout` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py)

Shared SessionTimeout exception and timeout handler for fixOS.

**`SessionTimeout`** (Exception) [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L10)
: Wyjątek rzucany po przekroczeniu limitu czasu sesji.

- `timeout_handler(signum, frame)` — Signal handler dla SIGALRM — rzuca SessionTimeout. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L16)

### `fixos.utils.web_search` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py)

Zewnętrzne źródła wiedzy – fallback gdy LLM nie zna rozwiązania.

**`SearchResult`** [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L18)

- `format_results_for_llm(results)` — Formatuje wyniki wyszukiwania do wklejenia w prompt LLM. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L267)
- `search_all(query, serpapi_key, max_per_source)` — Przeszukuje wszystkie dostępne źródła wiedzy. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L223)
- `search_arch_wiki(query, max_results)` — Arch Wiki – doskonałe źródło dla problemów Linux (nie tylko Arch). [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L90)
- `search_ask_fedora(query, max_results)` — Szuka w Linux forums przez Discourse API. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L66)
- `search_ddg(query, max_results)` — DuckDuckGo Instant Answer API (bez klucza, ograniczone). [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L187)
- `search_fedora_bugzilla(query, max_results)` — Szuka w Linux Bugzilla przez REST API. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L38)
- `search_github_issues(query, max_results)` — GitHub Issues – linuxhardware, ALSA, PipeWire, PulseAudio repos. [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L120)
- `search_serpapi(query, api_key, max_results)` — SerpAPI – Google/Bing search (wymaga klucza API). [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L157)

### `fixos.watch` [source](https://github.com/semcod/fixos/blob/main/fixos/watch.py)

Watch mode daemon for fixOS — periodic diagnostics with desktop notifications.

**`WatchDaemon`** [source](https://github.com/semcod/fixos/blob/main/fixos/watch.py#L22)
: Daemon wykonujący cykliczną diagnostykę z powiadomieniami.

| Method | Args | Returns | CC |
|--------|------|---------|----|
| `run` | `` | `—` | 12 |
| `stop` | `` | `—` | 1 |

## scripts

### `scripts.pyqual-calibrate` [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py)

Auto-kalibracja progów metryk dla pyqual.

- `calculate_new_threshold(actual_value, current_threshold, margin_percent, is_upper_limit)` — Wylicza nowy próg z marginesem. [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L81)
- `calibrate(workdir, margin, dry_run, force, provided_metrics)` — Główna funkcja kalibracji. [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L128)
- `extract_current_metrics(content)` — Wyciąga aktualne progi z YAML. [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L109)
- `main()` [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L235)
- `parse_pyqual_yaml(config_path)` — Odczytuje zawartość pyqual.yaml. [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L56)
- `read_last_metrics_from_db(workdir)` — Czyta ostatnie metryki z pipeline.db pyqual. [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L25)
- `update_metric(content, metric_name, new_value)` — Aktualizuje wartość metryki w YAML. [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L61)

### `scripts.runtime` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh)

- `approvalScopeDigest()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L345)
- `canonical()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L70)
- `diagnostic()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L99)
- `exactStringSet()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L340)
- `expectedVerdict()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L357)
- `findNumericScore()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L293)
- `git()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L329)
- `globToRegExp()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L307)
- `isDigest()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L162)
- `isObject()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L154)
- `isSha()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L158)
- `markdownReport()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L751)
- `parseOptions()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L44)
- `pathAllowed()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L325)
- `readJson()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L90)
- `readText()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L82)
- `sha256Bytes()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L74)
- `sha256File()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L78)
- `sortDeep()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L58)
- `usage()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L32)
- `validateEvaluation()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L379)
- `validateMinimumShape()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L166)
- `validatePolicyText()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L114)
- `writeResult()` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L772)
