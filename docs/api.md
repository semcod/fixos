# fixos — API Reference

> 188 modules | 929 functions | 109 classes

## Contents

- [Core](#core) (1 modules)
- [docker](#docker) (3 modules)
- [docs](#docs) (1 modules)
- [fixos](#fixos) (100 modules)
- [scripts](#scripts) (2 modules)

## Core

### `fixos` [source](https://github.com/semcod/fixos/blob/main/fixos/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `AgentReport` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L90) |
| `AutonomousSession` | 1 | Self-directed autonomous diagnostic and repair session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L113) |
| `FixAction` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L81) |
| `HITLSession` | 2 | Interactive Human-in-the-Loop diagnostic and repair session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L36) |
| `CmdResult` | 1 | Result of executed command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L19) |
| `DiagnosticChoice` | 0 | A diagnosed problem that is selectable but has no executable plan yet. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L76) |
| `RemediationAction` | 2 | One policy-labelled strategy for resolving a diagnostic finding. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L43) |
| `OutputFormat` | 0 | Supported output formats. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L24) |
| `OutputFormatter` | 9 | Centralized output formatter for fixOS CLI commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L43) |
| `NaturalLanguageGroup` | 1 | Click group that intelligently handles typos and routes natural language commands to 'ask'. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L107) |
| `FixOsConfig` | 3 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L179) |
| `DevProjectAnalyzer` | 5 | Analyze developer projects for dependency folders that can be cleaned. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L69) |
| `ProjectDependency` | 1 | Represents a dependency folder that can be cleaned | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L32) |
| `DiskAnalyzer` | 6 | Analyzes disk usage and provides cleanup suggestions | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L27) |
| `DockerNetworkCleaner` | 3 | Usuwa wyłącznie sieci bez endpointów i testuje pulę adresową. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_network_cleanup.py#L19) |
| `DockerStartupOptimizer` | 2 | Find and explicitly disable stale repository-backed Docker autostart. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_startup_optimizer.py#L31) |
| `FlatpakAnalyzer` | 1 | Advanced analyzer for Flatpak cleanup decisions | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L76) |
| `FlatpakItemInfo` | 1 | Detailed info about a Flatpak item (app, runtime, or data) | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L34) |
| `FlatpakItemType` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L27) |
| `JetBrainsAiControl` | 5 | Inspect or explicitly disable AI plugins and stop exact Qoder helpers. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L29) |
| `JetBrainsAiSafetyError` | 0 | Raised when an AI-control target cannot be proven exact and safe. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L25) |
| `EdtThreadState` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L83) |
| `JetBrainsDiagnosis` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L118) |
| `JetBrainsLogSignals` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L98) |
| `JetBrainsMetrics` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L61) |
| `JetBrainsRecovery` | 3 | Correlate JetBrains evidence and optionally run a bounded JVM GC. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L315) |
| `JetBrainsRecoveryResult` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L133) |
| `JetBrainsRecoverySafetyError` | 0 | Raised when a recovery request cannot be proven safe and applicable. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L56) |
| `JvmHeapInfo` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L71) |
| `OrphanedWorkloadCleaner` | 2 | Find and explicitly clean missing-project Docker and process workloads. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L45) |
| `OrphanedWorkloadSafetyError` | 0 | Raised when an exact cleanup target no longer satisfies safety checks. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L41) |
| `FileLockWait` | 0 | One kernel-reported file-lock dependency. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L74) |
| `ProcessChainFinding` | 2 | A fresh process subtree and the evidence associated with it. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L84) |
| `ProcessChainInspector` | 4 | List, analyse and explicitly terminate recent process subtrees. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L261) |
| `ProcessChainSafetyError` | 0 | Raised when a requested process-tree action fails a safety check. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L29) |
| `ProcessRecord` | 3 | Stable process metadata captured at one point in time. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L34) |
| `TerminationResult` | 1 | Result of a dry run or an attempted tree termination. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L119) |
| `ProjectArtifact` | 0 | A single removable artifact directory found inside a project. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L82) |
| `CacheRule` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L30) |
| `ServiceCleaner` | 19 | Plans and executes cleanup of service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_cleanup.py#L29) |
| `ServiceDetailsProvider` | 1 | Provides detailed information about service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_details.py#L19) |
| `RiskLevel` | 0 | How risky it is to delete a scanned service's data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L98) |
| `ServiceDataInfo` | 0 | Information about service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L116) |
| `ServiceDataScanner` | 5 | Scans for large service data directories and allows cleanup. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L135) |
| `ServiceType` | 0 | Service types that can be scanned and cleaned. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L26) |
| `StorageAnalyzer` | 2 | Comprehensive storage analyzer for Linux systems. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L59) |
| `StorageItem` | 1 | Represents a storage item that can be cleaned | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L25) |
| `SystemDetector` | 1 | Detects system parameters. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py#L51) |
| `SystemInfo` | 0 | Complete system information snapshot. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py#L16) |
| `AuditResult` | 3 | Result of feature audit - what's installed, what's missing. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L15) |
| `FeatureAuditor` | 1 | Compares installed packages with profile requirements. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L53) |
| `PackageCatalog` | 4 | Manages the package database. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L57) |
| `PackageCategory` | 0 | A category of packages (e.g., core_utils, dev_tools). | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L48) |
| `PackageInfo` | 2 | Information about a single package. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L12) |
| `FeatureInstaller` | 2 | Safely installs packages using native package manager or other backends. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/installer.py#L13) |
| `UserProfile` | 4 | A user profile defining what packages/features they want. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/profiles.py#L14) |
| `FeatureRenderer` | 3 | Renders audit results for terminal display. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/renderer.py#L17) |
| `CleanupAction` | 0 | Represents a cleanup action | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L32) |
| `CleanupPlanner` | 4 | Interactive cleanup planning and grouping system | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L53) |
| `CleanupType` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L20) |
| `Priority` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L13) |
| `CommandExecutor` | 6 | Bezpieczny executor komend z: | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L113) |
| `CommandTimeoutError` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L24) |
| `DangerousCommandError` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L15) |
| `ExecutionResult` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L32) |
| `Problem` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L19) |
| `ProblemGraph` | 7 | DAG problemów systemowych z topological sort do wyznaczania kolejności napraw. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L46) |
| `FixOrchestrator` | 4 | Orkiestrator napraw systemowych. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/orchestrator.py#L91) |
| `RollbackEntry` | 0 | Single recorded operation with its rollback command. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L20) |
| `RollbackSession` | 5 | A session of recorded operations that can be rolled back. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L33) |
| `OrphanProjectPinError` | 0 | Raised when persistent pin state cannot be trusted. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L18) |
| `OrphanProjectPins` | 4 | Read and atomically update exact Compose working-directory pins. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L42) |
| `DiagnosticPlugin` | 3 | Bazowa klasa dla pluginów diagnostycznych fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L67) |
| `DiagnosticResult` | 1 | Result of a diagnostic plugin run. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L38) |
| `Finding` | 0 | Single finding from a diagnostic plugin. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L26) |
| `Severity` | 0 | Severity level for diagnostic findings. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L16) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py#L9) |
| `PluginRegistry` | 6 | Registry for diagnostic plugins with autodiscovery. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/registry.py#L21) |
| `Profile` | 3 | Profil diagnostyczny z zestawem modułów i progów. | [source](https://github.com/semcod/fixos/blob/main/fixos/profiles/__init__.py#L21) |
| `LLMClient` | 6 | Wrapper nad openai.OpenAI kompatybilny z wieloma providerami. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L38) |
| `LLMError` | 0 | Błąd komunikacji z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L22) |
| `LLMAnalysis` | 0 | Result of LLM analysis | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L12) |
| `LLMAnalyzer` | 4 | Uses LLM to analyze disk issues when heuristics aren't sufficient | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L21) |
| `CommandValidation` | 0 | Wynik walidacji komendy przez LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L74) |
| `FixSuggestion` | 0 | Pojedyncza sugestia naprawy od LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L21) |
| `LLMDiagnosticResponse` | 0 | Strukturalna odpowiedź LLM na dane diagnostyczne. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L42) |
| `NLPIntent` | 0 | Rozpoznana intencja z polecenia NLP. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L61) |
| `RiskLevel` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L15) |
| `AnonymizationContext` | 3 | Memory-only alias state. Never include this object in LLM payloads. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L72) |
| `AnonymizationReport` | 2 | Raport anonimizacji – co zostało zmaskowane. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L112) |
| `ResolutionError` | 0 | Raised when an anonymized alias cannot be resolved safely. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L63) |
| `SessionTimeout` | 0 | Wyjątek rzucany po przekroczeniu limitu czasu sesji. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L10) |
| `SearchResult` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L18) |
| `WatchDaemon` | 2 | Daemon wykonujący cykliczną diagnostykę z powiadomieniami. | [source](https://github.com/semcod/fixos/blob/main/fixos/watch.py#L22) |

**`HITLSession` methods:**

- `remaining()` — Get remaining session time in seconds.
- `run()` — Run the HITL session.

**`OutputFormatter` methods:**

- `from_flags(cls, yaml_output, json_output)` — Create formatter from CLI flag values. YAML takes precedence over JSON.
- `status(msg, fg, bold)` — Print a status/progress message. Goes to stderr in machine mode.
- `progress(name, desc)` — Print a progress line for diagnostic module collection.
- `banner(text)` — Print banner. Suppressed in machine mode.
- `emit(data, stream)` — Emit structured data to stdout in the configured format.
- `format_data(data)` — Format data dict/list as string in the configured format.
- `format_diagnostics(data)` — Format full diagnostic result with metadata envelope.
- `format_scan_result(data)` — Format scan results with optional disk analysis.

**`FixOsConfig` methods:**

- `load(cls)` — Tworzy konfigurację z połączonych źródeł.
- `validate()` — Zwraca listę błędów walidacji (pusta = OK).
- `summary()` — Krótkie podsumowanie konfiguracji (bez klucza API).

**`DevProjectAnalyzer` methods:**

- `analyze(max_depth)` — Scan home directory for dependency folders.
- `get_old_dependencies(days)` — Get dependencies not modified in X days
- `get_large_dependencies(min_size_mb)` — Get dependencies larger than X MB
- `get_summary()` — Get human-readable summary
- `get_cleanup_commands()` — Get cleanup commands for each dependency

**`DiskAnalyzer` methods:**

- `analyze_disk_usage(path)` — Comprehensive disk usage analysis
- `get_large_files(path, min_size_mb, max_files)` — Find large files
- `get_cache_dirs(path, max_dirs)` — Find cache directories
- `get_log_dirs(path, max_dirs)` — Find log directories
- `get_temp_dirs(path, max_dirs)` — Find temporary directories
- `suggest_cleanup_actions(path)` — Generate cleanup suggestions using heuristics

**`DockerNetworkCleaner` methods:**

- `list_unused(min_age_days)` — Zwróć niestandardowe sieci bez endpointów.
- `probe_address_pool()` — Utwórz i usuń tymczasową sieć, potwierdzając dostępność puli.
- `cleanup()` — Usuń dokładnie wykryte sieci i opcjonalnie sprawdź pulę adresową.

**`DockerStartupOptimizer` methods:**

- `scan(min_inactive_days)` — Return evidence and stale candidates without changing Docker state.
- `optimize(container_ids)` — Disable exact stale candidates and optionally stop them.

**`JetBrainsAiControl` methods:**

- `find_qoder_helpers(records)`
- `find_config_dirs(records, explicit)`
- `status()`
- `disable_plugins(config_dir)`
- `stop_qoder_helpers(identities)`

**`JetBrainsRecovery` methods:**

- `find_main_processes(records)`
- `diagnose(pid)`
- `recover(diagnosis)` — Optionally run ``GC.run`` and verify evidence without closing the IDE.

**`OrphanedWorkloadCleaner` methods:**

- `scan()` — Return exact orphan evidence without changing Docker or processes.
- `cleanup()` — Revalidate and apply only exact selected orphan candidates.

**`ProcessChainInspector` methods:**

- `snapshot()`
- `list_recent()` — Return newest processes first, without classifying them as blockers.
- `find_suspicious_chains()` — Reconstruct fresh trees and attach explainable blocking evidence.
- `terminate_chain(finding)` — Terminate one selected tree after identity and ancestry checks.

**`ProcessRecord` methods:**

- `age_seconds(now)`
- `to_dict()`

**`ServiceCleaner` methods:**

- `docker_old_unused_until_hours(days)` — Convert a positive day count to Docker ``until=<Nh>`` hours.
- `get_docker_old_unused_command(days)` — Bounded prune: unused images (and old build cache) older than N days.
- `list_ollama_models()` — Return installed Ollama models with name/size/modified_at (UTC).
- `list_running_ollama_models()` — Names of models currently loaded in memory (must not be deleted).
- `select_old_ollama_models(models, days)` — Filter models whose modified_at is older than N days; skip running ones.
- `cleanup_ollama_old_unused(days, dry_run)` — Remove Ollama models not modified for more than N days (skip running).
- `get_docker_unused_command()` — Prune all unused images and rebuildable build cache (no age filter).
- `cleanup_docker_unused(dry_run)` — Remove unused images/cache and optionally orphaned networks.
- `cleanup_docker_networks(days, dry_run)` — Remove unused custom networks and verify Docker address-pool allocation.
- `cleanup_docker_old_unused(days, dry_run)` — Remove old images/cache and optionally orphaned networks.
- `build_safe_age_actions(selected_services)` — Bounded age-based cleanups treated as safe (option [1] in interactive cleanup).
- `get_cleanup_plan(selected_services)` — Generate cleanup plan for services, split into 3 risk tiers.
- `cleanup_service(service_type, dry_run, planned_service)` — Execute cleanup for a specific service or exact planned entry.
- `get_risk_level(service_type, path)` — Classify cleanup risk for a service path.
- `is_safe_cleanup(service_type, path)` — Backward-compatible bool view of get_risk_level() == SAFE.
- `get_cleanup_hints(service_type, size_gb)` — Get helpful hints for cleaning services that require manual review.
- `get_service_description(service_type)` — Get description for service type.
- `get_cleanup_command(service_type, path)` — Get a bounded cleanup command for a scanned service path.
- `get_preview_command(service_type, path)` — Get preview command for service.

**`ServiceDataScanner` methods:**

- `scan_all_services()` — Scan all known services for data above threshold.
- `scan_service(service_type)` — Scan specific service type for data.
- `measure_service_size_mb(service_type, path)` — Measure a service with the same source before and after cleanup.
- `get_cleanup_plan(selected_services)` — Generate cleanup plan for services.
- `cleanup_service(service_type, dry_run, planned_service)` — Execute cleanup for a specific service.

**`StorageAnalyzer` methods:**

- `analyze_full()` — Run full system storage analysis
- `get_summary()` — Get human-readable summary

**`PackageCatalog` methods:**

- `load(cls, data_dir)` — Load package catalog from YAML files.
- `get_package(pkg_id)` — Get package by ID.
- `get_packages_by_category(category)` — Get all packages in a category.
- `list_categories()` — List all category IDs.

**`PackageInfo` methods:**

- `get_distro_name(distro)` — Get package name for specific distro.
- `is_available_on(distro)` — Check if package is available on given distro.

**`FeatureInstaller` methods:**

- `install(packages)` — Install a list of packages.
- `get_rollback_commands(installed_packages)` — Generate rollback commands for installed packages.

**`UserProfile` methods:**

- `load(cls, profile_name, data_dir)` — Load a profile from YAML file.
- `list_available(cls, data_dir)` — List available profile names.
- `resolve_packages(catalog, system_info)` — Resolve all packages for this profile based on system.
- `to_dict()` — Convert to dictionary.

**`FeatureRenderer` methods:**

- `render_audit(result)` — Render complete audit results.
- `render_package_list(packages, title)` — Render a list of packages.
- `render_system_info(system)` — Render system information.

**`CleanupPlanner` methods:**

- `group_by_category(suggestions)` — Group cleanup suggestions by category
- `prioritize_actions(grouped_actions)` — Create prioritized list of all actions
- `create_cleanup_plan(suggestions)` — Create comprehensive cleanup plan
- `interactive_selection(plan)` — Interactive selection process (simulated for now)

**`CommandExecutor` methods:**

- `is_dangerous(command)` — Sprawdza czy komenda jest potencjalnie destruktywna.
- `needs_sudo(command)`
- `add_sudo(command)`
- `check_idempotent(command)` — Zwraca komendę sprawdzającą stan (jeśli znana), None jeśli nie dotyczy.
- `execute_sync(command, timeout, add_sudo, check_idempotent)` — Synchroniczne wykonanie komendy.
- `execute(command, timeout, add_sudo)` — Asynchroniczne wykonanie komendy.

**`Problem` methods:**

- `is_actionable()`
- `to_summary()`

**`ProblemGraph` methods:**

- `add(problem)`
- `get(problem_id)`
- `next_actionable()` — Zwraca pierwszy problem bez nierozwiązanych zależności.
- `all_done()`
- `pending_count()`
- `summary()`
- `render_tree()` — Renderuje drzewo problemów jako tekst.

**`FixOrchestrator` methods:**

- `load_from_diagnostics(diagnostics)` — Parsuje dane diagnostyczne przez LLM i buduje graf problemów.
- `load_from_dict(problems_data)` — Ładuje problemy bezpośrednio z listy dict (bez LLM).
- `run_sync(confirm_fn, progress_fn)` — Synchroniczna pętla napraw (dla trybu HITL).
- `run_async(confirm_fn, progress_fn)` — Asynchroniczna wersja run_sync.

**`RollbackSession` methods:**

- `record(command, rollback_cmd, stdout, stderr, ...)` — Zapisz wykonaną operację.
- `get_rollback_commands()` — Zwraca listę (komenda, rollback) w odwróconej kolejności.
- `rollback_last(n, dry_run)` — Cofnij ostatnich n operacji.
- `load(cls, session_id)` — Załaduj sesję z pliku.
- `list_sessions(cls, limit)` — Lista ostatnich sesji rollback.

**`OrphanProjectPins` methods:**

- `list()` — Load validated records, failing closed if the state is malformed.
- `paths()` — Return exact normalized paths used by the scanner.
- `pin(value)` — Persist one exact path and report whether state changed.
- `unpin(value)` — Remove one exact path, leaving unrelated pins untouched.

**`DiagnosticPlugin` methods:**

- `diagnose()` — Wykonaj diagnostykę i zwróć wynik.
- `can_run()` — Czy plugin może działać na aktualnej platformie?
- `get_metadata()`

**`PluginRegistry` methods:**

- `discover()` — Odkrywanie pluginów przez builtin + entry_points.
- `register(plugin)` — Ręczna rejestracja pluginu.
- `list_plugins(runnable_only)` — Lista zarejestrowanych pluginów.
- `get_plugin(name)` — Pobierz plugin po nazwie.
- `run(modules, progress_callback)` — Uruchom diagnostykę dla wybranych (lub wszystkich) modułów.

**`Profile` methods:**

- `load(cls, name)` — Załaduj profil — najpierw user, potem builtin.
- `list_available(cls)` — Lista dostępnych profili (builtin + user).
- `to_dict()`

**`LLMClient` methods:**

- `chat(messages)` — Wysyła wiadomości do LLM i zwraca odpowiedź jako string.
- `chat_stream(messages)` — Generator streamujący tokeny odpowiedzi.
- `chat_structured(messages, response_model)` — Wywołanie LLM z wymuszonym schematem JSON (Pydantic model).
- `ping()` — Sprawdza czy API odpowiada (krótki test).

**`LLMAnalyzer` methods:**

- `analyze_disk_issues(disk_data)` — Use LLM to analyze disk issues when heuristics are insufficient
- `analyze_failed_action(action, error)` — Analyze failed cleanup action and suggest alternatives
- `analyze_complex_pattern(pattern_data)` — Analyze complex disk usage patterns that heuristics can't categorize
- `enhance_heuristics_with_llm(heuristic_suggestions, disk_data)` — Enhance heuristic suggestions with LLM insights

**`AnonymizationContext` methods:**

- `bind(category, original, token)`
- `numbered_alias(category, original)`
- `user_alias(username)`

**`AnonymizationReport` methods:**

- `add(category, count)`
- `summary()`

**`WatchDaemon` methods:**

- `run()` — Główna pętla monitorowania.
- `stop()` — Zatrzymaj daemon.

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `run_autonomous_session` | `run_autonomous_session(diagnostics, config, show_data, max_fixes)` | 1 | Uruchamia autonomiczny tryb agenta. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous.py#L31) |
| `run_autonomous_session` | `run_autonomous_session(diagnostics, config, show_data, max_fixes)` | 1 | Run autonomous session (backward compatible wrapper). | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L460) |
| `get_remaining_time` | `get_remaining_time(session)` | 2 | Calculate remaining session time in seconds. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/__init__.py#L22) |
| `run_hitl_session` | `run_hitl_session(diagnostics, config, show_data)` | 1 | Run interactive HITL session with full transparency. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl.py#L24) |
| `run_hitl_session` | `run_hitl_session(diagnostics, config, show_data)` | 1 | Run interactive HITL session (backward compatible wrapper). | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L359) |
| `extract_diagnostic_choices` | `extract_diagnostic_choices(reply)` | 12 ⚠️ | Extract non-executable choices from numbered diagnosis headings. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L628) |
| `extract_fixes` | `extract_fixes(reply)` | 4 | Extract (command, comment) pairs from LLM reply. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L380) |
| `extract_remediation_actions` | `extract_remediation_actions(reply)` | 4 | Parse a closed remediation plan, falling back to legacy command syntax. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L603) |
| `extract_search_topic` | `extract_search_topic(llm_reply)` | 3 | Extract search keywords from LLM reply. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L710) |
| `select_recommended_actions` | `select_recommended_actions(actions)` | 4 | Return at most one recommended strategy for each finding. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L697) |
| `strip_remediation_plan` | `strip_remediation_plan(reply)` | 1 | Hide the machine plan block from the human-readable diagnosis. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L617) |
| `transform_remediation_commands` | `transform_remediation_commands(action, transform)` | 4 | Apply anonymization reversal to executable fields only. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L674) |
| `handle_cleanup_intent` | `handle_cleanup_intent(messages)` | 1 | Ask for a cleanup plan without authorizing or executing any command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L111) |
| `handle_describe_problem` | `handle_describe_problem(messages, ask_fn)` | 2 | Handle [D] Describe own problem command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L86) |
| `handle_direct_command` | `handle_direct_command(user_in, messages, executed, run_cmd_fn)` | 1 | Handle [!cmd] Direct command execution. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L408) |
| `handle_execute_all` | `handle_execute_all(fixes, messages, executed, run_cmd_fn)` | 17 ⚠️ | Handle [A] Execute all commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L283) |
| `handle_fix_by_number` | `handle_fix_by_number(user_in, fixes, messages, executed, ...)` | 9 | Handle [N] Execute specific fix by number. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L344) |
| `handle_free_text` | `handle_free_text(user_in, messages)` | 1 | Handle free text input → send to LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L443) |
| `handle_quit` | `handle_quit()` | 1 | Handle [Q] Quit command. Returns False to exit loop. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L72) |
| `handle_search` | `handle_search(user_in, messages, serpapi_key)` | 2 | Handle [search <q>] Web search command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L425) |
| `handle_skip_all` | `handle_skip_all(messages)` | 1 | Handle [S] Skip all command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L78) |
| `is_cleanup_intent` | `is_cleanup_intent(user_in)` | 2 | Recognize a bounded single-word spelling variant of ``cleanup``. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L103) |
| `parse_user_input` | `parse_user_input(user_in, fixes, messages, executed, ...)` | 10 | Parse user input and execute appropriate handler. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L515) |
| `run_single_command` | `run_single_command(cmd, comment)` | 5 | Run a command with full transparency and safety checks. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L449) |
| `ask_execute_prompt` | `ask_execute_prompt()` | 1 | Ask user if they want to execute a command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L375) |
| `ask_low_confidence_search` | `ask_low_confidence_search()` | 1 | Ask user if they want to search when LLM is uncertain. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L381) |
| `ask_send_data` | `ask_send_data()` | 1 | Ask user if they want to send data to LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L389) |
| `ask_user_problem` | `ask_user_problem()` | 2 | Interactively asks the user to describe their problem. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L222) |
| `clear_thinking` | `clear_thinking()` | 1 | Clear the 'Analyzing...' indicator. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L300) |
| `fmt_time` | `fmt_time(s)` | 1 | Format seconds as HH:MM:SS. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L81) |
| `get_user_input` | `get_user_input(remaining)` | 2 | Get user input with prompt. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L396) |
| `print_action_menu` | `print_action_menu(fixes, remaining, total_tokens, completed_count)` | 19 ⚠️ | Print the refreshed interactive menu of remaining choices. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L86) |
| `print_blocked_command` | `print_blocked_command(cmd, reason)` | 1 | Print blocked dangerous command warning. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L317) |
| `print_cmd_preview` | `print_cmd_preview(cmd, comment)` | 1 | Shows command in a clear block before execution. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L254) |
| `print_cmd_result` | `print_cmd_result(result)` | 8 | Shows command result with colorized markdown. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L259) |
| `print_executing_all` | `print_executing_all(count)` | 1 | Print executing all recommended command sets message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L338) |
| `print_invalid_option` | `print_invalid_option(user_in, max_option)` | 1 | Print invalid option message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L358) |
| `print_llm_error` | `print_llm_error(e)` | 1 | Print LLM error message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L312) |
| `print_llm_reply` | `print_llm_reply(reply)` | 1 | Render LLM reply with markdown formatting. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L305) |
| `print_no_commands` | `print_no_commands()` | 1 | Print no commands available message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L345) |
| `print_no_results` | `print_no_results()` | 1 | Print no search results message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L365) |
| `print_searching` | `print_searching()` | 1 | Print searching message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L370) |
| `print_select_one` | `print_select_one()` | 1 | Explain that diagnosis-only choices must be focused individually. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L350) |
| `print_session_ended` | `print_session_ended()` | 1 | Print session ended message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L328) |
| `print_session_header` | `print_session_header(os_info, pkg_manager, model, timeout, ...)` | 1 | Print session header with system info. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L64) |
| `print_session_interrupted` | `print_session_interrupted()` | 1 | Print session interrupted message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L333) |
| `print_session_summary` | `print_session_summary(messages_count, elapsed, total_tokens, executed)` | 3 | Print session summary. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L284) |
| `print_thinking` | `print_thinking()` | 1 | Print 'Analyzing...' indicator. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L295) |
| `print_timeout` | `print_timeout()` | 1 | Print session timeout message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L323) |
| `suspend_timeout` | `suspend_timeout()` | 4 | Context manager to temporarily suspend session timeout during user input. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L39) |
| `anonymize` | `anonymize(data_str)` | 1 | Keep the original string-only return shape used by ``llm_shell``. | [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py#L16) |
| `get_sensitive_values` | `get_sensitive_values()` | 1 | Return legacy key names without maintaining a second privacy policy. | [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py#L6) |
| `ask` | `ask(prompt, dry_run)` | 1 | Wykonaj polecenie w języku naturalnym. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/ask_cmd.py#L13) |
| `cleanup_services` | `cleanup_services(threshold, services, json_output, cleanup, ...)` | 56 ⚠️ | Skanuje i czyści dane usług przekraczające próg. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/cleanup_cmd.py#L1384) |
| `config` | `config()` | 1 | Zarządzanie konfiguracją fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L41) |
| `config_init` | `config_init(force)` | 3 | Zainicjalizuj plik konfiguracyjny .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L77) |
| `config_model` | `config_model(provider)` | 8 | Interaktywnie wybierz model LLM z listy. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L133) |
| `config_provider` | `config_provider()` | 6 | Interaktywnie wybierz providera LLM z listy. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L262) |
| `config_set` | `config_set(key, value)` | 2 | Ustaw wartość konfiguracyjną w .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L112) |
| `config_show` | `config_show()` | 4 | Pokaż aktualną konfigurację. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L47) |
| `features` | `features()` | 1 | Zarządzanie pakietami komfortu systemu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L20) |
| `features_audit` | `features_audit(profile, json_output)` | 4 | Sprawdź brakujące pakiety dla profilu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L30) |
| `features_install` | `features_install(profile, dry_run, yes, category)` | 7 | Zainstaluj brakujące pakiety dla profilu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L91) |
| `features_profiles` | `features_profiles()` | 3 | Lista dostępnych profili. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L122) |
| `features_system` | `features_system()` | 1 | Pokaż wykryty system. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L143) |
| `execute_cleanup_actions` | `execute_cleanup_actions(actions, cfg, llm_fallback)` | 6 | Execute cleanup actions with safety checks | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L349) |
| `fix` | `fix(provider, token, model, no_banner, ...)` | 13 ⚠️ | Przeprowadza pełną diagnostykę i uruchamia sesję naprawczą z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L130) |
| `handle_disk_cleanup_mode` | `handle_disk_cleanup_mode(disk_analysis, cfg, dry_run, interactive, ...)` | 13 ⚠️ | Handle disk cleanup mode with interactive planning | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L245) |
| `try_llm_fallback_for_failures` | `try_llm_fallback_for_failures(failed_actions, cfg)` | 3 | Try to fix failed actions using LLM | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L390) |
| `history` | `history(limit, json_output)` | 5 | Historia napraw fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/history_cmd.py#L11) |
| `ai_control` | `ai_control(config_dir, disable_plugins, stop_qoder, apply, ...)` | 23 ⚠️ | Diagnozuj i ogranicz dodatki AI bez zamykania okien IDE. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L283) |
| `doctor` | `doctor(pid, minutes, no_thread_dump, json_output, ...)` | 25 ⚠️ | Zbierz metryki JVM, stan EDT i sygnały z idea.log. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L162) |
| `jetbrains` | `jetbrains()` | 1 | Diagnozuj współdzieloną JVM JetBrains bez zamykania okien. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L137) |
| `cli` | `cli(ctx, dry_run, interactive_mode, version)` | 7 | fixos – AI-powered diagnostyka i naprawa Linux, Windows, macOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L28) |
| `main` | `main()` | 1 | Entry point for fixOS CLI. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L239) |
| `orchestrate` | `orchestrate(provider, token, model, no_banner, ...)` | 13 ⚠️ | Zaawansowana orkiestracja napraw z grafem problemów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/orchestrate_cmd.py#L30) |
| `profile` | `profile()` | 1 | Zarządzanie profilami diagnostycznymi. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L9) |
| `profile_list` | `profile_list()` | 4 | Pokaż dostępne profile diagnostyczne. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L15) |
| `profile_show` | `profile_show(name)` | 4 | Pokaż szczegóły profilu diagnostycznego. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L42) |
| `projects_cmd` | `projects_cmd(path, threshold, stale_days, only_stale, ...)` | 24 ⚠️ | Skanuje projekty deweloperskie (np. ~/github/*/*) w poszukiwaniu | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/projects_cmd.py#L384) |
| `llm_providers` | `llm_providers(free)` | 6 | Lista dostępnych providerów LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L110) |
| `providers` | `providers()` | 4 | Lista providerów LLM z oznaczeniem FREE/PAID. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L159) |
| `test_llm` | `test_llm(provider, token, model, no_banner)` | 9 | Test połączenia z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L201) |
| `quick` | `quick(hours, json_output, deep, no_save)` | 11 ⚠️ | Natychmiastowa analiza CPU, RAM, dysku, cache i ostatnich przyrostów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L179) |
| `render_quick_snapshot` | `render_quick_snapshot(snapshot)` | 25 ⚠️ | Render the quick snapshot in a stable, readable form. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L26) |
| `quickfix` | `quickfix(dry_run, modules)` | 12 ⚠️ | Natychmiastowe naprawy bez API — baza znanych bugów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quickfix_cmd.py#L13) |
| `report` | `report(output_format, output, modules, profile)` | 5 | Eksport wyników diagnostyki do raportu HTML/Markdown/JSON. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/report_cmd.py#L97) |
| `rollback` | `rollback()` | 1 | Zarządzanie cofaniem operacji fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L10) |
| `rollback_list` | `rollback_list(limit)` | 3 | Pokaż historię sesji naprawczych. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L17) |
| `rollback_show` | `rollback_show(session_id)` | 5 | Pokaż szczegóły sesji rollback. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L38) |
| `rollback_undo` | `rollback_undo(session_id, last, dry_run)` | 7 | Cofnij operacje z podanej sesji. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L70) |
| `scan` | `scan(modules, output, show_raw, no_banner, ...)` | 11 ⚠️ | Przeprowadza diagnostykę systemu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/scan_cmd.py#L70) |
| `add_common_options` | `add_common_options(fn)` | 2 | Decorator adding common LLM options to a Click command. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L45) |
| `add_shared_options` | `add_shared_options(func)` | 1 | Shared options for both scan and fix commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L52) |
| `get_banner` | `get_banner()` | 1 | Return the CLI banner with the installed package version. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L19) |
| `get_command_completer` | `get_command_completer()` | 1 | Build a nested completer for all fixOS commands and common options. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L20) |
| `print_interactive_menu` | `print_interactive_menu()` | 2 | Display the interactive quick menu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L69) |
| `run_interactive_shell` | `run_interactive_shell(ctx)` | 16 ⚠️ | Run the main interactive prompt loop. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L127) |
| `shell_cmd` | `shell_cmd(ctx)` | 1 | Uruchom interaktywny shell fixOS z menu i autouzupełnianiem TAB. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L122) |
| `token` | `token()` | 1 | Zarządzanie tokenem API. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L11) |
| `token_clear` | `token_clear(env_file)` | 3 | Usuń token z pliku .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L113) |
| `token_set` | `token_set(key, provider, env_file)` | 7 | Zapisz token API do pliku .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L22) |
| `token_show` | `token_show()` | 2 | Pokaż obecny token (masked). | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L97) |
| `watch` | `watch(interval, modules, alert_on, max_iterations)` | 2 | Monitorowanie systemu w tle z powiadomieniami. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/watch_cmd.py#L36) |
| `detect_provider_from_key` | `detect_provider_from_key(key)` | 3 | Wykrywa provider na podstawie prefiksu klucza API. | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L429) |
| `get_providers_list` | `get_providers_list()` | 3 | Zwraca listę providerów jako listę słowników. | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L448) |
| `interactive_provider_setup` | `interactive_provider_setup()` | 1 | Interaktywny wybór providera gdy brak konfiguracji. | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L437) |
| `interactive_provider_setup` | `interactive_provider_setup()` | 5 | Interaktywny wybór providera gdy brak konfiguracji. | [source](https://github.com/semcod/fixos/blob/main/fixos/config_interactive.py#L121) |
| `discover_additional_caches` | `discover_additional_caches(get_size_mb, threshold_mb, covered_paths)` | 5 | Discover large caches not already covered by known service scanners. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L109) |
| `is_generic_cache_safe` | `is_generic_cache_safe(path)` | 2 | Heuristic safety check for unknown cache directories. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L103) |
| `normalize_path` | `normalize_path(path)` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L85) |
| `path_is_covered` | `path_is_covered(path, covered_paths)` | 5 | Return True when path is already represented by a known service scan. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L89) |
| `diagnose_audio` | `diagnose_audio()` | 1 | Diagnostyka dźwięku (ALSA/PipeWire/PulseAudio/SOF). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/audio.py#L11) |
| `diagnose_files` | `diagnose_files()` | 4 | Diagnostyka plików użytkownika. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/file_analysis.py#L17) |
| `diagnose_hardware` | `diagnose_hardware()` | 1 | Diagnostyka sprzętu laptopa/desktopa (ACPI, kamera, touchpad, DMI). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/hardware.py#L10) |
| `diagnose_packages` | `diagnose_packages()` | 4 | Diagnostyka zainstalowanych pakietów i środowiska. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/packages.py#L18) |
| `diagnose_resources` | `diagnose_resources()` | 13 ⚠️ | Diagnostyka zasobów systemowych. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/resources.py#L24) |
| `diagnose_security` | `diagnose_security()` | 4 | Diagnostyka bezpieczeństwa systemu i sieci. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/security.py#L18) |
| `diagnose_storage` | `diagnose_storage()` | 4 | Diagnostyka optymalizacji dysków i partycji. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/storage_optimization.py#L11) |
| `diagnose_system` | `diagnose_system()` | 11 ⚠️ | System metrics – cross-platform: CPU, RAM, disks, processes. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/system_core.py#L96) |
| `diagnose_thumbnails` | `diagnose_thumbnails()` | 1 | Diagnostyka podglądów plików (thumbnails) w system. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/thumbnails.py#L10) |
| `main` | `main()` | 1 | Test the disk analyzer | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L487) |
| `analyze_flatpak_for_cleanup` | `analyze_flatpak_for_cleanup()` | 1 | Convenience function to run full Flatpak analysis | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L163) |
| `analyze_idea_log` | `analyze_idea_log(text)` | 15 ⚠️ | Extract bounded, explainable stall signals from JetBrains log text. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L171) |
| `collect_jetbrains_metrics` | `collect_jetbrains_metrics(pid)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L294) |
| `is_main_jetbrains_process` | `is_main_jetbrains_process(process)` | 1 | Return true only for a main IDE process, never a helper/server. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L148) |
| `jetbrains_product_marker` | `jetbrains_product_marker(process)` | 9 | Identify a product only from its launcher, never arbitrary arguments. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L154) |
| `parse_edt_thread` | `parse_edt_thread(text)` | 7 | Extract the AWT event-dispatch thread from a ``Thread.print`` result. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L246) |
| `parse_heap_info` | `parse_heap_info(text)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L236) |
| `read_log_since` | `read_log_since(path, offset)` | 3 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L283) |
| `read_log_tail` | `read_log_tail(path)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L273) |
| `collect_processes` | `collect_processes()` | 13 ⚠️ | Collect a best-effort process snapshot using the existing psutil dependency. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L135) |
| `parse_proc_locks` | `parse_proc_locks(text)` | 8 | Parse blocked lock requests from Linux ``/proc/locks`` content. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L172) |
| `read_linux_lock_waits` | `read_linux_lock_waits(path)` | 2 | Read Linux lock dependencies; return no evidence on other/denied systems. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L210) |
| `discover_project_roots` | `discover_project_roots(base, max_depth)` | 9 | Find developer project roots under `base` (dirs carrying a known | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L143) |
| `find_duplicate_venvs` | `find_duplicate_venvs(artifacts)` | 5 | Project paths that carry more than one virtualenv-type artifact at | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L235) |
| `scan_all` | `scan_all(base, threshold_mb, stale_days, max_depth)` | 2 | Scan every project under `base` for removable artifacts, largest first. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L221) |
| `scan_project_artifacts` | `scan_project_artifacts(project_root, threshold_mb, stale_days)` | 7 | Find removable artifacts directly under a single project root. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L174) |
| `summarize` | `summarize(artifacts)` | 9 | Aggregate stats used for the CLI summary header. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L245) |
| `collect_quick_snapshot` | `collect_quick_snapshot()` | 7 | Collect a bounded, heuristic snapshot without using an LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L784) |
| `main` | `main()` | 1 | Test the service data scanner. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L665) |
| `get_full_diagnostics` | `get_full_diagnostics(modules, progress_callback)` | 12 ⚠️ | Zbiera diagnostykę z wybranych modułów. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/system_checks.py#L49) |
| `format_size` | `format_size(size_bytes)` | 3 | Format bytes to human-readable string (B/KB/MB/GB/TB/PB). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/utils.py#L6) |
| `main` | `main()` | 1 | Test the cleanup planner | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L437) |
| `execute_command` | `execute_command(cmd)` | 10 | Wykonuje komendę systemową z potwierdzeniem użytkownika. | [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L67) |
| `format_time` | `format_time(seconds)` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L59) |
| `run_llm_shell` | `run_llm_shell(diagnostics_data, token, model, timeout, ...)` | 8 | Uruchamia interaktywny shell LLM z przekazanymi danymi diagnostycznymi. | [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L175) |
| `default_pin_path` | `default_pin_path()` | 2 | Return the XDG-compliant per-user pin store path. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L34) |
| `normalize_project_path` | `normalize_project_path(value)` | 3 | Return a stable absolute path without requiring the path to exist. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L22) |
| `cancel_signal_timeout` | `cancel_signal_timeout()` | 2 | Cancels the timeout signal (POSIX only). | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L246) |
| `elevate_cmd` | `elevate_cmd(cmd)` | 3 | Adds sudo (Linux/Mac) or wraps in PowerShell -Verb RunAs (Windows). | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L93) |
| `get_os_info` | `get_os_info()` | 5 | Returns basic OS information. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L21) |
| `get_package_manager` | `get_package_manager()` | 8 | Detects the system package manager. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L187) |
| `install_package_cmd` | `install_package_cmd(package)` | 2 | Returns the install command for the detected package manager. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L205) |
| `is_dangerous` | `is_dangerous(cmd)` | 3 | Returns reason string if command is dangerous, None if safe. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L104) |
| `is_interactive_blocker` | `is_interactive_blocker(cmd)` | 3 | Returns reason string if command is likely to hang in non-interactive session. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L127) |
| `needs_elevation` | `needs_elevation(cmd)` | 5 | Returns True if command likely needs admin/sudo. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L44) |
| `run_command` | `run_command(cmd, timeout, shell)` | 5 | Runs a command cross-platform. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L149) |
| `setup_signal_timeout` | `setup_signal_timeout(seconds, handler)` | 2 | Sets up a timeout signal. Returns True if supported (POSIX only). | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L232) |
| `main` | `main()` | 1 | Test the LLM analyzer | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L351) |
| `get_cpu_info` | `get_cpu_info()` | 2 | Metryki CPU. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L28) |
| `get_disk_info` | `get_disk_info()` | 3 | Metryki dysków dla wszystkich partycji. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L56) |
| `get_fedora_specific` | `get_fedora_specific()` | 1 | Komendy specyficzne dla system: dnf, journalctl, systemctl. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L105) |
| `get_full_diagnostics` | `get_full_diagnostics()` | 1 | Zbiera kompletne dane diagnostyczne systemu system. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L140) |
| `get_memory_info` | `get_memory_info()` | 1 | Metryki RAM i SWAP. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L41) |
| `get_network_info` | `get_network_info()` | 4 | Statystyki sieciowe (bez wrażliwych danych - anonimizacja jest osobno). | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L75) |
| `get_top_processes` | `get_top_processes(n)` | 3 | Lista TOP N procesów według zużycia CPU. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L91) |
| `run_cmd` | `run_cmd(cmd, timeout)` | 6 | Uruchamia komendę shell i zwraca output. Bezpieczny fallback przy błędzie. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L12) |
| `anonymize` | `anonymize(data_str, context)` | 7 | Anonimizuje wrażliwe dane. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L272) |
| `deanonymize` | `deanonymize(text, context, allowed_aliases)` | 3 | Resolve aliases locally while preserving the legacy primary tokens. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L360) |
| `display_anonymized_preview` | `display_anonymized_preview(data_str, report, max_lines)` | 5 | Wyświetla użytkownikowi zanonimizowane dane przed wysłaniem do LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L373) |
| `colorize` | `colorize(line)` | 1 | Return line unchanged – rich handles markup in render_md(). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L60) |
| `print_cmd_block` | `print_cmd_block(cmd, comment, dry_run)` | 4 | Print a framed command preview panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L188) |
| `print_problem_header` | `print_problem_header(problem_id, description, severity, status, ...)` | 3 | Print a colored problem header panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L255) |
| `print_stderr_box` | `print_stderr_box(stderr, max_lines)` | 1 | Print stderr in a rich Panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L228) |
| `print_stdout_box` | `print_stdout_box(stdout, max_lines)` | 1 | Print stdout in a rich Panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L223) |
| `render_md` | `render_md(text)` | 9 | Print LLM markdown reply to terminal via rich. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L101) |
| `render_tree_colored` | `render_tree_colored(nodes, execution_order)` | 8 | Render a ProblemGraph as a rich-markup string. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L283) |
| `timeout_handler` | `timeout_handler(signum, frame)` | 1 | Signal handler dla SIGALRM — rzuca SessionTimeout. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L16) |
| `format_results_for_llm` | `format_results_for_llm(results)` | 3 | Formatuje wyniki wyszukiwania do wklejenia w prompt LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L267) |
| `search_all` | `search_all(query, serpapi_key, max_per_source)` | 5 | Przeszukuje wszystkie dostępne źródła wiedzy. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L223) |
| `search_arch_wiki` | `search_arch_wiki(query, max_results)` | 9 | Arch Wiki – doskonałe źródło dla problemów Linux (nie tylko Arch). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L90) |
| `search_ask_fedora` | `search_ask_fedora(query, max_results)` | 4 | Szuka w Linux forums przez Discourse API. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L66) |
| `search_ddg` | `search_ddg(query, max_results)` | 8 | DuckDuckGo Instant Answer API (bez klucza, ograniczone). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L187) |
| `search_fedora_bugzilla` | `search_fedora_bugzilla(query, max_results)` | 4 | Szuka w Linux Bugzilla przez REST API. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L38) |
| `search_github_issues` | `search_github_issues(query, max_results)` | 4 | GitHub Issues – linuxhardware, ALSA, PipeWire, PulseAudio repos. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L120) |
| `search_serpapi` | `search_serpapi(query, api_key, max_results)` | 5 | SerpAPI – Google/Bing search (wymaga klucza API). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L157) |

## docker

### `docker.test-multi-system` [source](https://github.com/semcod/fixos/blob/main/docker/test-multi-system.sh)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `test_system` | `test_system()` | — | — | [source](https://github.com/semcod/fixos/blob/main/docker/test-multi-system.sh#L33) |

### `docker.test-scenarios` [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `build_base` | `build_base()` | — | — | [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh#L46) |
| `main` | `main()` | — | — | [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh#L105) |
| `run_scenario` | `run_scenario()` | — | — | [source](https://github.com/semcod/fixos/blob/main/docker/test-scenarios.sh#L53) |

### `docker.validate-scenario` [source](https://github.com/semcod/fixos/blob/main/docker/validate-scenario.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `main` | `main()` | 7 | — | [source](https://github.com/semcod/fixos/blob/main/docker/validate-scenario.py#L127) |
| `validate` | `validate(data, scenario)` | 11 ⚠️ | Validate data against scenario expectations. Returns list of failures. | [source](https://github.com/semcod/fixos/blob/main/docker/validate-scenario.py#L84) |

## docs

### `docs.examples.quickstart` [source](https://github.com/semcod/fixos/blob/main/docs/examples/quickstart.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `run_autonomous_session` | `run_autonomous_session()` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/docs/examples/quickstart.py#L4) |

## fixos

### `fixos.agent` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `AgentReport` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L90) |
| `AutonomousSession` | 1 | Self-directed autonomous diagnostic and repair session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L113) |
| `FixAction` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L81) |
| `HITLSession` | 2 | Interactive Human-in-the-Loop diagnostic and repair session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L36) |
| `CmdResult` | 1 | Result of executed command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L19) |
| `DiagnosticChoice` | 0 | A diagnosed problem that is selectable but has no executable plan yet. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L76) |
| `RemediationAction` | 2 | One policy-labelled strategy for resolving a diagnostic finding. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L43) |

**`HITLSession` methods:**

- `remaining()` — Get remaining session time in seconds.
- `run()` — Run the HITL session.

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `run_autonomous_session` | `run_autonomous_session(diagnostics, config, show_data, max_fixes)` | 1 | Uruchamia autonomiczny tryb agenta. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous.py#L31) |
| `run_autonomous_session` | `run_autonomous_session(diagnostics, config, show_data, max_fixes)` | 1 | Run autonomous session (backward compatible wrapper). | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L460) |
| `get_remaining_time` | `get_remaining_time(session)` | 2 | Calculate remaining session time in seconds. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/__init__.py#L22) |
| `run_hitl_session` | `run_hitl_session(diagnostics, config, show_data)` | 1 | Run interactive HITL session with full transparency. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl.py#L24) |
| `run_hitl_session` | `run_hitl_session(diagnostics, config, show_data)` | 1 | Run interactive HITL session (backward compatible wrapper). | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L359) |
| `extract_diagnostic_choices` | `extract_diagnostic_choices(reply)` | 12 ⚠️ | Extract non-executable choices from numbered diagnosis headings. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L628) |
| `extract_fixes` | `extract_fixes(reply)` | 4 | Extract (command, comment) pairs from LLM reply. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L380) |
| `extract_remediation_actions` | `extract_remediation_actions(reply)` | 4 | Parse a closed remediation plan, falling back to legacy command syntax. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L603) |
| `extract_search_topic` | `extract_search_topic(llm_reply)` | 3 | Extract search keywords from LLM reply. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L710) |
| `select_recommended_actions` | `select_recommended_actions(actions)` | 4 | Return at most one recommended strategy for each finding. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L697) |
| `strip_remediation_plan` | `strip_remediation_plan(reply)` | 1 | Hide the machine plan block from the human-readable diagnosis. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L617) |
| `transform_remediation_commands` | `transform_remediation_commands(action, transform)` | 4 | Apply anonymization reversal to executable fields only. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L674) |
| `handle_cleanup_intent` | `handle_cleanup_intent(messages)` | 1 | Ask for a cleanup plan without authorizing or executing any command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L111) |
| `handle_describe_problem` | `handle_describe_problem(messages, ask_fn)` | 2 | Handle [D] Describe own problem command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L86) |
| `handle_direct_command` | `handle_direct_command(user_in, messages, executed, run_cmd_fn)` | 1 | Handle [!cmd] Direct command execution. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L408) |
| `handle_execute_all` | `handle_execute_all(fixes, messages, executed, run_cmd_fn)` | 17 ⚠️ | Handle [A] Execute all commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L283) |
| `handle_fix_by_number` | `handle_fix_by_number(user_in, fixes, messages, executed, ...)` | 9 | Handle [N] Execute specific fix by number. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L344) |
| `handle_free_text` | `handle_free_text(user_in, messages)` | 1 | Handle free text input → send to LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L443) |
| `handle_quit` | `handle_quit()` | 1 | Handle [Q] Quit command. Returns False to exit loop. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L72) |
| `handle_search` | `handle_search(user_in, messages, serpapi_key)` | 2 | Handle [search <q>] Web search command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L425) |
| `handle_skip_all` | `handle_skip_all(messages)` | 1 | Handle [S] Skip all command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L78) |
| `is_cleanup_intent` | `is_cleanup_intent(user_in)` | 2 | Recognize a bounded single-word spelling variant of ``cleanup``. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L103) |
| `parse_user_input` | `parse_user_input(user_in, fixes, messages, executed, ...)` | 10 | Parse user input and execute appropriate handler. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L515) |
| `run_single_command` | `run_single_command(cmd, comment)` | 5 | Run a command with full transparency and safety checks. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L449) |
| `ask_execute_prompt` | `ask_execute_prompt()` | 1 | Ask user if they want to execute a command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L375) |
| `ask_low_confidence_search` | `ask_low_confidence_search()` | 1 | Ask user if they want to search when LLM is uncertain. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L381) |
| `ask_send_data` | `ask_send_data()` | 1 | Ask user if they want to send data to LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L389) |
| `ask_user_problem` | `ask_user_problem()` | 2 | Interactively asks the user to describe their problem. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L222) |
| `clear_thinking` | `clear_thinking()` | 1 | Clear the 'Analyzing...' indicator. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L300) |
| `fmt_time` | `fmt_time(s)` | 1 | Format seconds as HH:MM:SS. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L81) |
| `get_user_input` | `get_user_input(remaining)` | 2 | Get user input with prompt. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L396) |
| `print_action_menu` | `print_action_menu(fixes, remaining, total_tokens, completed_count)` | 19 ⚠️ | Print the refreshed interactive menu of remaining choices. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L86) |
| `print_blocked_command` | `print_blocked_command(cmd, reason)` | 1 | Print blocked dangerous command warning. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L317) |
| `print_cmd_preview` | `print_cmd_preview(cmd, comment)` | 1 | Shows command in a clear block before execution. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L254) |
| `print_cmd_result` | `print_cmd_result(result)` | 8 | Shows command result with colorized markdown. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L259) |
| `print_executing_all` | `print_executing_all(count)` | 1 | Print executing all recommended command sets message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L338) |
| `print_invalid_option` | `print_invalid_option(user_in, max_option)` | 1 | Print invalid option message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L358) |
| `print_llm_error` | `print_llm_error(e)` | 1 | Print LLM error message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L312) |
| `print_llm_reply` | `print_llm_reply(reply)` | 1 | Render LLM reply with markdown formatting. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L305) |
| `print_no_commands` | `print_no_commands()` | 1 | Print no commands available message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L345) |
| `print_no_results` | `print_no_results()` | 1 | Print no search results message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L365) |
| `print_searching` | `print_searching()` | 1 | Print searching message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L370) |
| `print_select_one` | `print_select_one()` | 1 | Explain that diagnosis-only choices must be focused individually. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L350) |
| `print_session_ended` | `print_session_ended()` | 1 | Print session ended message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L328) |
| `print_session_header` | `print_session_header(os_info, pkg_manager, model, timeout, ...)` | 1 | Print session header with system info. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L64) |
| `print_session_interrupted` | `print_session_interrupted()` | 1 | Print session interrupted message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L333) |
| `print_session_summary` | `print_session_summary(messages_count, elapsed, total_tokens, executed)` | 3 | Print session summary. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L284) |
| `print_thinking` | `print_thinking()` | 1 | Print 'Analyzing...' indicator. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L295) |
| `print_timeout` | `print_timeout()` | 1 | Print session timeout message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L323) |
| `suspend_timeout` | `suspend_timeout()` | 4 | Context manager to temporarily suspend session timeout during user input. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L39) |

### `fixos.agent.autonomous` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `run_autonomous_session` | `run_autonomous_session(diagnostics, config, show_data, max_fixes)` | 1 | Uruchamia autonomiczny tryb agenta. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous.py#L31) |

### `fixos.agent.autonomous_session` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `AgentReport` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L90) |
| `AutonomousSession` | 1 | Self-directed autonomous diagnostic and repair session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L113) |
| `FixAction` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L81) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `run_autonomous_session` | `run_autonomous_session(diagnostics, config, show_data, max_fixes)` | 1 | Run autonomous session (backward compatible wrapper). | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/autonomous_session.py#L460) |

### `fixos.agent.hitl` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `run_hitl_session` | `run_hitl_session(diagnostics, config, show_data)` | 1 | Run interactive HITL session with full transparency. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl.py#L24) |

### `fixos.agent.hitl_session` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `HITLSession` | 2 | Interactive Human-in-the-Loop diagnostic and repair session. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L36) |

**`HITLSession` methods:**

- `remaining()` — Get remaining session time in seconds.
- `run()` — Run the HITL session.

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `run_hitl_session` | `run_hitl_session(diagnostics, config, show_data)` | 1 | Run interactive HITL session (backward compatible wrapper). | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/hitl_session.py#L359) |

### `fixos.agent.session_core` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `CmdResult` | 1 | Result of executed command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L19) |
| `DiagnosticChoice` | 0 | A diagnosed problem that is selectable but has no executable plan yet. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L76) |
| `RemediationAction` | 2 | One policy-labelled strategy for resolving a diagnostic finding. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L43) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `extract_diagnostic_choices` | `extract_diagnostic_choices(reply)` | 12 ⚠️ | Extract non-executable choices from numbered diagnosis headings. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L628) |
| `extract_fixes` | `extract_fixes(reply)` | 4 | Extract (command, comment) pairs from LLM reply. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L380) |
| `extract_remediation_actions` | `extract_remediation_actions(reply)` | 4 | Parse a closed remediation plan, falling back to legacy command syntax. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L603) |
| `extract_search_topic` | `extract_search_topic(llm_reply)` | 3 | Extract search keywords from LLM reply. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L710) |
| `select_recommended_actions` | `select_recommended_actions(actions)` | 4 | Return at most one recommended strategy for each finding. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L697) |
| `strip_remediation_plan` | `strip_remediation_plan(reply)` | 1 | Hide the machine plan block from the human-readable diagnosis. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L617) |
| `transform_remediation_commands` | `transform_remediation_commands(action, transform)` | 4 | Apply anonymization reversal to executable fields only. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_core.py#L674) |

### `fixos.agent.session_handlers` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `handle_cleanup_intent` | `handle_cleanup_intent(messages)` | 1 | Ask for a cleanup plan without authorizing or executing any command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L111) |
| `handle_describe_problem` | `handle_describe_problem(messages, ask_fn)` | 2 | Handle [D] Describe own problem command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L86) |
| `handle_direct_command` | `handle_direct_command(user_in, messages, executed, run_cmd_fn)` | 1 | Handle [!cmd] Direct command execution. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L408) |
| `handle_execute_all` | `handle_execute_all(fixes, messages, executed, run_cmd_fn)` | 17 ⚠️ | Handle [A] Execute all commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L283) |
| `handle_fix_by_number` | `handle_fix_by_number(user_in, fixes, messages, executed, ...)` | 9 | Handle [N] Execute specific fix by number. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L344) |
| `handle_free_text` | `handle_free_text(user_in, messages)` | 1 | Handle free text input → send to LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L443) |
| `handle_quit` | `handle_quit()` | 1 | Handle [Q] Quit command. Returns False to exit loop. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L72) |
| `handle_search` | `handle_search(user_in, messages, serpapi_key)` | 2 | Handle [search <q>] Web search command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L425) |
| `handle_skip_all` | `handle_skip_all(messages)` | 1 | Handle [S] Skip all command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L78) |
| `is_cleanup_intent` | `is_cleanup_intent(user_in)` | 2 | Recognize a bounded single-word spelling variant of ``cleanup``. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L103) |
| `parse_user_input` | `parse_user_input(user_in, fixes, messages, executed, ...)` | 10 | Parse user input and execute appropriate handler. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L515) |
| `run_single_command` | `run_single_command(cmd, comment)` | 5 | Run a command with full transparency and safety checks. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_handlers.py#L449) |

### `fixos.agent.session_io` [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `ask_execute_prompt` | `ask_execute_prompt()` | 1 | Ask user if they want to execute a command. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L375) |
| `ask_low_confidence_search` | `ask_low_confidence_search()` | 1 | Ask user if they want to search when LLM is uncertain. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L381) |
| `ask_send_data` | `ask_send_data()` | 1 | Ask user if they want to send data to LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L389) |
| `ask_user_problem` | `ask_user_problem()` | 2 | Interactively asks the user to describe their problem. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L222) |
| `clear_thinking` | `clear_thinking()` | 1 | Clear the 'Analyzing...' indicator. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L300) |
| `fmt_time` | `fmt_time(s)` | 1 | Format seconds as HH:MM:SS. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L81) |
| `get_user_input` | `get_user_input(remaining)` | 2 | Get user input with prompt. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L396) |
| `print_action_menu` | `print_action_menu(fixes, remaining, total_tokens, completed_count)` | 19 ⚠️ | Print the refreshed interactive menu of remaining choices. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L86) |
| `print_blocked_command` | `print_blocked_command(cmd, reason)` | 1 | Print blocked dangerous command warning. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L317) |
| `print_cmd_preview` | `print_cmd_preview(cmd, comment)` | 1 | Shows command in a clear block before execution. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L254) |
| `print_cmd_result` | `print_cmd_result(result)` | 8 | Shows command result with colorized markdown. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L259) |
| `print_executing_all` | `print_executing_all(count)` | 1 | Print executing all recommended command sets message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L338) |
| `print_invalid_option` | `print_invalid_option(user_in, max_option)` | 1 | Print invalid option message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L358) |
| `print_llm_error` | `print_llm_error(e)` | 1 | Print LLM error message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L312) |
| `print_llm_reply` | `print_llm_reply(reply)` | 1 | Render LLM reply with markdown formatting. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L305) |
| `print_no_commands` | `print_no_commands()` | 1 | Print no commands available message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L345) |
| `print_no_results` | `print_no_results()` | 1 | Print no search results message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L365) |
| `print_searching` | `print_searching()` | 1 | Print searching message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L370) |
| `print_select_one` | `print_select_one()` | 1 | Explain that diagnosis-only choices must be focused individually. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L350) |
| `print_session_ended` | `print_session_ended()` | 1 | Print session ended message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L328) |
| `print_session_header` | `print_session_header(os_info, pkg_manager, model, timeout, ...)` | 1 | Print session header with system info. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L64) |
| `print_session_interrupted` | `print_session_interrupted()` | 1 | Print session interrupted message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L333) |
| `print_session_summary` | `print_session_summary(messages_count, elapsed, total_tokens, executed)` | 3 | Print session summary. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L284) |
| `print_thinking` | `print_thinking()` | 1 | Print 'Analyzing...' indicator. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L295) |
| `print_timeout` | `print_timeout()` | 1 | Print session timeout message. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L323) |
| `suspend_timeout` | `suspend_timeout()` | 4 | Context manager to temporarily suspend session timeout during user input. | [source](https://github.com/semcod/fixos/blob/main/fixos/agent/session_io.py#L39) |

### `fixos.anonymizer` [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `anonymize` | `anonymize(data_str)` | 1 | Keep the original string-only return shape used by ``llm_shell``. | [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py#L16) |
| `get_sensitive_values` | `get_sensitive_values()` | 1 | Return legacy key names without maintaining a second privacy policy. | [source](https://github.com/semcod/fixos/blob/main/fixos/anonymizer.py#L6) |

### `fixos.cli` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `OutputFormat` | 0 | Supported output formats. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L24) |
| `OutputFormatter` | 9 | Centralized output formatter for fixOS CLI commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L43) |
| `NaturalLanguageGroup` | 1 | Click group that intelligently handles typos and routes natural language commands to 'ask'. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L107) |

**`OutputFormatter` methods:**

- `from_flags(cls, yaml_output, json_output)` — Create formatter from CLI flag values. YAML takes precedence over JSON.
- `status(msg, fg, bold)` — Print a status/progress message. Goes to stderr in machine mode.
- `progress(name, desc)` — Print a progress line for diagnostic module collection.
- `banner(text)` — Print banner. Suppressed in machine mode.
- `emit(data, stream)` — Emit structured data to stdout in the configured format.
- `format_data(data)` — Format data dict/list as string in the configured format.
- `format_diagnostics(data)` — Format full diagnostic result with metadata envelope.
- `format_scan_result(data)` — Format scan results with optional disk analysis.

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `ask` | `ask(prompt, dry_run)` | 1 | Wykonaj polecenie w języku naturalnym. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/ask_cmd.py#L13) |
| `cleanup_services` | `cleanup_services(threshold, services, json_output, cleanup, ...)` | 56 ⚠️ | Skanuje i czyści dane usług przekraczające próg. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/cleanup_cmd.py#L1384) |
| `config` | `config()` | 1 | Zarządzanie konfiguracją fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L41) |
| `config_init` | `config_init(force)` | 3 | Zainicjalizuj plik konfiguracyjny .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L77) |
| `config_model` | `config_model(provider)` | 8 | Interaktywnie wybierz model LLM z listy. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L133) |
| `config_provider` | `config_provider()` | 6 | Interaktywnie wybierz providera LLM z listy. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L262) |
| `config_set` | `config_set(key, value)` | 2 | Ustaw wartość konfiguracyjną w .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L112) |
| `config_show` | `config_show()` | 4 | Pokaż aktualną konfigurację. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L47) |
| `features` | `features()` | 1 | Zarządzanie pakietami komfortu systemu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L20) |
| `features_audit` | `features_audit(profile, json_output)` | 4 | Sprawdź brakujące pakiety dla profilu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L30) |
| `features_install` | `features_install(profile, dry_run, yes, category)` | 7 | Zainstaluj brakujące pakiety dla profilu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L91) |
| `features_profiles` | `features_profiles()` | 3 | Lista dostępnych profili. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L122) |
| `features_system` | `features_system()` | 1 | Pokaż wykryty system. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L143) |
| `execute_cleanup_actions` | `execute_cleanup_actions(actions, cfg, llm_fallback)` | 6 | Execute cleanup actions with safety checks | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L349) |
| `fix` | `fix(provider, token, model, no_banner, ...)` | 13 ⚠️ | Przeprowadza pełną diagnostykę i uruchamia sesję naprawczą z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L130) |
| `handle_disk_cleanup_mode` | `handle_disk_cleanup_mode(disk_analysis, cfg, dry_run, interactive, ...)` | 13 ⚠️ | Handle disk cleanup mode with interactive planning | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L245) |
| `try_llm_fallback_for_failures` | `try_llm_fallback_for_failures(failed_actions, cfg)` | 3 | Try to fix failed actions using LLM | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L390) |
| `history` | `history(limit, json_output)` | 5 | Historia napraw fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/history_cmd.py#L11) |
| `ai_control` | `ai_control(config_dir, disable_plugins, stop_qoder, apply, ...)` | 23 ⚠️ | Diagnozuj i ogranicz dodatki AI bez zamykania okien IDE. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L283) |
| `doctor` | `doctor(pid, minutes, no_thread_dump, json_output, ...)` | 25 ⚠️ | Zbierz metryki JVM, stan EDT i sygnały z idea.log. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L162) |
| `jetbrains` | `jetbrains()` | 1 | Diagnozuj współdzieloną JVM JetBrains bez zamykania okien. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L137) |
| `cli` | `cli(ctx, dry_run, interactive_mode, version)` | 7 | fixos – AI-powered diagnostyka i naprawa Linux, Windows, macOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L28) |
| `main` | `main()` | 1 | Entry point for fixOS CLI. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L239) |
| `orchestrate` | `orchestrate(provider, token, model, no_banner, ...)` | 13 ⚠️ | Zaawansowana orkiestracja napraw z grafem problemów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/orchestrate_cmd.py#L30) |
| `profile` | `profile()` | 1 | Zarządzanie profilami diagnostycznymi. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L9) |
| `profile_list` | `profile_list()` | 4 | Pokaż dostępne profile diagnostyczne. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L15) |
| `profile_show` | `profile_show(name)` | 4 | Pokaż szczegóły profilu diagnostycznego. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L42) |
| `projects_cmd` | `projects_cmd(path, threshold, stale_days, only_stale, ...)` | 24 ⚠️ | Skanuje projekty deweloperskie (np. ~/github/*/*) w poszukiwaniu | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/projects_cmd.py#L384) |
| `llm_providers` | `llm_providers(free)` | 6 | Lista dostępnych providerów LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L110) |
| `providers` | `providers()` | 4 | Lista providerów LLM z oznaczeniem FREE/PAID. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L159) |
| `test_llm` | `test_llm(provider, token, model, no_banner)` | 9 | Test połączenia z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L201) |
| `quick` | `quick(hours, json_output, deep, no_save)` | 11 ⚠️ | Natychmiastowa analiza CPU, RAM, dysku, cache i ostatnich przyrostów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L179) |
| `render_quick_snapshot` | `render_quick_snapshot(snapshot)` | 25 ⚠️ | Render the quick snapshot in a stable, readable form. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L26) |
| `quickfix` | `quickfix(dry_run, modules)` | 12 ⚠️ | Natychmiastowe naprawy bez API — baza znanych bugów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quickfix_cmd.py#L13) |
| `report` | `report(output_format, output, modules, profile)` | 5 | Eksport wyników diagnostyki do raportu HTML/Markdown/JSON. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/report_cmd.py#L97) |
| `rollback` | `rollback()` | 1 | Zarządzanie cofaniem operacji fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L10) |
| `rollback_list` | `rollback_list(limit)` | 3 | Pokaż historię sesji naprawczych. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L17) |
| `rollback_show` | `rollback_show(session_id)` | 5 | Pokaż szczegóły sesji rollback. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L38) |
| `rollback_undo` | `rollback_undo(session_id, last, dry_run)` | 7 | Cofnij operacje z podanej sesji. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L70) |
| `scan` | `scan(modules, output, show_raw, no_banner, ...)` | 11 ⚠️ | Przeprowadza diagnostykę systemu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/scan_cmd.py#L70) |
| `add_common_options` | `add_common_options(fn)` | 2 | Decorator adding common LLM options to a Click command. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L45) |
| `add_shared_options` | `add_shared_options(func)` | 1 | Shared options for both scan and fix commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L52) |
| `get_banner` | `get_banner()` | 1 | Return the CLI banner with the installed package version. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L19) |
| `get_command_completer` | `get_command_completer()` | 1 | Build a nested completer for all fixOS commands and common options. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L20) |
| `print_interactive_menu` | `print_interactive_menu()` | 2 | Display the interactive quick menu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L69) |
| `run_interactive_shell` | `run_interactive_shell(ctx)` | 16 ⚠️ | Run the main interactive prompt loop. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L127) |
| `shell_cmd` | `shell_cmd(ctx)` | 1 | Uruchom interaktywny shell fixOS z menu i autouzupełnianiem TAB. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L122) |
| `token` | `token()` | 1 | Zarządzanie tokenem API. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L11) |
| `token_clear` | `token_clear(env_file)` | 3 | Usuń token z pliku .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L113) |
| `token_set` | `token_set(key, provider, env_file)` | 7 | Zapisz token API do pliku .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L22) |
| `token_show` | `token_show()` | 2 | Pokaż obecny token (masked). | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L97) |
| `watch` | `watch(interval, modules, alert_on, max_iterations)` | 2 | Monitorowanie systemu w tle z powiadomieniami. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/watch_cmd.py#L36) |

### `fixos.cli.ask_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/ask_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `ask` | `ask(prompt, dry_run)` | 1 | Wykonaj polecenie w języku naturalnym. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/ask_cmd.py#L13) |

### `fixos.cli.cleanup_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/cleanup_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `cleanup_services` | `cleanup_services(threshold, services, json_output, cleanup, ...)` | 56 ⚠️ | Skanuje i czyści dane usług przekraczające próg. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/cleanup_cmd.py#L1384) |

### `fixos.cli.config_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `config` | `config()` | 1 | Zarządzanie konfiguracją fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L41) |
| `config_init` | `config_init(force)` | 3 | Zainicjalizuj plik konfiguracyjny .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L77) |
| `config_model` | `config_model(provider)` | 8 | Interaktywnie wybierz model LLM z listy. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L133) |
| `config_provider` | `config_provider()` | 6 | Interaktywnie wybierz providera LLM z listy. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L262) |
| `config_set` | `config_set(key, value)` | 2 | Ustaw wartość konfiguracyjną w .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L112) |
| `config_show` | `config_show()` | 4 | Pokaż aktualną konfigurację. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/config_cmd.py#L47) |

### `fixos.cli.features_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `features` | `features()` | 1 | Zarządzanie pakietami komfortu systemu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L20) |
| `features_audit` | `features_audit(profile, json_output)` | 4 | Sprawdź brakujące pakiety dla profilu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L30) |
| `features_install` | `features_install(profile, dry_run, yes, category)` | 7 | Zainstaluj brakujące pakiety dla profilu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L91) |
| `features_profiles` | `features_profiles()` | 3 | Lista dostępnych profili. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L122) |
| `features_system` | `features_system()` | 1 | Pokaż wykryty system. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/features_cmd.py#L143) |

### `fixos.cli.fix_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `execute_cleanup_actions` | `execute_cleanup_actions(actions, cfg, llm_fallback)` | 6 | Execute cleanup actions with safety checks | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L349) |
| `fix` | `fix(provider, token, model, no_banner, ...)` | 13 ⚠️ | Przeprowadza pełną diagnostykę i uruchamia sesję naprawczą z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L130) |
| `handle_disk_cleanup_mode` | `handle_disk_cleanup_mode(disk_analysis, cfg, dry_run, interactive, ...)` | 13 ⚠️ | Handle disk cleanup mode with interactive planning | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L245) |
| `try_llm_fallback_for_failures` | `try_llm_fallback_for_failures(failed_actions, cfg)` | 3 | Try to fix failed actions using LLM | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/fix_cmd.py#L390) |

### `fixos.cli.history_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/history_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `history` | `history(limit, json_output)` | 5 | Historia napraw fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/history_cmd.py#L11) |

### `fixos.cli.jetbrains_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `ai_control` | `ai_control(config_dir, disable_plugins, stop_qoder, apply, ...)` | 23 ⚠️ | Diagnozuj i ogranicz dodatki AI bez zamykania okien IDE. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L283) |
| `doctor` | `doctor(pid, minutes, no_thread_dump, json_output, ...)` | 25 ⚠️ | Zbierz metryki JVM, stan EDT i sygnały z idea.log. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L162) |
| `jetbrains` | `jetbrains()` | 1 | Diagnozuj współdzieloną JVM JetBrains bez zamykania okien. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/jetbrains_cmd.py#L137) |

### `fixos.cli.main` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `cli` | `cli(ctx, dry_run, interactive_mode, version)` | 7 | fixos – AI-powered diagnostyka i naprawa Linux, Windows, macOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L28) |
| `main` | `main()` | 1 | Entry point for fixOS CLI. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/main.py#L239) |

### `fixos.cli.orchestrate_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/orchestrate_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `orchestrate` | `orchestrate(provider, token, model, no_banner, ...)` | 13 ⚠️ | Zaawansowana orkiestracja napraw z grafem problemów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/orchestrate_cmd.py#L30) |

### `fixos.cli.output_formatter` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `OutputFormat` | 0 | Supported output formats. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L24) |
| `OutputFormatter` | 9 | Centralized output formatter for fixOS CLI commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/output_formatter.py#L43) |

**`OutputFormatter` methods:**

- `from_flags(cls, yaml_output, json_output)` — Create formatter from CLI flag values. YAML takes precedence over JSON.
- `status(msg, fg, bold)` — Print a status/progress message. Goes to stderr in machine mode.
- `progress(name, desc)` — Print a progress line for diagnostic module collection.
- `banner(text)` — Print banner. Suppressed in machine mode.
- `emit(data, stream)` — Emit structured data to stdout in the configured format.
- `format_data(data)` — Format data dict/list as string in the configured format.
- `format_diagnostics(data)` — Format full diagnostic result with metadata envelope.
- `format_scan_result(data)` — Format scan results with optional disk analysis.

### `fixos.cli.profile_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `profile` | `profile()` | 1 | Zarządzanie profilami diagnostycznymi. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L9) |
| `profile_list` | `profile_list()` | 4 | Pokaż dostępne profile diagnostyczne. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L15) |
| `profile_show` | `profile_show(name)` | 4 | Pokaż szczegóły profilu diagnostycznego. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/profile_cmd.py#L42) |

### `fixos.cli.projects_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/projects_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `projects_cmd` | `projects_cmd(path, threshold, stale_days, only_stale, ...)` | 24 ⚠️ | Skanuje projekty deweloperskie (np. ~/github/*/*) w poszukiwaniu | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/projects_cmd.py#L384) |

### `fixos.cli.provider_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `llm_providers` | `llm_providers(free)` | 6 | Lista dostępnych providerów LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L110) |
| `providers` | `providers()` | 4 | Lista providerów LLM z oznaczeniem FREE/PAID. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L159) |
| `test_llm` | `test_llm(provider, token, model, no_banner)` | 9 | Test połączenia z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/provider_cmd.py#L201) |

### `fixos.cli.quick_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `quick` | `quick(hours, json_output, deep, no_save)` | 11 ⚠️ | Natychmiastowa analiza CPU, RAM, dysku, cache i ostatnich przyrostów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L179) |
| `render_quick_snapshot` | `render_quick_snapshot(snapshot)` | 25 ⚠️ | Render the quick snapshot in a stable, readable form. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quick_cmd.py#L26) |

### `fixos.cli.quickfix_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quickfix_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `quickfix` | `quickfix(dry_run, modules)` | 12 ⚠️ | Natychmiastowe naprawy bez API — baza znanych bugów. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/quickfix_cmd.py#L13) |

### `fixos.cli.report_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/report_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `report` | `report(output_format, output, modules, profile)` | 5 | Eksport wyników diagnostyki do raportu HTML/Markdown/JSON. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/report_cmd.py#L97) |

### `fixos.cli.rollback_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `rollback` | `rollback()` | 1 | Zarządzanie cofaniem operacji fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L10) |
| `rollback_list` | `rollback_list(limit)` | 3 | Pokaż historię sesji naprawczych. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L17) |
| `rollback_show` | `rollback_show(session_id)` | 5 | Pokaż szczegóły sesji rollback. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L38) |
| `rollback_undo` | `rollback_undo(session_id, last, dry_run)` | 7 | Cofnij operacje z podanej sesji. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/rollback_cmd.py#L70) |

### `fixos.cli.scan_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/scan_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `scan` | `scan(modules, output, show_raw, no_banner, ...)` | 11 ⚠️ | Przeprowadza diagnostykę systemu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/scan_cmd.py#L70) |

### `fixos.cli.shared` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `NaturalLanguageGroup` | 1 | Click group that intelligently handles typos and routes natural language commands to 'ask'. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L107) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `add_common_options` | `add_common_options(fn)` | 2 | Decorator adding common LLM options to a Click command. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L45) |
| `add_shared_options` | `add_shared_options(func)` | 1 | Shared options for both scan and fix commands. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L52) |
| `get_banner` | `get_banner()` | 1 | Return the CLI banner with the installed package version. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shared.py#L19) |

### `fixos.cli.shell_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `get_command_completer` | `get_command_completer()` | 1 | Build a nested completer for all fixOS commands and common options. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L20) |
| `print_interactive_menu` | `print_interactive_menu()` | 2 | Display the interactive quick menu. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L69) |
| `run_interactive_shell` | `run_interactive_shell(ctx)` | 16 ⚠️ | Run the main interactive prompt loop. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L127) |
| `shell_cmd` | `shell_cmd(ctx)` | 1 | Uruchom interaktywny shell fixOS z menu i autouzupełnianiem TAB. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/shell_cmd.py#L122) |

### `fixos.cli.token_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `token` | `token()` | 1 | Zarządzanie tokenem API. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L11) |
| `token_clear` | `token_clear(env_file)` | 3 | Usuń token z pliku .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L113) |
| `token_set` | `token_set(key, provider, env_file)` | 7 | Zapisz token API do pliku .env. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L22) |
| `token_show` | `token_show()` | 2 | Pokaż obecny token (masked). | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/token_cmd.py#L97) |

### `fixos.cli.watch_cmd` [source](https://github.com/semcod/fixos/blob/main/fixos/cli/watch_cmd.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `watch` | `watch(interval, modules, alert_on, max_iterations)` | 2 | Monitorowanie systemu w tle z powiadomieniami. | [source](https://github.com/semcod/fixos/blob/main/fixos/cli/watch_cmd.py#L36) |

### `fixos.config` [source](https://github.com/semcod/fixos/blob/main/fixos/config.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `FixOsConfig` | 3 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L179) |

**`FixOsConfig` methods:**

- `load(cls)` — Tworzy konfigurację z połączonych źródeł.
- `validate()` — Zwraca listę błędów walidacji (pusta = OK).
- `summary()` — Krótkie podsumowanie konfiguracji (bez klucza API).

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `detect_provider_from_key` | `detect_provider_from_key(key)` | 3 | Wykrywa provider na podstawie prefiksu klucza API. | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L429) |
| `get_providers_list` | `get_providers_list()` | 3 | Zwraca listę providerów jako listę słowników. | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L448) |
| `interactive_provider_setup` | `interactive_provider_setup()` | 1 | Interaktywny wybór providera gdy brak konfiguracji. | [source](https://github.com/semcod/fixos/blob/main/fixos/config.py#L437) |

### `fixos.config_interactive` [source](https://github.com/semcod/fixos/blob/main/fixos/config_interactive.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `interactive_provider_setup` | `interactive_provider_setup()` | 5 | Interaktywny wybór providera gdy brak konfiguracji. | [source](https://github.com/semcod/fixos/blob/main/fixos/config_interactive.py#L121) |

### `fixos.diagnostics` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `DevProjectAnalyzer` | 5 | Analyze developer projects for dependency folders that can be cleaned. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L69) |
| `ProjectDependency` | 1 | Represents a dependency folder that can be cleaned | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L32) |
| `DiskAnalyzer` | 6 | Analyzes disk usage and provides cleanup suggestions | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L27) |
| `DockerNetworkCleaner` | 3 | Usuwa wyłącznie sieci bez endpointów i testuje pulę adresową. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_network_cleanup.py#L19) |
| `DockerStartupOptimizer` | 2 | Find and explicitly disable stale repository-backed Docker autostart. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_startup_optimizer.py#L31) |
| `FlatpakAnalyzer` | 1 | Advanced analyzer for Flatpak cleanup decisions | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L76) |
| `FlatpakItemInfo` | 1 | Detailed info about a Flatpak item (app, runtime, or data) | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L34) |
| `FlatpakItemType` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L27) |
| `JetBrainsAiControl` | 5 | Inspect or explicitly disable AI plugins and stop exact Qoder helpers. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L29) |
| `JetBrainsAiSafetyError` | 0 | Raised when an AI-control target cannot be proven exact and safe. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L25) |
| `EdtThreadState` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L83) |
| `JetBrainsDiagnosis` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L118) |
| `JetBrainsLogSignals` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L98) |
| `JetBrainsMetrics` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L61) |
| `JetBrainsRecovery` | 3 | Correlate JetBrains evidence and optionally run a bounded JVM GC. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L315) |
| `JetBrainsRecoveryResult` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L133) |
| `JetBrainsRecoverySafetyError` | 0 | Raised when a recovery request cannot be proven safe and applicable. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L56) |
| `JvmHeapInfo` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L71) |
| `OrphanedWorkloadCleaner` | 2 | Find and explicitly clean missing-project Docker and process workloads. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L45) |
| `OrphanedWorkloadSafetyError` | 0 | Raised when an exact cleanup target no longer satisfies safety checks. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L41) |
| `FileLockWait` | 0 | One kernel-reported file-lock dependency. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L74) |
| `ProcessChainFinding` | 2 | A fresh process subtree and the evidence associated with it. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L84) |
| `ProcessChainInspector` | 4 | List, analyse and explicitly terminate recent process subtrees. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L261) |
| `ProcessChainSafetyError` | 0 | Raised when a requested process-tree action fails a safety check. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L29) |
| `ProcessRecord` | 3 | Stable process metadata captured at one point in time. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L34) |
| `TerminationResult` | 1 | Result of a dry run or an attempted tree termination. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L119) |
| `ProjectArtifact` | 0 | A single removable artifact directory found inside a project. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L82) |
| `CacheRule` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L30) |
| `ServiceCleaner` | 19 | Plans and executes cleanup of service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_cleanup.py#L29) |
| `ServiceDetailsProvider` | 1 | Provides detailed information about service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_details.py#L19) |
| `RiskLevel` | 0 | How risky it is to delete a scanned service's data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L98) |
| `ServiceDataInfo` | 0 | Information about service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L116) |
| `ServiceDataScanner` | 5 | Scans for large service data directories and allows cleanup. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L135) |
| `ServiceType` | 0 | Service types that can be scanned and cleaned. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L26) |
| `StorageAnalyzer` | 2 | Comprehensive storage analyzer for Linux systems. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L59) |
| `StorageItem` | 1 | Represents a storage item that can be cleaned | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L25) |

**`DevProjectAnalyzer` methods:**

- `analyze(max_depth)` — Scan home directory for dependency folders.
- `get_old_dependencies(days)` — Get dependencies not modified in X days
- `get_large_dependencies(min_size_mb)` — Get dependencies larger than X MB
- `get_summary()` — Get human-readable summary
- `get_cleanup_commands()` — Get cleanup commands for each dependency

**`DiskAnalyzer` methods:**

- `analyze_disk_usage(path)` — Comprehensive disk usage analysis
- `get_large_files(path, min_size_mb, max_files)` — Find large files
- `get_cache_dirs(path, max_dirs)` — Find cache directories
- `get_log_dirs(path, max_dirs)` — Find log directories
- `get_temp_dirs(path, max_dirs)` — Find temporary directories
- `suggest_cleanup_actions(path)` — Generate cleanup suggestions using heuristics

**`DockerNetworkCleaner` methods:**

- `list_unused(min_age_days)` — Zwróć niestandardowe sieci bez endpointów.
- `probe_address_pool()` — Utwórz i usuń tymczasową sieć, potwierdzając dostępność puli.
- `cleanup()` — Usuń dokładnie wykryte sieci i opcjonalnie sprawdź pulę adresową.

**`DockerStartupOptimizer` methods:**

- `scan(min_inactive_days)` — Return evidence and stale candidates without changing Docker state.
- `optimize(container_ids)` — Disable exact stale candidates and optionally stop them.

**`JetBrainsAiControl` methods:**

- `find_qoder_helpers(records)`
- `find_config_dirs(records, explicit)`
- `status()`
- `disable_plugins(config_dir)`
- `stop_qoder_helpers(identities)`

**`JetBrainsRecovery` methods:**

- `find_main_processes(records)`
- `diagnose(pid)`
- `recover(diagnosis)` — Optionally run ``GC.run`` and verify evidence without closing the IDE.

**`OrphanedWorkloadCleaner` methods:**

- `scan()` — Return exact orphan evidence without changing Docker or processes.
- `cleanup()` — Revalidate and apply only exact selected orphan candidates.

**`ProcessChainInspector` methods:**

- `snapshot()`
- `list_recent()` — Return newest processes first, without classifying them as blockers.
- `find_suspicious_chains()` — Reconstruct fresh trees and attach explainable blocking evidence.
- `terminate_chain(finding)` — Terminate one selected tree after identity and ancestry checks.

**`ProcessRecord` methods:**

- `age_seconds(now)`
- `to_dict()`

**`ServiceCleaner` methods:**

- `docker_old_unused_until_hours(days)` — Convert a positive day count to Docker ``until=<Nh>`` hours.
- `get_docker_old_unused_command(days)` — Bounded prune: unused images (and old build cache) older than N days.
- `list_ollama_models()` — Return installed Ollama models with name/size/modified_at (UTC).
- `list_running_ollama_models()` — Names of models currently loaded in memory (must not be deleted).
- `select_old_ollama_models(models, days)` — Filter models whose modified_at is older than N days; skip running ones.
- `cleanup_ollama_old_unused(days, dry_run)` — Remove Ollama models not modified for more than N days (skip running).
- `get_docker_unused_command()` — Prune all unused images and rebuildable build cache (no age filter).
- `cleanup_docker_unused(dry_run)` — Remove unused images/cache and optionally orphaned networks.
- `cleanup_docker_networks(days, dry_run)` — Remove unused custom networks and verify Docker address-pool allocation.
- `cleanup_docker_old_unused(days, dry_run)` — Remove old images/cache and optionally orphaned networks.
- `build_safe_age_actions(selected_services)` — Bounded age-based cleanups treated as safe (option [1] in interactive cleanup).
- `get_cleanup_plan(selected_services)` — Generate cleanup plan for services, split into 3 risk tiers.
- `cleanup_service(service_type, dry_run, planned_service)` — Execute cleanup for a specific service or exact planned entry.
- `get_risk_level(service_type, path)` — Classify cleanup risk for a service path.
- `is_safe_cleanup(service_type, path)` — Backward-compatible bool view of get_risk_level() == SAFE.
- `get_cleanup_hints(service_type, size_gb)` — Get helpful hints for cleaning services that require manual review.
- `get_service_description(service_type)` — Get description for service type.
- `get_cleanup_command(service_type, path)` — Get a bounded cleanup command for a scanned service path.
- `get_preview_command(service_type, path)` — Get preview command for service.

**`ServiceDataScanner` methods:**

- `scan_all_services()` — Scan all known services for data above threshold.
- `scan_service(service_type)` — Scan specific service type for data.
- `measure_service_size_mb(service_type, path)` — Measure a service with the same source before and after cleanup.
- `get_cleanup_plan(selected_services)` — Generate cleanup plan for services.
- `cleanup_service(service_type, dry_run, planned_service)` — Execute cleanup for a specific service.

**`StorageAnalyzer` methods:**

- `analyze_full()` — Run full system storage analysis
- `get_summary()` — Get human-readable summary

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `discover_additional_caches` | `discover_additional_caches(get_size_mb, threshold_mb, covered_paths)` | 5 | Discover large caches not already covered by known service scanners. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L109) |
| `is_generic_cache_safe` | `is_generic_cache_safe(path)` | 2 | Heuristic safety check for unknown cache directories. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L103) |
| `normalize_path` | `normalize_path(path)` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L85) |
| `path_is_covered` | `path_is_covered(path, covered_paths)` | 5 | Return True when path is already represented by a known service scan. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L89) |
| `diagnose_audio` | `diagnose_audio()` | 1 | Diagnostyka dźwięku (ALSA/PipeWire/PulseAudio/SOF). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/audio.py#L11) |
| `diagnose_files` | `diagnose_files()` | 4 | Diagnostyka plików użytkownika. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/file_analysis.py#L17) |
| `diagnose_hardware` | `diagnose_hardware()` | 1 | Diagnostyka sprzętu laptopa/desktopa (ACPI, kamera, touchpad, DMI). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/hardware.py#L10) |
| `diagnose_packages` | `diagnose_packages()` | 4 | Diagnostyka zainstalowanych pakietów i środowiska. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/packages.py#L18) |
| `diagnose_resources` | `diagnose_resources()` | 13 ⚠️ | Diagnostyka zasobów systemowych. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/resources.py#L24) |
| `diagnose_security` | `diagnose_security()` | 4 | Diagnostyka bezpieczeństwa systemu i sieci. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/security.py#L18) |
| `diagnose_storage` | `diagnose_storage()` | 4 | Diagnostyka optymalizacji dysków i partycji. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/storage_optimization.py#L11) |
| `diagnose_system` | `diagnose_system()` | 11 ⚠️ | System metrics – cross-platform: CPU, RAM, disks, processes. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/system_core.py#L96) |
| `diagnose_thumbnails` | `diagnose_thumbnails()` | 1 | Diagnostyka podglądów plików (thumbnails) w system. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/thumbnails.py#L10) |
| `main` | `main()` | 1 | Test the disk analyzer | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L487) |
| `analyze_flatpak_for_cleanup` | `analyze_flatpak_for_cleanup()` | 1 | Convenience function to run full Flatpak analysis | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L163) |
| `analyze_idea_log` | `analyze_idea_log(text)` | 15 ⚠️ | Extract bounded, explainable stall signals from JetBrains log text. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L171) |
| `collect_jetbrains_metrics` | `collect_jetbrains_metrics(pid)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L294) |
| `is_main_jetbrains_process` | `is_main_jetbrains_process(process)` | 1 | Return true only for a main IDE process, never a helper/server. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L148) |
| `jetbrains_product_marker` | `jetbrains_product_marker(process)` | 9 | Identify a product only from its launcher, never arbitrary arguments. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L154) |
| `parse_edt_thread` | `parse_edt_thread(text)` | 7 | Extract the AWT event-dispatch thread from a ``Thread.print`` result. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L246) |
| `parse_heap_info` | `parse_heap_info(text)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L236) |
| `read_log_since` | `read_log_since(path, offset)` | 3 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L283) |
| `read_log_tail` | `read_log_tail(path)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L273) |
| `collect_processes` | `collect_processes()` | 13 ⚠️ | Collect a best-effort process snapshot using the existing psutil dependency. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L135) |
| `parse_proc_locks` | `parse_proc_locks(text)` | 8 | Parse blocked lock requests from Linux ``/proc/locks`` content. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L172) |
| `read_linux_lock_waits` | `read_linux_lock_waits(path)` | 2 | Read Linux lock dependencies; return no evidence on other/denied systems. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L210) |
| `discover_project_roots` | `discover_project_roots(base, max_depth)` | 9 | Find developer project roots under `base` (dirs carrying a known | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L143) |
| `find_duplicate_venvs` | `find_duplicate_venvs(artifacts)` | 5 | Project paths that carry more than one virtualenv-type artifact at | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L235) |
| `scan_all` | `scan_all(base, threshold_mb, stale_days, max_depth)` | 2 | Scan every project under `base` for removable artifacts, largest first. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L221) |
| `scan_project_artifacts` | `scan_project_artifacts(project_root, threshold_mb, stale_days)` | 7 | Find removable artifacts directly under a single project root. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L174) |
| `summarize` | `summarize(artifacts)` | 9 | Aggregate stats used for the CLI summary header. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L245) |
| `collect_quick_snapshot` | `collect_quick_snapshot()` | 7 | Collect a bounded, heuristic snapshot without using an LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L784) |
| `main` | `main()` | 1 | Test the service data scanner. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L665) |
| `get_full_diagnostics` | `get_full_diagnostics(modules, progress_callback)` | 12 ⚠️ | Zbiera diagnostykę z wybranych modułów. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/system_checks.py#L49) |
| `format_size` | `format_size(size_bytes)` | 3 | Format bytes to human-readable string (B/KB/MB/GB/TB/PB). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/utils.py#L6) |

### `fixos.diagnostics.cache_discovery` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `discover_additional_caches` | `discover_additional_caches(get_size_mb, threshold_mb, covered_paths)` | 5 | Discover large caches not already covered by known service scanners. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L109) |
| `is_generic_cache_safe` | `is_generic_cache_safe(path)` | 2 | Heuristic safety check for unknown cache directories. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L103) |
| `normalize_path` | `normalize_path(path)` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L85) |
| `path_is_covered` | `path_is_covered(path, covered_paths)` | 5 | Return True when path is already represented by a known service scan. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/cache_discovery.py#L89) |

### `fixos.diagnostics.checks.audio` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/audio.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_audio` | `diagnose_audio()` | 1 | Diagnostyka dźwięku (ALSA/PipeWire/PulseAudio/SOF). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/audio.py#L11) |

### `fixos.diagnostics.checks.file_analysis` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/file_analysis.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_files` | `diagnose_files()` | 4 | Diagnostyka plików użytkownika. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/file_analysis.py#L17) |

### `fixos.diagnostics.checks.hardware` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/hardware.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_hardware` | `diagnose_hardware()` | 1 | Diagnostyka sprzętu laptopa/desktopa (ACPI, kamera, touchpad, DMI). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/hardware.py#L10) |

### `fixos.diagnostics.checks.packages` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/packages.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_packages` | `diagnose_packages()` | 4 | Diagnostyka zainstalowanych pakietów i środowiska. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/packages.py#L18) |

### `fixos.diagnostics.checks.resources` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/resources.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_resources` | `diagnose_resources()` | 13 ⚠️ | Diagnostyka zasobów systemowych. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/resources.py#L24) |

### `fixos.diagnostics.checks.security` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/security.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_security` | `diagnose_security()` | 4 | Diagnostyka bezpieczeństwa systemu i sieci. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/security.py#L18) |

### `fixos.diagnostics.checks.storage_optimization` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/storage_optimization.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_storage` | `diagnose_storage()` | 4 | Diagnostyka optymalizacji dysków i partycji. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/storage_optimization.py#L11) |

### `fixos.diagnostics.checks.system_core` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/system_core.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_system` | `diagnose_system()` | 11 ⚠️ | System metrics – cross-platform: CPU, RAM, disks, processes. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/system_core.py#L96) |

### `fixos.diagnostics.checks.thumbnails` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/thumbnails.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `diagnose_thumbnails` | `diagnose_thumbnails()` | 1 | Diagnostyka podglądów plików (thumbnails) w system. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/checks/thumbnails.py#L10) |

### `fixos.diagnostics.dev_project_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `DevProjectAnalyzer` | 5 | Analyze developer projects for dependency folders that can be cleaned. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L69) |
| `ProjectDependency` | 1 | Represents a dependency folder that can be cleaned | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/dev_project_analyzer.py#L32) |

**`DevProjectAnalyzer` methods:**

- `analyze(max_depth)` — Scan home directory for dependency folders.
- `get_old_dependencies(days)` — Get dependencies not modified in X days
- `get_large_dependencies(min_size_mb)` — Get dependencies larger than X MB
- `get_summary()` — Get human-readable summary
- `get_cleanup_commands()` — Get cleanup commands for each dependency

### `fixos.diagnostics.disk_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `DiskAnalyzer` | 6 | Analyzes disk usage and provides cleanup suggestions | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L27) |

**`DiskAnalyzer` methods:**

- `analyze_disk_usage(path)` — Comprehensive disk usage analysis
- `get_large_files(path, min_size_mb, max_files)` — Find large files
- `get_cache_dirs(path, max_dirs)` — Find cache directories
- `get_log_dirs(path, max_dirs)` — Find log directories
- `get_temp_dirs(path, max_dirs)` — Find temporary directories
- `suggest_cleanup_actions(path)` — Generate cleanup suggestions using heuristics

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `main` | `main()` | 1 | Test the disk analyzer | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/disk_analyzer.py#L487) |

### `fixos.diagnostics.docker_network_cleanup` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_network_cleanup.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `DockerNetworkCleaner` | 3 | Usuwa wyłącznie sieci bez endpointów i testuje pulę adresową. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_network_cleanup.py#L19) |

**`DockerNetworkCleaner` methods:**

- `list_unused(min_age_days)` — Zwróć niestandardowe sieci bez endpointów.
- `probe_address_pool()` — Utwórz i usuń tymczasową sieć, potwierdzając dostępność puli.
- `cleanup()` — Usuń dokładnie wykryte sieci i opcjonalnie sprawdź pulę adresową.

### `fixos.diagnostics.docker_startup_optimizer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_startup_optimizer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `DockerStartupOptimizer` | 2 | Find and explicitly disable stale repository-backed Docker autostart. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/docker_startup_optimizer.py#L31) |

**`DockerStartupOptimizer` methods:**

- `scan(min_inactive_days)` — Return evidence and stale candidates without changing Docker state.
- `optimize(container_ids)` — Disable exact stale candidates and optionally stop them.

### `fixos.diagnostics.flatpak_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `FlatpakAnalyzer` | 1 | Advanced analyzer for Flatpak cleanup decisions | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L76) |
| `FlatpakItemInfo` | 1 | Detailed info about a Flatpak item (app, runtime, or data) | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L34) |
| `FlatpakItemType` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L27) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `analyze_flatpak_for_cleanup` | `analyze_flatpak_for_cleanup()` | 1 | Convenience function to run full Flatpak analysis | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/flatpak_analyzer.py#L163) |

### `fixos.diagnostics.jetbrains_ai` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `JetBrainsAiControl` | 5 | Inspect or explicitly disable AI plugins and stop exact Qoder helpers. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L29) |
| `JetBrainsAiSafetyError` | 0 | Raised when an AI-control target cannot be proven exact and safe. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_ai.py#L25) |

**`JetBrainsAiControl` methods:**

- `find_qoder_helpers(records)`
- `find_config_dirs(records, explicit)`
- `status()`
- `disable_plugins(config_dir)`
- `stop_qoder_helpers(identities)`

### `fixos.diagnostics.jetbrains_recovery` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `EdtThreadState` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L83) |
| `JetBrainsDiagnosis` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L118) |
| `JetBrainsLogSignals` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L98) |
| `JetBrainsMetrics` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L61) |
| `JetBrainsRecovery` | 3 | Correlate JetBrains evidence and optionally run a bounded JVM GC. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L315) |
| `JetBrainsRecoveryResult` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L133) |
| `JetBrainsRecoverySafetyError` | 0 | Raised when a recovery request cannot be proven safe and applicable. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L56) |
| `JvmHeapInfo` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L71) |

**`JetBrainsRecovery` methods:**

- `find_main_processes(records)`
- `diagnose(pid)`
- `recover(diagnosis)` — Optionally run ``GC.run`` and verify evidence without closing the IDE.

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `analyze_idea_log` | `analyze_idea_log(text)` | 15 ⚠️ | Extract bounded, explainable stall signals from JetBrains log text. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L171) |
| `collect_jetbrains_metrics` | `collect_jetbrains_metrics(pid)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L294) |
| `is_main_jetbrains_process` | `is_main_jetbrains_process(process)` | 1 | Return true only for a main IDE process, never a helper/server. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L148) |
| `jetbrains_product_marker` | `jetbrains_product_marker(process)` | 9 | Identify a product only from its launcher, never arbitrary arguments. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L154) |
| `parse_edt_thread` | `parse_edt_thread(text)` | 7 | Extract the AWT event-dispatch thread from a ``Thread.print`` result. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L246) |
| `parse_heap_info` | `parse_heap_info(text)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L236) |
| `read_log_since` | `read_log_since(path, offset)` | 3 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L283) |
| `read_log_tail` | `read_log_tail(path)` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/jetbrains_recovery.py#L273) |

### `fixos.diagnostics.orphaned_workloads` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `OrphanedWorkloadCleaner` | 2 | Find and explicitly clean missing-project Docker and process workloads. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L45) |
| `OrphanedWorkloadSafetyError` | 0 | Raised when an exact cleanup target no longer satisfies safety checks. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/orphaned_workloads.py#L41) |

**`OrphanedWorkloadCleaner` methods:**

- `scan()` — Return exact orphan evidence without changing Docker or processes.
- `cleanup()` — Revalidate and apply only exact selected orphan candidates.

### `fixos.diagnostics.process_chains` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `FileLockWait` | 0 | One kernel-reported file-lock dependency. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L74) |
| `ProcessChainFinding` | 2 | A fresh process subtree and the evidence associated with it. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L84) |
| `ProcessChainInspector` | 4 | List, analyse and explicitly terminate recent process subtrees. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L261) |
| `ProcessChainSafetyError` | 0 | Raised when a requested process-tree action fails a safety check. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L29) |
| `ProcessRecord` | 3 | Stable process metadata captured at one point in time. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L34) |
| `TerminationResult` | 1 | Result of a dry run or an attempted tree termination. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L119) |

**`ProcessChainInspector` methods:**

- `snapshot()`
- `list_recent()` — Return newest processes first, without classifying them as blockers.
- `find_suspicious_chains()` — Reconstruct fresh trees and attach explainable blocking evidence.
- `terminate_chain(finding)` — Terminate one selected tree after identity and ancestry checks.

**`ProcessRecord` methods:**

- `age_seconds(now)`
- `to_dict()`

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `collect_processes` | `collect_processes()` | 13 ⚠️ | Collect a best-effort process snapshot using the existing psutil dependency. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L135) |
| `parse_proc_locks` | `parse_proc_locks(text)` | 8 | Parse blocked lock requests from Linux ``/proc/locks`` content. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L172) |
| `read_linux_lock_waits` | `read_linux_lock_waits(path)` | 2 | Read Linux lock dependencies; return no evidence on other/denied systems. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/process_chains.py#L210) |

### `fixos.diagnostics.project_scanner` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `ProjectArtifact` | 0 | A single removable artifact directory found inside a project. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L82) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `discover_project_roots` | `discover_project_roots(base, max_depth)` | 9 | Find developer project roots under `base` (dirs carrying a known | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L143) |
| `find_duplicate_venvs` | `find_duplicate_venvs(artifacts)` | 5 | Project paths that carry more than one virtualenv-type artifact at | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L235) |
| `scan_all` | `scan_all(base, threshold_mb, stale_days, max_depth)` | 2 | Scan every project under `base` for removable artifacts, largest first. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L221) |
| `scan_project_artifacts` | `scan_project_artifacts(project_root, threshold_mb, stale_days)` | 7 | Find removable artifacts directly under a single project root. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L174) |
| `summarize` | `summarize(artifacts)` | 9 | Aggregate stats used for the CLI summary header. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/project_scanner.py#L245) |

### `fixos.diagnostics.quick_snapshot` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `CacheRule` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L30) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `collect_quick_snapshot` | `collect_quick_snapshot()` | 7 | Collect a bounded, heuristic snapshot without using an LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/quick_snapshot.py#L784) |

### `fixos.diagnostics.service_cleanup` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_cleanup.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `ServiceCleaner` | 19 | Plans and executes cleanup of service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_cleanup.py#L29) |

**`ServiceCleaner` methods:**

- `docker_old_unused_until_hours(days)` — Convert a positive day count to Docker ``until=<Nh>`` hours.
- `get_docker_old_unused_command(days)` — Bounded prune: unused images (and old build cache) older than N days.
- `list_ollama_models()` — Return installed Ollama models with name/size/modified_at (UTC).
- `list_running_ollama_models()` — Names of models currently loaded in memory (must not be deleted).
- `select_old_ollama_models(models, days)` — Filter models whose modified_at is older than N days; skip running ones.
- `cleanup_ollama_old_unused(days, dry_run)` — Remove Ollama models not modified for more than N days (skip running).
- `get_docker_unused_command()` — Prune all unused images and rebuildable build cache (no age filter).
- `cleanup_docker_unused(dry_run)` — Remove unused images/cache and optionally orphaned networks.
- `cleanup_docker_networks(days, dry_run)` — Remove unused custom networks and verify Docker address-pool allocation.
- `cleanup_docker_old_unused(days, dry_run)` — Remove old images/cache and optionally orphaned networks.
- `build_safe_age_actions(selected_services)` — Bounded age-based cleanups treated as safe (option [1] in interactive cleanup).
- `get_cleanup_plan(selected_services)` — Generate cleanup plan for services, split into 3 risk tiers.
- `cleanup_service(service_type, dry_run, planned_service)` — Execute cleanup for a specific service or exact planned entry.
- `get_risk_level(service_type, path)` — Classify cleanup risk for a service path.
- `is_safe_cleanup(service_type, path)` — Backward-compatible bool view of get_risk_level() == SAFE.
- `get_cleanup_hints(service_type, size_gb)` — Get helpful hints for cleaning services that require manual review.
- `get_service_description(service_type)` — Get description for service type.
- `get_cleanup_command(service_type, path)` — Get a bounded cleanup command for a scanned service path.
- `get_preview_command(service_type, path)` — Get preview command for service.

### `fixos.diagnostics.service_details` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_details.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `ServiceDetailsProvider` | 1 | Provides detailed information about service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_details.py#L19) |

### `fixos.diagnostics.service_scanner` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `RiskLevel` | 0 | How risky it is to delete a scanned service's data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L98) |
| `ServiceDataInfo` | 0 | Information about service data. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L116) |
| `ServiceDataScanner` | 5 | Scans for large service data directories and allows cleanup. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L135) |
| `ServiceType` | 0 | Service types that can be scanned and cleaned. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L26) |

**`ServiceDataScanner` methods:**

- `scan_all_services()` — Scan all known services for data above threshold.
- `scan_service(service_type)` — Scan specific service type for data.
- `measure_service_size_mb(service_type, path)` — Measure a service with the same source before and after cleanup.
- `get_cleanup_plan(selected_services)` — Generate cleanup plan for services.
- `cleanup_service(service_type, dry_run, planned_service)` — Execute cleanup for a specific service.

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `main` | `main()` | 1 | Test the service data scanner. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/service_scanner.py#L665) |

### `fixos.diagnostics.storage_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `StorageAnalyzer` | 2 | Comprehensive storage analyzer for Linux systems. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L59) |
| `StorageItem` | 1 | Represents a storage item that can be cleaned | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/storage_analyzer.py#L25) |

**`StorageAnalyzer` methods:**

- `analyze_full()` — Run full system storage analysis
- `get_summary()` — Get human-readable summary

### `fixos.diagnostics.system_checks` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/system_checks.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `get_full_diagnostics` | `get_full_diagnostics(modules, progress_callback)` | 12 ⚠️ | Zbiera diagnostykę z wybranych modułów. | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/system_checks.py#L49) |

### `fixos.diagnostics.utils` [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/utils.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `format_size` | `format_size(size_bytes)` | 3 | Format bytes to human-readable string (B/KB/MB/GB/TB/PB). | [source](https://github.com/semcod/fixos/blob/main/fixos/diagnostics/utils.py#L6) |

### `fixos.features` [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `SystemDetector` | 1 | Detects system parameters. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py#L51) |
| `SystemInfo` | 0 | Complete system information snapshot. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/__init__.py#L16) |
| `AuditResult` | 3 | Result of feature audit - what's installed, what's missing. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L15) |
| `FeatureAuditor` | 1 | Compares installed packages with profile requirements. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L53) |
| `PackageCatalog` | 4 | Manages the package database. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L57) |
| `PackageCategory` | 0 | A category of packages (e.g., core_utils, dev_tools). | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L48) |
| `PackageInfo` | 2 | Information about a single package. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L12) |
| `FeatureInstaller` | 2 | Safely installs packages using native package manager or other backends. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/installer.py#L13) |
| `UserProfile` | 4 | A user profile defining what packages/features they want. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/profiles.py#L14) |
| `FeatureRenderer` | 3 | Renders audit results for terminal display. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/renderer.py#L17) |

**`PackageCatalog` methods:**

- `load(cls, data_dir)` — Load package catalog from YAML files.
- `get_package(pkg_id)` — Get package by ID.
- `get_packages_by_category(category)` — Get all packages in a category.
- `list_categories()` — List all category IDs.

**`PackageInfo` methods:**

- `get_distro_name(distro)` — Get package name for specific distro.
- `is_available_on(distro)` — Check if package is available on given distro.

**`FeatureInstaller` methods:**

- `install(packages)` — Install a list of packages.
- `get_rollback_commands(installed_packages)` — Generate rollback commands for installed packages.

**`UserProfile` methods:**

- `load(cls, profile_name, data_dir)` — Load a profile from YAML file.
- `list_available(cls, data_dir)` — List available profile names.
- `resolve_packages(catalog, system_info)` — Resolve all packages for this profile based on system.
- `to_dict()` — Convert to dictionary.

**`FeatureRenderer` methods:**

- `render_audit(result)` — Render complete audit results.
- `render_package_list(packages, title)` — Render a list of packages.
- `render_system_info(system)` — Render system information.

### `fixos.features.auditor` [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `AuditResult` | 3 | Result of feature audit - what's installed, what's missing. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L15) |
| `FeatureAuditor` | 1 | Compares installed packages with profile requirements. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/auditor.py#L53) |

### `fixos.features.catalog` [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `PackageCatalog` | 4 | Manages the package database. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L57) |
| `PackageCategory` | 0 | A category of packages (e.g., core_utils, dev_tools). | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L48) |
| `PackageInfo` | 2 | Information about a single package. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/catalog.py#L12) |

**`PackageCatalog` methods:**

- `load(cls, data_dir)` — Load package catalog from YAML files.
- `get_package(pkg_id)` — Get package by ID.
- `get_packages_by_category(category)` — Get all packages in a category.
- `list_categories()` — List all category IDs.

**`PackageInfo` methods:**

- `get_distro_name(distro)` — Get package name for specific distro.
- `is_available_on(distro)` — Check if package is available on given distro.

### `fixos.features.installer` [source](https://github.com/semcod/fixos/blob/main/fixos/features/installer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `FeatureInstaller` | 2 | Safely installs packages using native package manager or other backends. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/installer.py#L13) |

**`FeatureInstaller` methods:**

- `install(packages)` — Install a list of packages.
- `get_rollback_commands(installed_packages)` — Generate rollback commands for installed packages.

### `fixos.features.profiles` [source](https://github.com/semcod/fixos/blob/main/fixos/features/profiles.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `UserProfile` | 4 | A user profile defining what packages/features they want. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/profiles.py#L14) |

**`UserProfile` methods:**

- `load(cls, profile_name, data_dir)` — Load a profile from YAML file.
- `list_available(cls, data_dir)` — List available profile names.
- `resolve_packages(catalog, system_info)` — Resolve all packages for this profile based on system.
- `to_dict()` — Convert to dictionary.

### `fixos.features.renderer` [source](https://github.com/semcod/fixos/blob/main/fixos/features/renderer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `FeatureRenderer` | 3 | Renders audit results for terminal display. | [source](https://github.com/semcod/fixos/blob/main/fixos/features/renderer.py#L17) |

**`FeatureRenderer` methods:**

- `render_audit(result)` — Render complete audit results.
- `render_package_list(packages, title)` — Render a list of packages.
- `render_system_info(system)` — Render system information.

### `fixos.interactive` [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `CleanupAction` | 0 | Represents a cleanup action | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L32) |
| `CleanupPlanner` | 4 | Interactive cleanup planning and grouping system | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L53) |
| `CleanupType` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L20) |
| `Priority` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L13) |

**`CleanupPlanner` methods:**

- `group_by_category(suggestions)` — Group cleanup suggestions by category
- `prioritize_actions(grouped_actions)` — Create prioritized list of all actions
- `create_cleanup_plan(suggestions)` — Create comprehensive cleanup plan
- `interactive_selection(plan)` — Interactive selection process (simulated for now)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `main` | `main()` | 1 | Test the cleanup planner | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L437) |

### `fixos.interactive.cleanup_planner` [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `CleanupAction` | 0 | Represents a cleanup action | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L32) |
| `CleanupPlanner` | 4 | Interactive cleanup planning and grouping system | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L53) |
| `CleanupType` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L20) |
| `Priority` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L13) |

**`CleanupPlanner` methods:**

- `group_by_category(suggestions)` — Group cleanup suggestions by category
- `prioritize_actions(grouped_actions)` — Create prioritized list of all actions
- `create_cleanup_plan(suggestions)` — Create comprehensive cleanup plan
- `interactive_selection(plan)` — Interactive selection process (simulated for now)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `main` | `main()` | 1 | Test the cleanup planner | [source](https://github.com/semcod/fixos/blob/main/fixos/interactive/cleanup_planner.py#L437) |

### `fixos.llm_shell` [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `execute_command` | `execute_command(cmd)` | 10 | Wykonuje komendę systemową z potwierdzeniem użytkownika. | [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L67) |
| `format_time` | `format_time(seconds)` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L59) |
| `run_llm_shell` | `run_llm_shell(diagnostics_data, token, model, timeout, ...)` | 8 | Uruchamia interaktywny shell LLM z przekazanymi danymi diagnostycznymi. | [source](https://github.com/semcod/fixos/blob/main/fixos/llm_shell.py#L175) |

### `fixos.orchestrator` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `CommandExecutor` | 6 | Bezpieczny executor komend z: | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L113) |
| `CommandTimeoutError` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L24) |
| `DangerousCommandError` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L15) |
| `ExecutionResult` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L32) |
| `Problem` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L19) |
| `ProblemGraph` | 7 | DAG problemów systemowych z topological sort do wyznaczania kolejności napraw. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L46) |
| `FixOrchestrator` | 4 | Orkiestrator napraw systemowych. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/orchestrator.py#L91) |
| `RollbackEntry` | 0 | Single recorded operation with its rollback command. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L20) |
| `RollbackSession` | 5 | A session of recorded operations that can be rolled back. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L33) |

**`CommandExecutor` methods:**

- `is_dangerous(command)` — Sprawdza czy komenda jest potencjalnie destruktywna.
- `needs_sudo(command)`
- `add_sudo(command)`
- `check_idempotent(command)` — Zwraca komendę sprawdzającą stan (jeśli znana), None jeśli nie dotyczy.
- `execute_sync(command, timeout, add_sudo, check_idempotent)` — Synchroniczne wykonanie komendy.
- `execute(command, timeout, add_sudo)` — Asynchroniczne wykonanie komendy.

**`Problem` methods:**

- `is_actionable()`
- `to_summary()`

**`ProblemGraph` methods:**

- `add(problem)`
- `get(problem_id)`
- `next_actionable()` — Zwraca pierwszy problem bez nierozwiązanych zależności.
- `all_done()`
- `pending_count()`
- `summary()`
- `render_tree()` — Renderuje drzewo problemów jako tekst.

**`FixOrchestrator` methods:**

- `load_from_diagnostics(diagnostics)` — Parsuje dane diagnostyczne przez LLM i buduje graf problemów.
- `load_from_dict(problems_data)` — Ładuje problemy bezpośrednio z listy dict (bez LLM).
- `run_sync(confirm_fn, progress_fn)` — Synchroniczna pętla napraw (dla trybu HITL).
- `run_async(confirm_fn, progress_fn)` — Asynchroniczna wersja run_sync.

**`RollbackSession` methods:**

- `record(command, rollback_cmd, stdout, stderr, ...)` — Zapisz wykonaną operację.
- `get_rollback_commands()` — Zwraca listę (komenda, rollback) w odwróconej kolejności.
- `rollback_last(n, dry_run)` — Cofnij ostatnich n operacji.
- `load(cls, session_id)` — Załaduj sesję z pliku.
- `list_sessions(cls, limit)` — Lista ostatnich sesji rollback.

### `fixos.orchestrator.executor` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `CommandExecutor` | 6 | Bezpieczny executor komend z: | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L113) |
| `CommandTimeoutError` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L24) |
| `DangerousCommandError` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L15) |
| `ExecutionResult` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/executor.py#L32) |

**`CommandExecutor` methods:**

- `is_dangerous(command)` — Sprawdza czy komenda jest potencjalnie destruktywna.
- `needs_sudo(command)`
- `add_sudo(command)`
- `check_idempotent(command)` — Zwraca komendę sprawdzającą stan (jeśli znana), None jeśli nie dotyczy.
- `execute_sync(command, timeout, add_sudo, check_idempotent)` — Synchroniczne wykonanie komendy.
- `execute(command, timeout, add_sudo)` — Asynchroniczne wykonanie komendy.

### `fixos.orchestrator.graph` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Problem` | 2 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L19) |
| `ProblemGraph` | 7 | DAG problemów systemowych z topological sort do wyznaczania kolejności napraw. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/graph.py#L46) |

**`Problem` methods:**

- `is_actionable()`
- `to_summary()`

**`ProblemGraph` methods:**

- `add(problem)`
- `get(problem_id)`
- `next_actionable()` — Zwraca pierwszy problem bez nierozwiązanych zależności.
- `all_done()`
- `pending_count()`
- `summary()`
- `render_tree()` — Renderuje drzewo problemów jako tekst.

### `fixos.orchestrator.orchestrator` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/orchestrator.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `FixOrchestrator` | 4 | Orkiestrator napraw systemowych. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/orchestrator.py#L91) |

**`FixOrchestrator` methods:**

- `load_from_diagnostics(diagnostics)` — Parsuje dane diagnostyczne przez LLM i buduje graf problemów.
- `load_from_dict(problems_data)` — Ładuje problemy bezpośrednio z listy dict (bez LLM).
- `run_sync(confirm_fn, progress_fn)` — Synchroniczna pętla napraw (dla trybu HITL).
- `run_async(confirm_fn, progress_fn)` — Asynchroniczna wersja run_sync.

### `fixos.orchestrator.rollback` [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `RollbackEntry` | 0 | Single recorded operation with its rollback command. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L20) |
| `RollbackSession` | 5 | A session of recorded operations that can be rolled back. | [source](https://github.com/semcod/fixos/blob/main/fixos/orchestrator/rollback.py#L33) |

**`RollbackSession` methods:**

- `record(command, rollback_cmd, stdout, stderr, ...)` — Zapisz wykonaną operację.
- `get_rollback_commands()` — Zwraca listę (komenda, rollback) w odwróconej kolejności.
- `rollback_last(n, dry_run)` — Cofnij ostatnich n operacji.
- `load(cls, session_id)` — Załaduj sesję z pliku.
- `list_sessions(cls, limit)` — Lista ostatnich sesji rollback.

### `fixos.orphan_pins` [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `OrphanProjectPinError` | 0 | Raised when persistent pin state cannot be trusted. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L18) |
| `OrphanProjectPins` | 4 | Read and atomically update exact Compose working-directory pins. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L42) |

**`OrphanProjectPins` methods:**

- `list()` — Load validated records, failing closed if the state is malformed.
- `paths()` — Return exact normalized paths used by the scanner.
- `pin(value)` — Persist one exact path and report whether state changed.
- `unpin(value)` — Remove one exact path, leaving unrelated pins untouched.

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `default_pin_path` | `default_pin_path()` | 2 | Return the XDG-compliant per-user pin store path. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L34) |
| `normalize_project_path` | `normalize_project_path(value)` | 3 | Return a stable absolute path without requiring the path to exist. | [source](https://github.com/semcod/fixos/blob/main/fixos/orphan_pins.py#L22) |

### `fixos.platform_utils` [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `cancel_signal_timeout` | `cancel_signal_timeout()` | 2 | Cancels the timeout signal (POSIX only). | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L246) |
| `elevate_cmd` | `elevate_cmd(cmd)` | 3 | Adds sudo (Linux/Mac) or wraps in PowerShell -Verb RunAs (Windows). | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L93) |
| `get_os_info` | `get_os_info()` | 5 | Returns basic OS information. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L21) |
| `get_package_manager` | `get_package_manager()` | 8 | Detects the system package manager. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L187) |
| `install_package_cmd` | `install_package_cmd(package)` | 2 | Returns the install command for the detected package manager. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L205) |
| `is_dangerous` | `is_dangerous(cmd)` | 3 | Returns reason string if command is dangerous, None if safe. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L104) |
| `is_interactive_blocker` | `is_interactive_blocker(cmd)` | 3 | Returns reason string if command is likely to hang in non-interactive session. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L127) |
| `needs_elevation` | `needs_elevation(cmd)` | 5 | Returns True if command likely needs admin/sudo. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L44) |
| `run_command` | `run_command(cmd, timeout, shell)` | 5 | Runs a command cross-platform. | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L149) |
| `setup_signal_timeout` | `setup_signal_timeout(seconds, handler)` | 2 | Sets up a timeout signal. Returns True if supported (POSIX only). | [source](https://github.com/semcod/fixos/blob/main/fixos/platform_utils.py#L232) |

### `fixos.plugins` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `DiagnosticPlugin` | 3 | Bazowa klasa dla pluginów diagnostycznych fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L67) |
| `DiagnosticResult` | 1 | Result of a diagnostic plugin run. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L38) |
| `Finding` | 0 | Single finding from a diagnostic plugin. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L26) |
| `Severity` | 0 | Severity level for diagnostic findings. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L16) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py#L9) |
| `PluginRegistry` | 6 | Registry for diagnostic plugins with autodiscovery. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/registry.py#L21) |

**`DiagnosticPlugin` methods:**

- `diagnose()` — Wykonaj diagnostykę i zwróć wynik.
- `can_run()` — Czy plugin może działać na aktualnej platformie?
- `get_metadata()`

**`PluginRegistry` methods:**

- `discover()` — Odkrywanie pluginów przez builtin + entry_points.
- `register(plugin)` — Ręczna rejestracja pluginu.
- `list_plugins(runnable_only)` — Lista zarejestrowanych pluginów.
- `get_plugin(name)` — Pobierz plugin po nazwie.
- `run(modules, progress_callback)` — Uruchom diagnostykę dla wybranych (lub wszystkich) modułów.

### `fixos.plugins.base` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `DiagnosticPlugin` | 3 | Bazowa klasa dla pluginów diagnostycznych fixOS. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L67) |
| `DiagnosticResult` | 1 | Result of a diagnostic plugin run. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L38) |
| `Finding` | 0 | Single finding from a diagnostic plugin. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L26) |
| `Severity` | 0 | Severity level for diagnostic findings. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/base.py#L16) |

**`DiagnosticPlugin` methods:**

- `diagnose()` — Wykonaj diagnostykę i zwróć wynik.
- `can_run()` — Czy plugin może działać na aktualnej platformie?
- `get_metadata()`

### `fixos.plugins.builtin` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py#L9) |
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py#L9) |

### `fixos.plugins.builtin.audio` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/audio.py#L9) |

### `fixos.plugins.builtin.disk` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/disk.py#L9) |

### `fixos.plugins.builtin.hardware` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/hardware.py#L9) |

### `fixos.plugins.builtin.resources` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/resources.py#L9) |

### `fixos.plugins.builtin.security` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/security.py#L9) |

### `fixos.plugins.builtin.thumbnails` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Plugin` | 1 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/builtin/thumbnails.py#L9) |

### `fixos.plugins.registry` [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/registry.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `PluginRegistry` | 6 | Registry for diagnostic plugins with autodiscovery. | [source](https://github.com/semcod/fixos/blob/main/fixos/plugins/registry.py#L21) |

**`PluginRegistry` methods:**

- `discover()` — Odkrywanie pluginów przez builtin + entry_points.
- `register(plugin)` — Ręczna rejestracja pluginu.
- `list_plugins(runnable_only)` — Lista zarejestrowanych pluginów.
- `get_plugin(name)` — Pobierz plugin po nazwie.
- `run(modules, progress_callback)` — Uruchom diagnostykę dla wybranych (lub wszystkich) modułów.

### `fixos.profiles` [source](https://github.com/semcod/fixos/blob/main/fixos/profiles/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `Profile` | 3 | Profil diagnostyczny z zestawem modułów i progów. | [source](https://github.com/semcod/fixos/blob/main/fixos/profiles/__init__.py#L21) |

**`Profile` methods:**

- `load(cls, name)` — Załaduj profil — najpierw user, potem builtin.
- `list_available(cls)` — Lista dostępnych profili (builtin + user).
- `to_dict()`

### `fixos.providers` [source](https://github.com/semcod/fixos/blob/main/fixos/providers/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `LLMClient` | 6 | Wrapper nad openai.OpenAI kompatybilny z wieloma providerami. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L38) |
| `LLMError` | 0 | Błąd komunikacji z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L22) |
| `LLMAnalysis` | 0 | Result of LLM analysis | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L12) |
| `LLMAnalyzer` | 4 | Uses LLM to analyze disk issues when heuristics aren't sufficient | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L21) |
| `CommandValidation` | 0 | Wynik walidacji komendy przez LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L74) |
| `FixSuggestion` | 0 | Pojedyncza sugestia naprawy od LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L21) |
| `LLMDiagnosticResponse` | 0 | Strukturalna odpowiedź LLM na dane diagnostyczne. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L42) |
| `NLPIntent` | 0 | Rozpoznana intencja z polecenia NLP. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L61) |
| `RiskLevel` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L15) |

**`LLMClient` methods:**

- `chat(messages)` — Wysyła wiadomości do LLM i zwraca odpowiedź jako string.
- `chat_stream(messages)` — Generator streamujący tokeny odpowiedzi.
- `chat_structured(messages, response_model)` — Wywołanie LLM z wymuszonym schematem JSON (Pydantic model).
- `ping()` — Sprawdza czy API odpowiada (krótki test).

**`LLMAnalyzer` methods:**

- `analyze_disk_issues(disk_data)` — Use LLM to analyze disk issues when heuristics are insufficient
- `analyze_failed_action(action, error)` — Analyze failed cleanup action and suggest alternatives
- `analyze_complex_pattern(pattern_data)` — Analyze complex disk usage patterns that heuristics can't categorize
- `enhance_heuristics_with_llm(heuristic_suggestions, disk_data)` — Enhance heuristic suggestions with LLM insights

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `main` | `main()` | 1 | Test the LLM analyzer | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L351) |

### `fixos.providers.llm` [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `LLMClient` | 6 | Wrapper nad openai.OpenAI kompatybilny z wieloma providerami. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L38) |
| `LLMError` | 0 | Błąd komunikacji z LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm.py#L22) |

**`LLMClient` methods:**

- `chat(messages)` — Wysyła wiadomości do LLM i zwraca odpowiedź jako string.
- `chat_stream(messages)` — Generator streamujący tokeny odpowiedzi.
- `chat_structured(messages, response_model)` — Wywołanie LLM z wymuszonym schematem JSON (Pydantic model).
- `ping()` — Sprawdza czy API odpowiada (krótki test).

### `fixos.providers.llm_analyzer` [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `LLMAnalysis` | 0 | Result of LLM analysis | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L12) |
| `LLMAnalyzer` | 4 | Uses LLM to analyze disk issues when heuristics aren't sufficient | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L21) |

**`LLMAnalyzer` methods:**

- `analyze_disk_issues(disk_data)` — Use LLM to analyze disk issues when heuristics are insufficient
- `analyze_failed_action(action, error)` — Analyze failed cleanup action and suggest alternatives
- `analyze_complex_pattern(pattern_data)` — Analyze complex disk usage patterns that heuristics can't categorize
- `enhance_heuristics_with_llm(heuristic_suggestions, disk_data)` — Enhance heuristic suggestions with LLM insights

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `main` | `main()` | 1 | Test the LLM analyzer | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/llm_analyzer.py#L351) |

### `fixos.providers.schemas` [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `CommandValidation` | 0 | Wynik walidacji komendy przez LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L74) |
| `FixSuggestion` | 0 | Pojedyncza sugestia naprawy od LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L21) |
| `LLMDiagnosticResponse` | 0 | Strukturalna odpowiedź LLM na dane diagnostyczne. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L42) |
| `NLPIntent` | 0 | Rozpoznana intencja z polecenia NLP. | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L61) |
| `RiskLevel` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/providers/schemas.py#L15) |

### `fixos.system_checks` [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `get_cpu_info` | `get_cpu_info()` | 2 | Metryki CPU. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L28) |
| `get_disk_info` | `get_disk_info()` | 3 | Metryki dysków dla wszystkich partycji. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L56) |
| `get_fedora_specific` | `get_fedora_specific()` | 1 | Komendy specyficzne dla system: dnf, journalctl, systemctl. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L105) |
| `get_full_diagnostics` | `get_full_diagnostics()` | 1 | Zbiera kompletne dane diagnostyczne systemu system. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L140) |
| `get_memory_info` | `get_memory_info()` | 1 | Metryki RAM i SWAP. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L41) |
| `get_network_info` | `get_network_info()` | 4 | Statystyki sieciowe (bez wrażliwych danych - anonimizacja jest osobno). | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L75) |
| `get_top_processes` | `get_top_processes(n)` | 3 | Lista TOP N procesów według zużycia CPU. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L91) |
| `run_cmd` | `run_cmd(cmd, timeout)` | 6 | Uruchamia komendę shell i zwraca output. Bezpieczny fallback przy błędzie. | [source](https://github.com/semcod/fixos/blob/main/fixos/system_checks.py#L12) |

### `fixos.utils` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/__init__.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `AnonymizationContext` | 3 | Memory-only alias state. Never include this object in LLM payloads. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L72) |
| `AnonymizationReport` | 2 | Raport anonimizacji – co zostało zmaskowane. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L112) |
| `ResolutionError` | 0 | Raised when an anonymized alias cannot be resolved safely. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L63) |
| `SessionTimeout` | 0 | Wyjątek rzucany po przekroczeniu limitu czasu sesji. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L10) |
| `SearchResult` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L18) |

**`AnonymizationContext` methods:**

- `bind(category, original, token)`
- `numbered_alias(category, original)`
- `user_alias(username)`

**`AnonymizationReport` methods:**

- `add(category, count)`
- `summary()`

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `anonymize` | `anonymize(data_str, context)` | 7 | Anonimizuje wrażliwe dane. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L272) |
| `deanonymize` | `deanonymize(text, context, allowed_aliases)` | 3 | Resolve aliases locally while preserving the legacy primary tokens. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L360) |
| `display_anonymized_preview` | `display_anonymized_preview(data_str, report, max_lines)` | 5 | Wyświetla użytkownikowi zanonimizowane dane przed wysłaniem do LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L373) |
| `colorize` | `colorize(line)` | 1 | Return line unchanged – rich handles markup in render_md(). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L60) |
| `print_cmd_block` | `print_cmd_block(cmd, comment, dry_run)` | 4 | Print a framed command preview panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L188) |
| `print_problem_header` | `print_problem_header(problem_id, description, severity, status, ...)` | 3 | Print a colored problem header panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L255) |
| `print_stderr_box` | `print_stderr_box(stderr, max_lines)` | 1 | Print stderr in a rich Panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L228) |
| `print_stdout_box` | `print_stdout_box(stdout, max_lines)` | 1 | Print stdout in a rich Panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L223) |
| `render_md` | `render_md(text)` | 9 | Print LLM markdown reply to terminal via rich. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L101) |
| `render_tree_colored` | `render_tree_colored(nodes, execution_order)` | 8 | Render a ProblemGraph as a rich-markup string. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L283) |
| `timeout_handler` | `timeout_handler(signum, frame)` | 1 | Signal handler dla SIGALRM — rzuca SessionTimeout. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L16) |
| `format_results_for_llm` | `format_results_for_llm(results)` | 3 | Formatuje wyniki wyszukiwania do wklejenia w prompt LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L267) |
| `search_all` | `search_all(query, serpapi_key, max_per_source)` | 5 | Przeszukuje wszystkie dostępne źródła wiedzy. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L223) |
| `search_arch_wiki` | `search_arch_wiki(query, max_results)` | 9 | Arch Wiki – doskonałe źródło dla problemów Linux (nie tylko Arch). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L90) |
| `search_ask_fedora` | `search_ask_fedora(query, max_results)` | 4 | Szuka w Linux forums przez Discourse API. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L66) |
| `search_ddg` | `search_ddg(query, max_results)` | 8 | DuckDuckGo Instant Answer API (bez klucza, ograniczone). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L187) |
| `search_fedora_bugzilla` | `search_fedora_bugzilla(query, max_results)` | 4 | Szuka w Linux Bugzilla przez REST API. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L38) |
| `search_github_issues` | `search_github_issues(query, max_results)` | 4 | GitHub Issues – linuxhardware, ALSA, PipeWire, PulseAudio repos. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L120) |
| `search_serpapi` | `search_serpapi(query, api_key, max_results)` | 5 | SerpAPI – Google/Bing search (wymaga klucza API). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L157) |

### `fixos.utils.anonymizer` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `AnonymizationContext` | 3 | Memory-only alias state. Never include this object in LLM payloads. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L72) |
| `AnonymizationReport` | 2 | Raport anonimizacji – co zostało zmaskowane. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L112) |
| `ResolutionError` | 0 | Raised when an anonymized alias cannot be resolved safely. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L63) |

**`AnonymizationContext` methods:**

- `bind(category, original, token)`
- `numbered_alias(category, original)`
- `user_alias(username)`

**`AnonymizationReport` methods:**

- `add(category, count)`
- `summary()`

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `anonymize` | `anonymize(data_str, context)` | 7 | Anonimizuje wrażliwe dane. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L272) |
| `deanonymize` | `deanonymize(text, context, allowed_aliases)` | 3 | Resolve aliases locally while preserving the legacy primary tokens. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L360) |
| `display_anonymized_preview` | `display_anonymized_preview(data_str, report, max_lines)` | 5 | Wyświetla użytkownikowi zanonimizowane dane przed wysłaniem do LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/anonymizer.py#L373) |

### `fixos.utils.terminal` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `colorize` | `colorize(line)` | 1 | Return line unchanged – rich handles markup in render_md(). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L60) |
| `print_cmd_block` | `print_cmd_block(cmd, comment, dry_run)` | 4 | Print a framed command preview panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L188) |
| `print_problem_header` | `print_problem_header(problem_id, description, severity, status, ...)` | 3 | Print a colored problem header panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L255) |
| `print_stderr_box` | `print_stderr_box(stderr, max_lines)` | 1 | Print stderr in a rich Panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L228) |
| `print_stdout_box` | `print_stdout_box(stdout, max_lines)` | 1 | Print stdout in a rich Panel. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L223) |
| `render_md` | `render_md(text)` | 9 | Print LLM markdown reply to terminal via rich. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L101) |
| `render_tree_colored` | `render_tree_colored(nodes, execution_order)` | 8 | Render a ProblemGraph as a rich-markup string. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/terminal.py#L283) |

### `fixos.utils.timeout` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `SessionTimeout` | 0 | Wyjątek rzucany po przekroczeniu limitu czasu sesji. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L10) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `timeout_handler` | `timeout_handler(signum, frame)` | 1 | Signal handler dla SIGALRM — rzuca SessionTimeout. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/timeout.py#L16) |

### `fixos.utils.web_search` [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `SearchResult` | 0 | — | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L18) |

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `format_results_for_llm` | `format_results_for_llm(results)` | 3 | Formatuje wyniki wyszukiwania do wklejenia w prompt LLM. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L267) |
| `search_all` | `search_all(query, serpapi_key, max_per_source)` | 5 | Przeszukuje wszystkie dostępne źródła wiedzy. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L223) |
| `search_arch_wiki` | `search_arch_wiki(query, max_results)` | 9 | Arch Wiki – doskonałe źródło dla problemów Linux (nie tylko Arch). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L90) |
| `search_ask_fedora` | `search_ask_fedora(query, max_results)` | 4 | Szuka w Linux forums przez Discourse API. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L66) |
| `search_ddg` | `search_ddg(query, max_results)` | 8 | DuckDuckGo Instant Answer API (bez klucza, ograniczone). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L187) |
| `search_fedora_bugzilla` | `search_fedora_bugzilla(query, max_results)` | 4 | Szuka w Linux Bugzilla przez REST API. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L38) |
| `search_github_issues` | `search_github_issues(query, max_results)` | 4 | GitHub Issues – linuxhardware, ALSA, PipeWire, PulseAudio repos. | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L120) |
| `search_serpapi` | `search_serpapi(query, api_key, max_results)` | 5 | SerpAPI – Google/Bing search (wymaga klucza API). | [source](https://github.com/semcod/fixos/blob/main/fixos/utils/web_search.py#L157) |

### `fixos.watch` [source](https://github.com/semcod/fixos/blob/main/fixos/watch.py)

| Class | Methods | Description | Source |
|-------|---------|-------------|--------|
| `WatchDaemon` | 2 | Daemon wykonujący cykliczną diagnostykę z powiadomieniami. | [source](https://github.com/semcod/fixos/blob/main/fixos/watch.py#L22) |

**`WatchDaemon` methods:**

- `run()` — Główna pętla monitorowania.
- `stop()` — Zatrzymaj daemon.

## scripts

### `scripts.pyqual-calibrate` [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `calculate_new_threshold` | `calculate_new_threshold(actual_value, current_threshold, margin_percent, is_upper_limit)` | 3 | Wylicza nowy próg z marginesem. | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L81) |
| `calibrate` | `calibrate(workdir, margin, dry_run, force, ...)` | 14 ⚠️ | Główna funkcja kalibracji. | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L128) |
| `extract_current_metrics` | `extract_current_metrics(content)` | 4 | Wyciąga aktualne progi z YAML. | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L109) |
| `main` | `main()` | 6 | — | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L235) |
| `parse_pyqual_yaml` | `parse_pyqual_yaml(config_path)` | 1 | Odczytuje zawartość pyqual.yaml. | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L56) |
| `read_last_metrics_from_db` | `read_last_metrics_from_db(workdir)` | 6 | Czyta ostatnie metryki z pipeline.db pyqual. | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L25) |
| `update_metric` | `update_metric(content, metric_name, new_value)` | 4 | Aktualizuje wartość metryki w YAML. | [source](https://github.com/semcod/fixos/blob/main/scripts/pyqual-calibrate.py#L61) |

### `scripts.runtime` [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh)

| Function | Signature | CC | Description | Source |
|----------|-----------|----|-----------  |--------|
| `approvalScopeDigest` | `approvalScopeDigest()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L345) |
| `canonical` | `canonical()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L70) |
| `diagnostic` | `diagnostic()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L99) |
| `exactStringSet` | `exactStringSet()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L340) |
| `expectedVerdict` | `expectedVerdict()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L357) |
| `findNumericScore` | `findNumericScore()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L293) |
| `git` | `git()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L329) |
| `globToRegExp` | `globToRegExp()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L307) |
| `isDigest` | `isDigest()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L162) |
| `isObject` | `isObject()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L154) |
| `isSha` | `isSha()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L158) |
| `markdownReport` | `markdownReport()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L751) |
| `parseOptions` | `parseOptions()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L44) |
| `pathAllowed` | `pathAllowed()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L325) |
| `readJson` | `readJson()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L90) |
| `readText` | `readText()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L82) |
| `sha256Bytes` | `sha256Bytes()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L74) |
| `sha256File` | `sha256File()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L78) |
| `sortDeep` | `sortDeep()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L58) |
| `usage` | `usage()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L32) |
| `validateEvaluation` | `validateEvaluation()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L379) |
| `validateMinimumShape` | `validateMinimumShape()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L166) |
| `validatePolicyText` | `validatePolicyText()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L114) |
| `writeResult` | `writeResult()` | — | — | [source](https://github.com/semcod/fixos/blob/main/scripts/runtime.sh#L772) |
