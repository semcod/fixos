"""
fixos CLI – backward compatibility layer

This module re-exports all CLI functionality from fixos.cli package.
The actual implementation has been moved to fixos.cli.* modules.

Migration path:
- Old: from fixos.cli import cli, main
- New: from fixos.cli import cli, main (unchanged)

For internal imports, use fixos.cli.* modules directly.
"""

# Re-export all public API from new cli package
from fixos.cli import cli, main
from fixos.cli.shared import (
    BANNER,
    COMMON_OPTIONS,
    add_common_options,
    add_shared_options,
    NaturalLanguageGroup,
)

# Re-export command functions for backward compatibility
from fixos.cli.scan_cmd import scan, _run_disk_analysis, _print_quick_issues
from fixos.cli.fix_cmd import (
    fix,
    handle_disk_cleanup_mode,
    execute_cleanup_actions,
    try_llm_fallback_for_failures,
)
from fixos.cli.orchestrate_cmd import orchestrate
from fixos.cli.cleanup_cmd import (
    cleanup_services,
    _cleanup_flatpak_detailed,
    _cleanup_single_service,
)
from fixos.cli.token_cmd import token, token_set, token_show, token_clear
from fixos.cli.config_cmd import config, config_show, config_init, config_set
from fixos.cli.provider_cmd import llm_providers, providers, test_llm
from fixos.cli.ask_cmd import (
    ask,
    _handle_natural_command,
    _match_heuristic_command,
    _execute_heuristic_command,
)
from fixos.cli.rollback_cmd import rollback, rollback_list, rollback_show, rollback_undo
from fixos.cli.watch_cmd import watch
from fixos.cli.profile_cmd import profile, profile_list, profile_show
from fixos.cli.history_cmd import history
from fixos.cli.report_cmd import report
from fixos.cli.quickfix_cmd import quickfix
from fixos.cli.quick_cmd import quick, render_quick_snapshot

__all__ = [
    # Main entry points
    "cli",
    "main",
    # Shared utilities
    "BANNER",
    "COMMON_OPTIONS",
    "add_common_options",
    "add_shared_options",
    "NaturalLanguageGroup",
    # Commands (for backward compat imports)
    "scan",
    "fix",
    "orchestrate",
    "cleanup_services",
    "token",
    "config",
    "ask",
    "rollback",
    "watch",
    "profile",
    "history",
    "report",
    "quickfix",
    "quick",
    "llm_providers",
    "providers",
    "test_llm",
    # Helper functions (backward compat)
    "_handle_natural_command",
    "_match_heuristic_command",
    "_execute_heuristic_command",
    "_run_disk_analysis",
    "_print_quick_issues",
    "_cleanup_flatpak_detailed",
    "_cleanup_single_service",
    "handle_disk_cleanup_mode",
    "execute_cleanup_actions",
    "try_llm_fallback_for_failures",
    "render_quick_snapshot",
    # Token subcommands
    "token_set",
    "token_show",
    "token_clear",
    # Config subcommands
    "config_show",
    "config_init",
    "config_set",
    # Rollback subcommands
    "rollback_list",
    "rollback_show",
    "rollback_undo",
    # Profile subcommands
    "profile_list",
    "profile_show",
]
