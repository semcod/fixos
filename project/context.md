# System Architecture Analysis
<!-- generated in 0.00s -->

## Overview

- **Project**: /home/tom/github/semcod/fixOS
- **Primary Language**: python
- **Languages**: python: 108, yaml: 15, txt: 3, shell: 3, yml: 3
- **Analysis Mode**: static
- **Total Functions**: 650
- **Total Classes**: 79
- **Modules**: 145
- **Entry Points**: 463

## Architecture by Module

### fixos.agent.session_io
- **Functions**: 26
- **File**: `session_io.py`

### fixos.agent.autonomous_session
- **Functions**: 22
- **Classes**: 3
- **File**: `autonomous_session.py`

### fixos.cli._cleanup_system
- **Functions**: 17
- **File**: `_cleanup_system.py`

### fixos.interactive.cleanup_planner
- **Functions**: 16
- **Classes**: 4
- **File**: `cleanup_planner.py`

### fixos.diagnostics.disk_analyzer
- **Functions**: 15
- **Classes**: 1
- **File**: `disk_analyzer.py`

### fixos.utils.anonymizer
- **Functions**: 14
- **Classes**: 1
- **File**: `anonymizer.py`

### fixos.diagnostics.dev_project_analyzer
- **Functions**: 13
- **Classes**: 2
- **File**: `dev_project_analyzer.py`

### fixos.orchestrator.orchestrator
- **Functions**: 13
- **Classes**: 2
- **File**: `orchestrator.py`

### fixos.diagnostics.service_cleanup
- **Functions**: 13
- **Classes**: 1
- **File**: `service_cleanup.py`

### fixos.agent.session_handlers
- **Functions**: 12
- **File**: `session_handlers.py`

### fixos.agent.hitl_session
- **Functions**: 12
- **Classes**: 1
- **File**: `hitl_session.py`

### fixos.features
- **Functions**: 12
- **Classes**: 2
- **File**: `__init__.py`

### fixos.features.installer
- **Functions**: 12
- **Classes**: 1
- **File**: `installer.py`

### fixos.cli.output_formatter
- **Functions**: 12
- **Classes**: 2
- **File**: `output_formatter.py`

### fixos.utils.terminal
- **Functions**: 12
- **Classes**: 1
- **File**: `terminal.py`

### fixos.orchestrator.executor
- **Functions**: 12
- **Classes**: 4
- **File**: `executor.py`

### fixos.diagnostics.service_scanner
- **Functions**: 12
- **Classes**: 4
- **File**: `service_scanner.py`

### fixos.cli.cleanup_cmd
- **Functions**: 12
- **File**: `cleanup_cmd.py`

### fixos.platform_utils
- **Functions**: 11
- **File**: `platform_utils.py`

### fixos.diagnostics._storage_user_mixin
- **Functions**: 11
- **Classes**: 1
- **File**: `_storage_user_mixin.py`

## Key Entry Points

Main execution flows into the system:

### fixos.cli.orchestrate_cmd.orchestrate
> Zaawansowana orkiestracja napraw z grafem problemów.


Różnica od 'fix':
  - Buduje graf kaskadowych zależności między problemami
  - Wykonuje napraw
- **Calls**: click.command, click.option, click.option, click.option, click.option, click.option, FixOsConfig.load, click.echo

### fixos.diagnostics.checks.resources.diagnose_resources
> Diagnostyka zasobów systemowych.
Sprawdza: dysk (co zajmuje miejsce), pamięć (co ją żre),
procesy startujące automatycznie, usługi w tle.
- **Calls**: psutil.process_iter, top_cpu.sort, top_mem.sort, fixos.diagnostics.checks._shared._psutil_required, len, round, result.update, round

### fixos.diagnostics._flatpak_execution_mixin._FlatpakExecutionMixin.ask_user_and_cleanup
> Pytaj użytkownika o zgodę i wykonaj czyszczenie.

Args:
    auto_confirm_low_risk: Jeśli True, automatycznie wykonuje operacje niskiego ryzyka

Return
- **Calls**: self.get_cleanup_recommendations, print, print, print, enumerate, print, print, print

### fixos.cli.config_cmd.config_model
> Interaktywnie wybierz model LLM z listy.
- **Calls**: config.command, click.option, FixOsConfig.load, PROVIDER_MODELS.get, click.echo, click.echo, click.echo, fixos.cli.config_cmd._set_env_key

### fixos.cli.scan_cmd._print_quick_issues
> Wyświetla szybki przegląd problemów z zebranych danych.
- **Calls**: click.echo, data.get, data.get, None.strip, data.get, None.strip, click.style, issues.append

### fixos.diagnostics.checks.security.diagnose_security
> Diagnostyka bezpieczeństwa systemu i sieci.
Sprawdza: firewall, otwarte porty, usługi sieciowe, SELinux/AppArmor,
aktualizacje bezpieczeństwa, nieauto
- **Calls**: result.update, result.update, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd

### fixos.cli.scan_cmd.scan
> Przeprowadza diagnostykę systemu.

\b
Formaty wyjścia:
  (domyślny)    – Human-readable z kolorami
  --json        – Wyjście w formacie JSON
  --yaml 
- **Calls**: click.command, click.option, click.option, click.option, click.option, click.option, click.option, click.option

### fixos.cli.fix_cmd.fix
> Przeprowadza pełną diagnostykę i uruchamia sesję naprawczą z LLM.


Tryby:
  hitl        – Human-in-the-Loop (pyta o każdą akcję) [domyślny]
  autono
- **Calls**: click.command, click.option, click.option, click.option, click.option, click.option, click.option, OutputFormatter.from_flags

### fixos.llm_shell.run_llm_shell
> Uruchamia interaktywny shell LLM z przekazanymi danymi diagnostycznymi.

Args:
    diagnostics_data: Słownik z danymi diagnostycznymi (przed anonimiza
- **Calls**: fixos.anonymizer.anonymize, openai.OpenAI, signal.signal, signal.alarm, time.time, Style.from_dict, PromptSession, print

### fixos.cli.provider_cmd.test_llm
> Test połączenia z LLM.


Wysyła proste zapytanie "Hello" i wyświetla odpowiedź.
Sprawdza czy token działa i provider jest dostępny.


Przykłady:
  f
- **Calls**: click.command, click.option, click.option, click.option, click.option, FixOsConfig.load, click.echo, click.echo

### fixos.cli.quickfix_cmd.quickfix
> Natychmiastowe naprawy bez API — baza znanych bugów.


Działa offline, zero tokenów. Używa wbudowanych heurystyk
do naprawy typowych problemów.


Pr
- **Calls**: click.command, click.option, click.option, PluginRegistry, registry.discover, click.echo, registry.run, click.echo

### fixos.utils.terminal.render_md
> Print LLM markdown reply to terminal via rich.

Handles:
- ``` code blocks ``` rendered as Syntax panels
- # / ## headings via rich Markdown
- ━━━ / =
- **Calls**: text.splitlines, _flush_md, None.startswith, line.strip, fixos.utils.terminal._is_divider_line, fixos.utils.terminal._get_severity_style, re.match, md_buffer.append

### fixos.cli.provider_cmd.llm_providers
> Lista dostępnych providerów LLM.


Pokazuje wszystkich providerów z linkami do kluczy API.
Użyj --free aby zobaczyć tylko darmowe opcje.
- **Calls**: click.command, click.option, FixOsConfig.load, click.echo, click.echo, click.echo, PROVIDERS_INFO.items, click.echo

### fixos.cli.token_cmd.token_set
> Zapisz token API do pliku .env.


Przykłady:
  fixos token set AIzaSy...                    # auto-detect provider
  fixos token set sk-... --provide
- **Calls**: token.command, click.argument, click.option, click.option, fixos.config.detect_provider_from_key, None.resolve, provider_env_vars.get, click.echo

### fixos.plugins.builtin.resources.Plugin.diagnose
- **Calls**: self._check_cpu, self._check_ram, self._check_top_processes, self._check_zombies, self._check_swap, any, DiagnosticResult, cpu.get

### fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._load_installed_refs
> Load all installed apps and runtimes with metadata
- **Calls**: self._run_flatpak_command, self._run_flatpak_command, json.loads, json.loads, FlatpakItemInfo, self._parse_size, self.installed_apps.append, FlatpakItemInfo

### docker.validate-scenario.main
- **Calls**: docker.validate-scenario.validate, len, print, print, sys.exit, print, print, sys.exit

### fixos.features.renderer.FeatureRenderer.render_audit
> Render complete audit results.
- **Calls**: console.print, console.print, len, len, len, console.print, console.print, console.print

### fixos.plugins.builtin.security.Plugin.diagnose
- **Calls**: self._check_firewall, self._check_selinux, findings.extend, self._check_open_ports, self._check_ssh, self._check_fail2ban, findings.extend, DiagnosticResult

### fixos.config.FixOsConfig.load
> Tworzy konfigurację z połączonych źródeł.
- **Calls**: fixos.config._load_env_files, cls, None.lower, pdef.get, None.lower, None.lower, os.environ.get, None.lower

### fixos.orchestrator.orchestrator.FixOrchestrator.load_from_diagnostics
> Parsuje dane diagnostyczne przez LLM i buduje graf problemów.
- **Calls**: fixos.anonymizer.anonymize, None.get, fixos.anonymizer.anonymize, DIAGNOSE_PROMPT.format, str, p.to_summary, self.llm.chat, self._parse_json

### fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin.get_cleanup_summary
> Get human-readable summary of cleanup opportunities
- **Calls**: self.analyze, lines.append, None.join, lines.append, sorted, lines.append, lines.append, lines.append

### fixos.diagnostics.storage_analyzer.StorageAnalyzer.analyze_full
> Run full system storage analysis
- **Calls**: self._analyze_dnf_cache, self._analyze_old_kernels, self._analyze_journal_logs, self._analyze_orphaned_packages, self._analyze_docker, self._analyze_podman, self._analyze_user_cache, self._analyze_browser_cache

### fixos.diagnostics.checks.audio.diagnose_audio
> Diagnostyka dźwięku (ALSA/PipeWire/PulseAudio/SOF).
Typowe problemy po aktualizacji system:
- SOF (Sound Open Firmware) - brak karty dźwiękowej
- Pipe
- **Calls**: fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd, fixos.diagnostics.checks._shared._cmd

### fixos.cli.report_cmd.report
> Eksport wyników diagnostyki do raportu HTML/Markdown/JSON.


Przykłady:
  fixos report                           # HTML do stdout
  fixos report -o r
- **Calls**: click.command, click.option, click.option, click.option, click.option, PluginRegistry, registry.discover, click.echo

### fixos.features.catalog.PackageCatalog.load
> Load package catalog from YAML files.
- **Calls**: cls, data.items, packages_file.exists, open, yaml.safe_load, cat_id.startswith, PackageCategory, cat_data.get

### fixos.cli.provider_cmd.providers
> Lista providerów LLM z oznaczeniem FREE/PAID.
- **Calls**: click.command, FixOsConfig.load, click.echo, click.echo, click.echo, PROVIDERS_INFO.items, click.echo, click.echo

### fixos.diagnostics.checks.system_core.diagnose_system
> System metrics – cross-platform: CPU, RAM, disks, processes.
- **Calls**: psutil.virtual_memory, psutil.swap_memory, psutil.disk_partitions, psutil.process_iter, procs.sort, fixos.diagnostics.checks.system_core._collect_os_info, result.update, fixos.diagnostics.checks._shared._psutil_required

### fixos.agent.session_io.print_action_menu
> Print the interactive numbered action menu.
- **Calls**: console.print, console.print, console.print, console.print, console.print, console.print, console.print, console.print

### fixos.features.SystemDetector.detect
> Detect complete system information.
- **Calls**: SystemInfo, self._detect_id_like, self._detect_de, self._detect_display_server, self._detect_gpu_vendor, self._detect_gpu_model, None.exists, self._detect_pkg_manager

## Process Flows

Key execution flows identified:

### Flow 1: orchestrate
```
orchestrate [fixos.cli.orchestrate_cmd]
```

### Flow 2: diagnose_resources
```
diagnose_resources [fixos.diagnostics.checks.resources]
  └─ →> _psutil_required
```

### Flow 3: ask_user_and_cleanup
```
ask_user_and_cleanup [fixos.diagnostics._flatpak_execution_mixin._FlatpakExecutionMixin]
```

### Flow 4: config_model
```
config_model [fixos.cli.config_cmd]
```

### Flow 5: _print_quick_issues
```
_print_quick_issues [fixos.cli.scan_cmd]
```

### Flow 6: diagnose_security
```
diagnose_security [fixos.diagnostics.checks.security]
  └─ →> _cmd
  └─ →> _cmd
```

### Flow 7: scan
```
scan [fixos.cli.scan_cmd]
```

### Flow 8: fix
```
fix [fixos.cli.fix_cmd]
```

### Flow 9: run_llm_shell
```
run_llm_shell [fixos.llm_shell]
  └─ →> anonymize
      └─> get_sensitive_values
```

### Flow 10: test_llm
```
test_llm [fixos.cli.provider_cmd]
```

## Key Classes

### fixos.agent.autonomous_session.AutonomousSession
> Self-directed autonomous diagnostic and repair session.
- **Methods**: 20
- **Key Methods**: fixos.agent.autonomous_session.AutonomousSession.__init__, fixos.agent.autonomous_session.AutonomousSession._setup_timeout, fixos.agent.autonomous_session.AutonomousSession._clear_timeout, fixos.agent.autonomous_session.AutonomousSession._confirm_start, fixos.agent.autonomous_session.AutonomousSession._initialize_messages, fixos.agent.autonomous_session.AutonomousSession._get_remaining_time, fixos.agent.autonomous_session.AutonomousSession._check_timeout, fixos.agent.autonomous_session.AutonomousSession._query_llm, fixos.agent.autonomous_session.AutonomousSession._handle_llm_error, fixos.agent.autonomous_session.AutonomousSession._parse_action

### fixos.diagnostics.disk_analyzer.DiskAnalyzer
> Analyzes disk usage and provides cleanup suggestions
- **Methods**: 14
- **Key Methods**: fixos.diagnostics.disk_analyzer.DiskAnalyzer.__init__, fixos.diagnostics.disk_analyzer.DiskAnalyzer.analyze_disk_usage, fixos.diagnostics.disk_analyzer.DiskAnalyzer._get_disk_status, fixos.diagnostics.disk_analyzer.DiskAnalyzer.get_large_files, fixos.diagnostics.disk_analyzer.DiskAnalyzer.get_cache_dirs, fixos.diagnostics.disk_analyzer.DiskAnalyzer.get_log_dirs, fixos.diagnostics.disk_analyzer.DiskAnalyzer.get_temp_dirs, fixos.diagnostics.disk_analyzer.DiskAnalyzer.suggest_cleanup_actions, fixos.diagnostics.disk_analyzer.DiskAnalyzer._get_dir_size_mb, fixos.diagnostics.disk_analyzer.DiskAnalyzer._categorize_file

### fixos.interactive.cleanup_planner.CleanupPlanner
> Interactive cleanup planning and grouping system
- **Methods**: 14
- **Key Methods**: fixos.interactive.cleanup_planner.CleanupPlanner.__init__, fixos.interactive.cleanup_planner.CleanupPlanner.group_by_category, fixos.interactive.cleanup_planner.CleanupPlanner.prioritize_actions, fixos.interactive.cleanup_planner.CleanupPlanner.create_cleanup_plan, fixos.interactive.cleanup_planner.CleanupPlanner.interactive_selection, fixos.interactive.cleanup_planner.CleanupPlanner._dict_to_action, fixos.interactive.cleanup_planner.CleanupPlanner._action_to_dict, fixos.interactive.cleanup_planner.CleanupPlanner._get_category_for_action, fixos.interactive.cleanup_planner.CleanupPlanner._priority_score, fixos.interactive.cleanup_planner.CleanupPlanner._rec_safe_high_impact

### fixos.orchestrator.orchestrator.FixOrchestrator
> Orkiestrator napraw systemowych.

Tryby:
- hitl: każda komenda wymaga potwierdzenia użytkownika
- au
- **Methods**: 13
- **Key Methods**: fixos.orchestrator.orchestrator.FixOrchestrator.__init__, fixos.orchestrator.orchestrator.FixOrchestrator.load_from_diagnostics, fixos.orchestrator.orchestrator.FixOrchestrator.load_from_dict, fixos.orchestrator.orchestrator.FixOrchestrator._process_fix_commands, fixos.orchestrator.orchestrator.FixOrchestrator._process_rediagnose, fixos.orchestrator.orchestrator.FixOrchestrator.run_sync, fixos.orchestrator.orchestrator.FixOrchestrator.run_async, fixos.orchestrator.orchestrator.FixOrchestrator._evaluate_and_rediagnose, fixos.orchestrator.orchestrator.FixOrchestrator._parse_json, fixos.orchestrator.orchestrator.FixOrchestrator._log

### fixos.diagnostics.service_cleanup.ServiceCleaner
> Plans and executes cleanup of service data.
- **Methods**: 13
- **Key Methods**: fixos.diagnostics.service_cleanup.ServiceCleaner.__init__, fixos.diagnostics.service_cleanup.ServiceCleaner.get_cleanup_plan, fixos.diagnostics.service_cleanup.ServiceCleaner.cleanup_service, fixos.diagnostics.service_cleanup.ServiceCleaner._service_to_dict, fixos.diagnostics.service_cleanup.ServiceCleaner.get_risk_level, fixos.diagnostics.service_cleanup.ServiceCleaner.is_safe_cleanup, fixos.diagnostics.service_cleanup.ServiceCleaner.get_cleanup_hints, fixos.diagnostics.service_cleanup.ServiceCleaner.get_service_description, fixos.diagnostics.service_cleanup.ServiceCleaner.get_cleanup_command, fixos.diagnostics.service_cleanup.ServiceCleaner._chrome_cleanup_command

### fixos.features.SystemDetector
> Detects system parameters.
- **Methods**: 12
- **Key Methods**: fixos.features.SystemDetector.detect, fixos.features.SystemDetector._detect_os_family, fixos.features.SystemDetector._detect_distro, fixos.features.SystemDetector._detect_distro_version, fixos.features.SystemDetector._detect_id_like, fixos.features.SystemDetector._detect_de, fixos.features.SystemDetector._detect_display_server, fixos.features.SystemDetector._detect_gpu_vendor, fixos.features.SystemDetector._detect_gpu_model, fixos.features.SystemDetector._detect_pkg_manager

### fixos.features.installer.FeatureInstaller
> Safely installs packages using native package manager or other backends.
- **Methods**: 12
- **Key Methods**: fixos.features.installer.FeatureInstaller.__init__, fixos.features.installer.FeatureInstaller.install, fixos.features.installer.FeatureInstaller._build_install_methods, fixos.features.installer.FeatureInstaller._install_package, fixos.features.installer.FeatureInstaller._install_repo, fixos.features.installer.FeatureInstaller._install_native, fixos.features.installer.FeatureInstaller._install_flatpak, fixos.features.installer.FeatureInstaller._install_pip, fixos.features.installer.FeatureInstaller._install_cargo, fixos.features.installer.FeatureInstaller._install_npm

### fixos.cli.output_formatter.OutputFormatter
> Centralized output formatter for fixOS CLI commands.

Usage:
    fmt = OutputFormatter.from_flags(ya
- **Methods**: 12
- **Key Methods**: fixos.cli.output_formatter.OutputFormatter.__init__, fixos.cli.output_formatter.OutputFormatter.from_flags, fixos.cli.output_formatter.OutputFormatter.is_machine, fixos.cli.output_formatter.OutputFormatter.status, fixos.cli.output_formatter.OutputFormatter.progress, fixos.cli.output_formatter.OutputFormatter.banner, fixos.cli.output_formatter.OutputFormatter.emit, fixos.cli.output_formatter.OutputFormatter.format_data, fixos.cli.output_formatter.OutputFormatter.format_diagnostics, fixos.cli.output_formatter.OutputFormatter.format_scan_result

### fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer
> Analyze developer projects for dependency folders that can be cleaned.

Skanuje tylko prywatne proje
- **Methods**: 11
- **Key Methods**: fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer.__init__, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer.analyze, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer._scan_directory, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer._check_dependency_folder, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer._create_dependency, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer._get_dir_size, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer._check_can_recreate, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer.get_old_dependencies, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer.get_large_dependencies, fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer.get_summary

### fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin
> Mixin providing user-level _analyze_* methods for StorageAnalyzer.
- **Methods**: 11
- **Key Methods**: fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_user_cache, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_browser_cache, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_btrfs_snapshots, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_browser_profiles, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_flatpak_user_data, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_ostree_repo, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_dev_projects, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._analyze_home_directory, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._find_large_files, fixos.diagnostics._storage_user_mixin._UserAnalyzerMixin._find_large_home_dirs

### fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin
> Mixin providing analysis methods for FlatpakAnalyzer.
- **Methods**: 11
- **Key Methods**: fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._load_installed_refs, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._find_unused_runtimes, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._dir_total_size, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._find_leftover_data, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._find_orphaned_apps, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._find_duplicate_apps, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._get_dir_size_du, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._get_dir_size_walk, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._measure_path_size, fixos.diagnostics._flatpak_analysis_mixin._FlatpakAnalysisMixin._analyze_repo_size

### fixos.agent.hitl_session.HITLSession
> Interactive Human-in-the-Loop diagnostic and repair session.
- **Methods**: 11
- **Key Methods**: fixos.agent.hitl_session.HITLSession.__init__, fixos.agent.hitl_session.HITLSession._setup_timeout, fixos.agent.hitl_session.HITLSession._clear_timeout, fixos.agent.hitl_session.HITLSession.remaining, fixos.agent.hitl_session.HITLSession._initialize_messages, fixos.agent.hitl_session.HITLSession._print_header, fixos.agent.hitl_session.HITLSession._handle_llm_error, fixos.agent.hitl_session.HITLSession._check_low_confidence, fixos.agent.hitl_session.HITLSession._process_turn, fixos.agent.hitl_session.HITLSession.run

### fixos.diagnostics.service_scanner.ServiceDataScanner
> Scans for large service data directories and allows cleanup.
- **Methods**: 11
- **Key Methods**: fixos.diagnostics.service_scanner.ServiceDataScanner.__init__, fixos.diagnostics.service_scanner.ServiceDataScanner.scan_all_services, fixos.diagnostics.service_scanner.ServiceDataScanner._collect_covered_paths, fixos.diagnostics.service_scanner.ServiceDataScanner.scan_service, fixos.diagnostics.service_scanner.ServiceDataScanner._merge_by_risk, fixos.diagnostics.service_scanner.ServiceDataScanner._merge_service_entries, fixos.diagnostics.service_scanner.ServiceDataScanner._analyze_service_path, fixos.diagnostics.service_scanner.ServiceDataScanner._get_path_size_mb, fixos.diagnostics.service_scanner.ServiceDataScanner._should_descend, fixos.diagnostics.service_scanner.ServiceDataScanner.get_cleanup_plan

### fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin
> Mixin providing system-level _analyze_* methods for StorageAnalyzer.
- **Methods**: 10
- **Key Methods**: fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_dnf_cache, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_old_kernels, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_journal_logs, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_coredumps, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_orphaned_packages, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_system_logs, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_var_cache, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._parse_snap_line, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._add_snap_items, fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._analyze_snap

### fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin
> Mixin providing cleanup recommendation methods for FlatpakAnalyzer.
- **Methods**: 9
- **Key Methods**: fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin.get_largest_apps, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin.get_cleanup_summary, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin._rec_repo_bloat, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin._rec_duplicates, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin._rec_unused_runtimes, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin._rec_large_apps, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin._rec_leftover_and_orphaned, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin._rec_hard_reset, fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin.get_cleanup_recommendations

### fixos.diagnostics.service_details.ServiceDetailsProvider
> Provides detailed information about service data.
- **Methods**: 9
- **Key Methods**: fixos.diagnostics.service_details.ServiceDetailsProvider.get_details, fixos.diagnostics.service_details.ServiceDetailsProvider._parse_docker_system_df, fixos.diagnostics.service_details.ServiceDetailsProvider._get_docker_counts, fixos.diagnostics.service_details.ServiceDetailsProvider._docker, fixos.diagnostics.service_details.ServiceDetailsProvider._ollama, fixos.diagnostics.service_details.ServiceDetailsProvider._conda, fixos.diagnostics.service_details.ServiceDetailsProvider._package_cache, fixos.diagnostics.service_details.ServiceDetailsProvider._flatpak, fixos.diagnostics.service_details.ServiceDetailsProvider._parse_size_bytes

### fixos.diagnostics.storage_analyzer.StorageAnalyzer
> Comprehensive storage analyzer for Linux systems.

Analizuje:
- DNF/RPM cache i stare kernele
- Jour
- **Methods**: 9
- **Key Methods**: fixos.diagnostics.storage_analyzer.StorageAnalyzer.__init__, fixos.diagnostics.storage_analyzer.StorageAnalyzer.analyze_full, fixos.diagnostics.storage_analyzer.StorageAnalyzer._get_dir_size, fixos.diagnostics.storage_analyzer.StorageAnalyzer._get_file_size, fixos.diagnostics.storage_analyzer.StorageAnalyzer._run_command, fixos.diagnostics.storage_analyzer.StorageAnalyzer._parse_size_static, fixos.diagnostics.storage_analyzer.StorageAnalyzer._parse_size, fixos.diagnostics.storage_analyzer.StorageAnalyzer._get_recommendations, fixos.diagnostics.storage_analyzer.StorageAnalyzer.get_summary
- **Inherits**: _SystemAnalyzerMixin, _ContainerAnalyzerMixin, _UserAnalyzerMixin

### fixos.plugins.registry.PluginRegistry
> Registry for diagnostic plugins with autodiscovery.
- **Methods**: 9
- **Key Methods**: fixos.plugins.registry.PluginRegistry.__init__, fixos.plugins.registry.PluginRegistry.discover, fixos.plugins.registry.PluginRegistry._register_builtins, fixos.plugins.registry.PluginRegistry._register_external, fixos.plugins.registry.PluginRegistry.register, fixos.plugins.registry.PluginRegistry.list_plugins, fixos.plugins.registry.PluginRegistry.get_plugin, fixos.plugins.registry.PluginRegistry.run, fixos.plugins.registry.PluginRegistry.last_results

### fixos.plugins.builtin.security.Plugin
- **Methods**: 9
- **Key Methods**: fixos.plugins.builtin.security.Plugin._selinux_findings, fixos.plugins.builtin.security.Plugin._fail2ban_findings, fixos.plugins.builtin.security.Plugin._overall_status, fixos.plugins.builtin.security.Plugin.diagnose, fixos.plugins.builtin.security.Plugin._check_firewall, fixos.plugins.builtin.security.Plugin._check_selinux, fixos.plugins.builtin.security.Plugin._check_open_ports, fixos.plugins.builtin.security.Plugin._check_ssh, fixos.plugins.builtin.security.Plugin._check_fail2ban
- **Inherits**: DiagnosticPlugin

### fixos.orchestrator.graph.ProblemGraph
> DAG problemów systemowych z topological sort do wyznaczania kolejności napraw.
Problemy bez nierozwi
- **Methods**: 9
- **Key Methods**: fixos.orchestrator.graph.ProblemGraph.__init__, fixos.orchestrator.graph.ProblemGraph.add, fixos.orchestrator.graph.ProblemGraph.get, fixos.orchestrator.graph.ProblemGraph.next_actionable, fixos.orchestrator.graph.ProblemGraph.all_done, fixos.orchestrator.graph.ProblemGraph.pending_count, fixos.orchestrator.graph.ProblemGraph.summary, fixos.orchestrator.graph.ProblemGraph.render_tree, fixos.orchestrator.graph.ProblemGraph._recalculate_order

## Data Transformation Functions

Key functions that process and transform data:

### docker.validate-scenario.validate
> Validate data against scenario expectations. Returns list of failures.
- **Output to**: SCENARIOS.get, exp.get, docker.validate-scenario._get_nested, str, failures.append

### fixos.config.FixOsConfig.validate
> Zwraca listę błędów walidacji (pusta = OK).
- **Output to**: errors.append, errors.append, None.get

### fixos.system_checks.get_top_processes
> Lista TOP N procesów według zużycia CPU.
- **Output to**: psutil.process_iter, processes.sort, processes.append, x.get

### fixos.llm_shell.format_time

### fixos.diagnostics._storage_system_mixin._SystemAnalyzerMixin._parse_snap_line
> Parse a single line from 'snap list --all' output. Returns None if invalid.
- **Output to**: line.split, len, status.lower, os.path.exists, self._get_file_size

### fixos.diagnostics.flatpak_analyzer.FlatpakAnalyzer._parse_size
> Parse human-readable size to bytes
- **Output to**: None.upper, sorted, multipliers.items, size_str.endswith, int

### fixos.diagnostics.flatpak_analyzer.FlatpakAnalyzer._format_size
> Format bytes to human-readable string
- **Output to**: _format_size_shared

### fixos.diagnostics._storage_container_mixin._ContainerAnalyzerMixin._parse_docker_df_output
> Parse 'docker system df -v' output into image/cache stats.
- **Output to**: output.split, raw_line.strip, _ContainerAnalyzerMixin._detect_docker_section, line.split, line.startswith

### fixos.diagnostics.utils.format_size
> Format bytes to human-readable string (B/KB/MB/GB/TB/PB).

### fixos.diagnostics.dev_project_analyzer.ProjectDependency._format_size
- **Output to**: fixos.diagnostics.dev_project_analyzer.ProjectDependency._format_size

### fixos.diagnostics.service_details.ServiceDetailsProvider._parse_docker_system_df
> Populate details from 'docker system df -v' output.
- **Output to**: subprocess.run, None.split, any, result.stdout.strip, line.split

### fixos.diagnostics.service_details.ServiceDetailsProvider._parse_size_bytes
> Parse human-readable size to bytes.
- **Output to**: None.upper, sorted, multipliers.items, size_str.endswith, int

### fixos.diagnostics.storage_analyzer.StorageItem._format_size
- **Output to**: fixos.diagnostics.storage_analyzer.StorageItem._format_size

### fixos.diagnostics.storage_analyzer.StorageAnalyzer._parse_size_static
> Parse size string like '1.2G' to bytes (static version for use in classmethods).
- **Output to**: None.upper, multipliers.items, size_str.endswith, int, size_str.strip

### fixos.diagnostics.storage_analyzer.StorageAnalyzer._parse_size
> Parse size string like '1.2G' to bytes
- **Output to**: self._parse_size_static

### fixos.agent.session_handlers.parse_user_input
> Parse user input and execute appropriate handler.

Returns:
    Tuple of (should_continue, was_handl
- **Output to**: user_in.lower, user_in.isdigit, user_in.startswith, lo.startswith, fixos.agent.session_handlers.handle_quit

### fixos.agent.autonomous_session.AutonomousSession._parse_action
> Parse JSON action from LLM reply.
- **Output to**: re.search, json.loads, reply.strip, json.loads, m.group

### fixos.agent.autonomous_session.AutonomousSession._process_turn
> Process one turn of the autonomous session.

Returns False if session should end, True to continue.
- **Output to**: self._check_timeout, self._get_remaining_time, print, self._query_llm, self.messages.append

### fixos.agent.hitl_session.HITLSession._process_turn
> Process one turn of the HITL session.
- **Output to**: self.remaining, io.print_thinking, io.clear_thinking, io.print_llm_reply, fixos.agent.session_core.extract_fixes

### fixos.cli._cleanup_utils._format_bytes
> Format bytes to human-readable string.
- **Output to**: fixos.diagnostics.flatpak_analyzer.FlatpakAnalyzer._format_size

### fixos.cli._cleanup_utils._parse_size_to_bytes
> Parse human-readable size to bytes.
- **Output to**: None.replace, sorted, multipliers.items, size_str.endswith, int

### fixos.cli._cleanup_utils._parse_size_to_gb
> Parse human-readable size to GB.
- **Output to**: None.upper, sorted, multipliers.items, size_str.endswith, size_str.strip

### fixos.cli._cleanup_utils._parse_selection
> Parse user selection into list of indices.
- **Output to**: None.lower, list, selection.split, sorted, selection.strip

### fixos.cli._cleanup_utils._parse_numeric_range_set
> Parse comma/range number string (e.g. '1,3,5-10') into a set of ints.
- **Output to**: set, nums.split, part.strip, part.split, selected.update

### fixos.cli.output_formatter.OutputFormatter.format_data
> Format data dict/list as string in the configured format.
- **Output to**: str, self._to_yaml, self._to_json

## Behavioral Patterns

### recursion__format_size
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fixos.diagnostics.dev_project_analyzer.ProjectDependency._format_size

### recursion__format_size
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fixos.diagnostics.storage_analyzer.StorageItem._format_size

### recursion__dict_to_markdown
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: fixos.utils.anonymizer._dict_to_markdown

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `fixos.cli.orchestrate_cmd.orchestrate` - 63 calls
- `fixos.diagnostics.checks.resources.diagnose_resources` - 49 calls
- `fixos.diagnostics._flatpak_execution_mixin._FlatpakExecutionMixin.ask_user_and_cleanup` - 44 calls
- `fixos.cli.fix_cmd.handle_disk_cleanup_mode` - 41 calls
- `fixos.cli.config_cmd.config_model` - 38 calls
- `fixos.diagnostics.checks.security.diagnose_security` - 36 calls
- `fixos.cli.scan_cmd.scan` - 36 calls
- `fixos.cli.fix_cmd.fix` - 36 calls
- `fixos.llm_shell.run_llm_shell` - 34 calls
- `fixos.cli.provider_cmd.test_llm` - 34 calls
- `fixos.cli.quickfix_cmd.quickfix` - 31 calls
- `fixos.utils.terminal.render_md` - 30 calls
- `fixos.cli.provider_cmd.llm_providers` - 29 calls
- `fixos.cli.token_cmd.token_set` - 29 calls
- `fixos.plugins.builtin.resources.Plugin.diagnose` - 29 calls
- `docker.validate-scenario.main` - 27 calls
- `fixos.features.renderer.FeatureRenderer.render_audit` - 27 calls
- `fixos.plugins.builtin.security.Plugin.diagnose` - 27 calls
- `fixos.config.FixOsConfig.load` - 26 calls
- `fixos.orchestrator.orchestrator.FixOrchestrator.load_from_diagnostics` - 26 calls
- `scripts.pyqual-calibrate.calibrate` - 26 calls
- `fixos.diagnostics._flatpak_recommendations_mixin._FlatpakRecommendationsMixin.get_cleanup_summary` - 25 calls
- `fixos.diagnostics.storage_analyzer.StorageAnalyzer.analyze_full` - 25 calls
- `fixos.diagnostics.checks.audio.diagnose_audio` - 25 calls
- `fixos.cli.report_cmd.report` - 25 calls
- `fixos.features.catalog.PackageCatalog.load` - 24 calls
- `fixos.cli.provider_cmd.providers` - 24 calls
- `fixos.diagnostics.checks.system_core.diagnose_system` - 23 calls
- `fixos.agent.session_io.print_action_menu` - 23 calls
- `fixos.features.SystemDetector.detect` - 23 calls
- `fixos.cli.fix_cmd.execute_cleanup_actions` - 23 calls
- `fixos.plugins.builtin.hardware.Plugin.diagnose` - 23 calls
- `fixos.plugins.builtin.thumbnails.Plugin.diagnose` - 23 calls
- `fixos.diagnostics.dev_project_analyzer.DevProjectAnalyzer.get_summary` - 22 calls
- `fixos.cli.rollback_cmd.rollback_undo` - 22 calls
- `fixos.plugins.builtin.audio.Plugin.diagnose` - 22 calls
- `fixos.diagnostics.checks.thumbnails.diagnose_thumbnails` - 21 calls
- `fixos.agent.session_handlers.run_single_command` - 21 calls
- `fixos.plugins.builtin.disk.Plugin.diagnose` - 21 calls
- `fixos.providers.llm_analyzer.LLMAnalyzer.analyze_failed_action` - 21 calls

## System Interactions

How components interact:

```mermaid
graph TD
    orchestrate --> command
    orchestrate --> option
    diagnose_resources --> process_iter
    diagnose_resources --> sort
    diagnose_resources --> _psutil_required
    diagnose_resources --> len
    ask_user_and_cleanup --> get_cleanup_recommen
    ask_user_and_cleanup --> print
    ask_user_and_cleanup --> enumerate
    config_model --> command
    config_model --> option
    config_model --> load
    config_model --> get
    config_model --> echo
    _print_quick_issues --> echo
    _print_quick_issues --> get
    _print_quick_issues --> strip
    diagnose_security --> update
    diagnose_security --> _cmd
    scan --> command
    scan --> option
    fix --> command
    fix --> option
    run_llm_shell --> anonymize
    run_llm_shell --> OpenAI
    run_llm_shell --> signal
    run_llm_shell --> alarm
    run_llm_shell --> time
    test_llm --> command
    test_llm --> option
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.