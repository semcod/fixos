"""
Tryb autonomiczny – agent sam diagnozuje i naprawia system.
Wymaga jawnego włączenia: --mode autonomous lub AGENT_MODE=autonomous
Posiada mechanizmy bezpieczeństwa i limity.

Refactored: Now uses AutonomousSession class for better modularity.
"""

from __future__ import annotations

from .autonomous_session import (
    FORBIDDEN_COMMANDS,
    SUDO_PREFIXES,
    SYSTEM_PROMPT_AUTONOMOUS,
    AgentReport,
    AutonomousSession,
    FixAction,
)

__all__ = [
    "FORBIDDEN_COMMANDS",
    "SUDO_PREFIXES",
    "SYSTEM_PROMPT_AUTONOMOUS",
    "AgentReport",
    "AutonomousSession",
    "FixAction",
    "run_autonomous_session",
]


def run_autonomous_session(
    diagnostics: dict,
    config,
    show_data: bool = True,
    max_fixes: int = 10,
    auto_confirm: bool = False,
    use_llm: bool | None = None,
    dry_run: bool = False,
) -> AgentReport:
    """
    Uruchamia autonomiczny tryb agenta.

    This is a backward-compatible wrapper around AutonomousSession.
    For new code, use AutonomousSession directly.
    """
    session = AutonomousSession(
        diagnostics=diagnostics,
        config=config,
        show_data=show_data,
        max_fixes=max_fixes,
        auto_confirm=auto_confirm,
        use_llm=use_llm,
        dry_run=dry_run,
    )
    return session.run()
