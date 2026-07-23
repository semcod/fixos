"""
Fix command for fixOS CLI - diagnostics and repair session with LLM
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

import click

from fixos.cli.shared import add_common_options, add_shared_options, BANNER
from fixos.cli.output_formatter import OutputFormatter
from fixos.config import FixOsConfig, interactive_provider_setup
from fixos.agent.hitl import run_hitl_session
from fixos.agent.autonomous import run_autonomous_session
from fixos.constants import (
    DEFAULT_SESSION_TIMEOUT,
    MAX_FIXES_DEFAULT,
    MAX_SEARCH_QUERY_LENGTH,
)


def _collect_diagnostics(
    modules: str, disc: bool, fmt: OutputFormatter, output: str
) -> dict:
    """Run quick-first diagnostics and optionally disk analysis."""
    selected_modules = modules.split(",") if modules else None
    from fixos.diagnostics.quick_snapshot import collect_quick_snapshot

    quick_snapshot = collect_quick_snapshot()
    data: dict = {"quick": quick_snapshot}
    if not fmt.is_machine:
        from fixos.cli.quick_cmd import render_quick_snapshot

        render_quick_snapshot(quick_snapshot)

    if disc and not modules:
        pass
    else:
        fmt.status("\nZbieranie diagnostyki rozszerzonej...", fg="yellow")
        from fixos.diagnostics import get_full_diagnostics
        from fixos.diagnostics.system_checks import DEFAULT_DIAGNOSTIC_MODULES

        diagnostic_modules = selected_modules or list(DEFAULT_DIAGNOSTIC_MODULES)
        data.update(
            get_full_diagnostics(diagnostic_modules, progress_callback=fmt.progress)
        )

    if disc:
        from fixos.cli.scan_cmd import _run_disk_analysis

        _run_disk_analysis(data, fmt=fmt, is_fix_mode=True)

    if output:
        from fixos.utils.anonymizer import anonymize

        anon_str, _ = anonymize(str(data))
        try:
            Path(output).write_text(
                json.dumps(
                    {"anonymized": anon_str, "raw": data},
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            fmt.status(f"Raport: {output}", fg="green")
        except Exception as e:
            fmt.status(f"Błąd zapisu: {e}")

    return data


def _run_agent_session(cfg, data: dict, max_fixes: int) -> None:
    """Dispatch to the appropriate agent session based on cfg.agent_mode."""
    if cfg.agent_mode == "autonomous":
        run_autonomous_session(
            diagnostics=data,
            config=cfg,
            show_data=cfg.show_anonymized_data,
            max_fixes=max_fixes,
        )
    else:
        run_hitl_session(
            diagnostics=data,
            config=cfg,
            show_data=cfg.show_anonymized_data,
        )


@click.command()
@add_common_options
@click.option(
    "--mode",
    type=click.Choice(["hitl", "autonomous"]),
    default=None,
    help="Tryb: hitl (domyślny) lub autonomous",
)
@click.option(
    "--timeout",
    default=DEFAULT_SESSION_TIMEOUT,
    show_default=True,
    help="Timeout sesji agenta (sekundy)",
)
@click.option(
    "--modules",
    "-M",
    default=None,
    help=(
        "Moduły diagnostyki: audio,thumbnails,hardware,system,... "
        "(domyślnie szybki zestaw bez głębokiego skanu plików; użyj 'all')"
    ),
)
@click.option(
    "--no-show-data",
    is_flag=True,
    default=False,
    help="Nie pokazuj danych diagnostycznych (tylko podsumowanie)",
)
@click.option("--output", "-o", default=None, help="Zapisz log sesji do JSON")
@click.option(
    "--max-fixes",
    default=MAX_FIXES_DEFAULT,
    show_default=True,
    help="Maksymalna liczba napraw w sesji",
)
@add_shared_options
def fix(
    provider,
    token,
    model,
    no_banner,
    mode,
    timeout,
    modules,
    no_show_data,
    output,
    max_fixes,
    disc,
    dry_run,
    interactive,
    json_output,
    yaml_output,
    llm_fallback,
    show_raw,
) -> None:
    """
    Przeprowadza pełną diagnostykę i uruchamia sesję naprawczą z LLM.

    \b
    Tryby:
      hitl        – Human-in-the-Loop (pyta o każdą akcję) [domyślny]
      autonomous  – Agent sam wykonuje komendy (UWAGA: wymaga potwierdzenia)

    \b
    Pipeline (synchroniczny, bez interakcji):
      fixos fix --yaml --no-interactive       # diagnostyka → YAML
      fixos fix --yaml --no-interactive --disc # diagnostyka + dysk → YAML

    \b
    Opcje dyskowe:
      --disc      – Analiza zajętości dysku + grupowanie przyczyn
      --dry-run   – Symulacja bez wykonywania akcji
      --json      – Wyjście w formacie JSON
      --yaml      – Wyjście w formacie YAML (pipe-safe)
      --llm-fallback – Użyj LLM gdy heurystyki nie wystarczą

    \b
    Przykłady:
      fixos fix                              # domyślnie hitl + Gemini z .env
      fixos fix --disc                       # z analizą dysku
      fixos fix --disc --dry-run             # analiza dysku bez wykonywania
      fixos fix --mode autonomous            # tryb autonomiczny
      fixos fix --modules audio,thumbnails   # tylko audio i thumbnails
      fixos fix --modules all                # także głęboki skan plików
      fixos fix --yaml --no-interactive      # pipeline mode → YAML
      fixos fix --provider openai --token sk-...
    """
    fmt = OutputFormatter.from_flags(yaml_output=yaml_output, json_output=json_output)

    if not no_banner:
        fmt.banner(BANNER)

    # ── Pipeline mode: --yaml/--json + --no-interactive ──────
    if fmt.is_machine and not interactive:
        fmt.status("Pipeline mode: diagnostyka → structured output", fg="cyan")
        data = _collect_diagnostics(modules, disc, fmt, output)
        fmt.status("Diagnostyka gotowa.", fg="green")
        content = fmt.format_diagnostics(data)
        click.echo(content)
        return

    # ── Interactive / LLM mode ────────────────────────────────
    cfg = FixOsConfig.load(
        provider=provider,
        api_key=token,
        model=model,
        agent_mode=mode,
        session_timeout=timeout,
        show_anonymized_data=not no_show_data,
    )

    if mode:
        cfg.agent_mode = mode

    errors = cfg.validate()
    if errors:
        click.echo(click.style("\nBrak konfiguracji LLM.", fg="yellow"))
        new_cfg = interactive_provider_setup()
        if new_cfg is None:
            click.echo(
                click.style(
                    "Anulowano. Użyj: fixos llm  aby zobaczyć dostępne providery.",
                    fg="red",
                )
            )
            sys.exit(1)
        cfg = new_cfg
        errors = cfg.validate()
        if errors:
            for err in errors:
                click.echo(click.style(f"{err}", fg="red"))
            sys.exit(1)

    fmt.status("\nKonfiguracja:", fg="cyan")
    click.echo(cfg.summary())
    if dry_run:
        fmt.status("  Tryb: DRY-RUN (komendy nie będą wykonywane)", fg="yellow")
    if disc:
        fmt.status("  Analiza dysku: Włączona", fg="blue")

    data = _collect_diagnostics(modules, disc, fmt, output)
    fmt.status("Diagnostyka gotowa.\n", fg="green")

    if disc and "disk_analysis" in data:
        return handle_disk_cleanup_mode(
            data["disk_analysis"], cfg, dry_run, interactive, json_output, llm_fallback
        )

    _run_agent_session(cfg, data, max_fixes)


def handle_disk_cleanup_mode(
    disk_analysis: Dict[str, Any],
    cfg,
    dry_run: bool,
    interactive: bool,
    json_output: bool,
    llm_fallback: bool,
) -> None:
    """Handle disk cleanup mode with interactive planning"""
    from fixos.interactive.cleanup_planner import CleanupPlanner

    suggestions = disk_analysis.get("suggestions", [])
    if not suggestions:
        click.echo(click.style("Brak sugestii czyszczenia dysku.", fg="green"))
        return

    # Create cleanup plan
    planner = CleanupPlanner()
    plan = planner.create_cleanup_plan(suggestions)

    if json_output:
        click.echo(json.dumps(plan, indent=2, default=str))
        return

    # Display plan summary
    summary = plan["summary"]
    click.echo(click.style("\nPlan czyszczenia dysku:", fg="cyan"))
    click.echo(f"  🔢 Akcje: {summary['total_actions']}")
    click.echo(f"  Miejsce: {summary['total_size_gb']:.1f} GB")
    click.echo(f"  Bezpieczne: {summary['safe_size_gb']:.1f} GB")
    click.echo(f"  📂 Kategorie: {summary['categories_count']}")

    # Show categories
    for category_id, category_data in plan["categories"].items():
        info = category_data["info"]
        click.echo(f"\n{info['icon']} {info['name']}:")
        click.echo(f"  📁 Akcje: {category_data['actions_count']}")
        click.echo(f"  Miejsce: {category_data['total_size_gb']:.1f} GB")

        # Show top actions
        for action in category_data["actions"][:3]:
            safe_icon = "" if action["safe"] else ""
            priority_icon = {"critical": "", "high": "", "medium": "", "low": ""}.get(
                action["priority"], ""
            )
            click.echo(
                f"    {safe_icon} {priority_icon} {action['description']} ({action['size_gb']:.1f}GB)"
            )

    # Show recommendations
    recommendations = plan.get("recommendations", [])
    if recommendations:
        click.echo(click.style("\nRekomendacje:", fg="yellow"))
        for rec in recommendations:
            priority_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(
                rec["priority"], "gray"
            )
            click.echo(click.style(f"  🎯 {rec['title']}", fg=priority_color))
            click.echo(f"     {rec['description']}")

    if dry_run:
        click.echo(
            click.style(
                "\nTryb DRY-RUN - żadne akcje nie zostaną wykonane", fg="yellow"
            )
        )
        return

    if interactive:
        selection = planner.interactive_selection(plan)
        click.echo(
            click.style(
                f"\nWybrano {selection['total_selected']} akcji do wykonania",
                fg="green",
            )
        )
        click.echo(
            click.style(
                f"Szacowane miejsce: {selection['estimated_space_gb']:.1f} GB",
                fg="green",
            )
        )

        # Execute selected actions
        execute_cleanup_actions(selection["selected_actions"], cfg, llm_fallback)
    else:
        # Auto-execute safe actions
        safe_actions = [a for a in plan["prioritized_actions"] if a.get("safe", False)]
        if safe_actions:
            click.echo(
                click.style(
                    f"\nAutomatyczne wykonanie {len(safe_actions)} bezpiecznych akcji",
                    fg="blue",
                )
            )
            execute_cleanup_actions(safe_actions, cfg, llm_fallback)
        else:
            click.echo(
                click.style(
                    "\nBrak bezpiecznych akcji do automatycznego wykonania", fg="yellow"
                )
            )


def execute_cleanup_actions(actions: List[Dict], cfg, llm_fallback: bool) -> None:
    """Execute cleanup actions with safety checks"""
    from fixos.orchestrator.executor import CommandExecutor

    executor = CommandExecutor(
        default_timeout=60,
        require_confirmation=False,  # Already confirmed
        dry_run=False,
    )

    successful = []
    failed = []

    for i, action in enumerate(actions, 1):
        click.echo(f"\n[{i}/{len(actions)}] {action['description']}")

        # Execute the action
        cmd = action.get("command")
        if not cmd:
            click.echo(click.style("  Brak komendy", fg="yellow"))
            continue

        result = executor.execute_sync(cmd)

        if result.success:
            click.echo(click.style("  OK", fg="green"))
            successful.append(action)
        else:
            click.echo(click.style(f"  Błąd: {result.error}", fg="red"))
            failed.append(action)

    # Summary
    click.echo(click.style("\nPodsumowanie:", fg="cyan"))
    click.echo(f"  Wykonane: {len(successful)}")
    click.echo(f"  Błędy: {len(failed)}")

    if failed and llm_fallback:
        click.echo(click.style("\nPróba naprawy błędów przez LLM...", fg="yellow"))
        try_llm_fallback_for_failures(failed, cfg)


def try_llm_fallback_for_failures(failed_actions, cfg) -> None:
    """Try to fix failed actions using LLM"""
    from fixos.providers.llm import LLMClient

    try:
        llm = LLMClient(cfg)

        failed_desc = "\n".join(
            [
                f"- {a['description']}: {a.get('command', 'brak komendy')}"
                for a in failed_actions
            ]
        )

        prompt = f"""Następujące akcje czyszczenia dysku zakończyły się błędem:
{failed_desc}

Zaproponuj alternatywne komendy lub podejście. Odpowiedz krótko, maksymalnie 3 komendy.
"""
        response = llm.chat(
            [{"role": "user", "content": prompt}], max_tokens=MAX_SEARCH_QUERY_LENGTH
        )
        click.echo(click.style("Sugestie LLM:", fg="cyan"))
        click.echo(response)

    except Exception as e:
        click.echo(click.style(f"Błąd LLM fallback: {e}", fg="red"))
