"""
Main CLI entry point for fixOS
"""

import click

from fixos import __version__
from fixos.cli.shared import BANNER, NaturalLanguageGroup
from fixos.config import FixOsConfig


@click.group(cls=NaturalLanguageGroup, invoke_without_command=True)
@click.pass_context
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Symuluj bez wykonania (dla komend naturalnych)",
)
@click.option("--version", "-v", is_flag=True, default=False, help="Pokaż wersję fixos")
def cli(ctx, dry_run, version) -> None:
    """
    fixos – AI-powered diagnostyka i naprawa Linux, Windows, macOS.

    \b
    Szybki start:
      fixos token set AIzaSy...   # zapisz token Gemini
      fixos fix                   # diagnostyka + naprawa
      fixos scan --audio          # tylko skan audio

    \b
    Polecenia w jezyku naturalnym:
      fixos "wylacz wszystkie kontenery docker"
      fixos "zlap bledy w systemie"
      fixos "napraw audio"

    \b
    Więcej:
      fixos --help
      fixos fix --help
    """
    if version:
        click.echo(f"fixos v{__version__}")
        return

    if ctx.invoked_subcommand is None:
        _print_welcome()


def _print_welcome() -> None:
    """Display welcome screen when no subcommand is specified."""
    click.echo(click.style(BANNER, fg="cyan"))

    cfg = FixOsConfig.load()
    has_key = bool(cfg.api_key)
    key_status = (
        click.style("skonfigurowany", fg="green")
        if has_key
        else click.style("BRAK", fg="red")
    )
    provider_info = f"{cfg.provider} ({cfg.model})"

    click.echo(click.style("═" * 60, fg="cyan"))
    click.echo(click.style("  DOSTĘPNE KOMENDY", fg="cyan", bold=True))
    click.echo(click.style("═" * 60, fg="cyan"))
    click.echo()

    commands = [
        ("fixos fix", "", "Diagnostyka + sesja naprawcza z AI (HITL)"),
        ("fixos scan", "", "Diagnostyka systemu bez AI"),
        ("fixos quickfix", "", "Naprawy offline bez API (baza znanych bugów)"),
        ("fixos cleanup", "", "Skanuj i czyść dane usług (Docker, Ollama)"),
        ("fixos projects", "", "Skanuj projekty dev (venv, node_modules, ~/github/*/*)"),
        ("fixos orchestrate", "", "Zaawansowana orkiestracja napraw (graf problemów)"),
        ("fixos watch", "", "Monitoring w tle z powiadomieniami"),
        ("fixos report", "", "Eksport diagnostyki do HTML/Markdown/JSON"),
        ("fixos history", "", "Historia sesji naprawczych"),
        ("fixos rollback", "", "Cofanie operacji (undo/list/show)"),
        ("fixos profile", "", "Profile diagnostyczne (server/desktop/dev)"),
        ("fixos llm", "", "Lista providerów LLM + linki do kluczy API"),
        ("fixos token set", "", "Zapisz klucz API (auto-detekcja providera)"),
        ("fixos config show", "", "Pokaż konfigurację"),
        ("fixos test-llm", "", "Test połączenia z LLM"),
    ]

    for cmd, icon, desc in commands:
        cmd_styled = click.style(f"{cmd:<26}", fg="yellow")
        click.echo(f"  {icon}  {cmd_styled} {desc}")

    click.echo()
    click.echo(click.style("─" * 60, fg="cyan"))
    click.echo(click.style("  🔬 MODUŁY DIAGNOSTYKI", fg="cyan"))
    click.echo(click.style("─" * 60, fg="cyan"))
    modules_info = [
        ("system", " ", "CPU, RAM, dyski, usługi, aktualizacje"),
        ("audio", "", "ALSA, PipeWire, SOF firmware, mikrofon"),
        ("thumbnails", " ", "Podglądy plików, cache, GStreamer"),
        ("hardware", "", "DMI, GPU, touchpad, kamera, bateria"),
        ("security", "", "Firewall, porty, SELinux, SSH, fail2ban"),
        ("resources", "", "Dysk (co zajmuje), procesy, autostart"),
    ]
    for mod, icon, desc in modules_info:
        mod_styled = click.style(f"{mod:<12}", fg="white")
        click.echo(f"  {icon}  {mod_styled} {desc}")
    click.echo(
        click.style("  Użycie: fixos scan --modules security,resources", fg="cyan")
    )

    click.echo()
    click.echo(click.style("─" * 60, fg="cyan"))
    click.echo(click.style("  AKTUALNY STATUS", fg="cyan"))
    click.echo(click.style("─" * 60, fg="cyan"))
    click.echo(f"  Provider  : {provider_info}")
    click.echo(f"  API Key   : {key_status}")
    click.echo(f"  .env plik : {cfg.env_file_loaded or 'nie znaleziono'}")
    click.echo()

    if not has_key:
        click.echo(click.style("  Szybki start:", fg="yellow", bold=True))
        click.echo(
            f"{click.style('     fixos llm', fg='yellow')}                    # wybierz provider i pobierz klucz"
        )
        click.echo(
            f"{click.style('     fixos token set <KLUCZ>', fg='yellow')}      # zapisz klucz (auto-detekcja providera)"
        )
        click.echo(
            f"{click.style('     fixos fix', fg='yellow')}                    # uruchom diagnostykę + naprawę"
        )
        click.echo()
        click.echo(click.style("  ⚡ Lub po prostu:", fg="yellow"))
        click.echo(
            f"{click.style('     fixos fix', fg='yellow')}  # zapyta o provider interaktywnie"
        )
    else:
        click.echo(click.style("  Przykłady użycia:", fg="yellow", bold=True))
        click.echo(
            f"{click.style('     fixos fix', fg='yellow')}                           # pełna diagnostyka + naprawa"
        )
        click.echo(
            f"{click.style('     fixos fix --modules security,resources', fg='yellow')} # bezpieczeństwo + zasoby"
        )
        click.echo(
            f"{click.style('     fixos scan --modules security', fg='yellow')}        # tylko skan bezpieczeństwa"
        )
        click.echo(
            f"{click.style('     fixos orchestrate --dry-run', fg='yellow')}          # podgląd napraw bez wykonania"
        )
    click.echo()


def main() -> None:
    """Entry point for fixOS CLI."""
    cli()


# Register commands
from fixos.cli.rollback_cmd import rollback
from fixos.cli.watch_cmd import watch
from fixos.cli.profile_cmd import profile
from fixos.cli.history_cmd import history
from fixos.cli.report_cmd import report
from fixos.cli.quickfix_cmd import quickfix
from fixos.cli.token_cmd import token
from fixos.cli.config_cmd import config
from fixos.cli.provider_cmd import llm_providers, providers, test_llm
from fixos.cli.ask_cmd import ask
from fixos.cli.scan_cmd import scan
from fixos.cli.fix_cmd import fix
from fixos.cli.orchestrate_cmd import orchestrate
from fixos.cli.cleanup_cmd import cleanup_services
from fixos.cli.projects_cmd import projects_cmd
from fixos.cli.features_cmd import features

cli.add_command(rollback)
cli.add_command(watch)
cli.add_command(profile)
cli.add_command(history)
cli.add_command(report)
cli.add_command(quickfix)
cli.add_command(token)
cli.add_command(config)
cli.add_command(llm_providers)
cli.add_command(providers)
cli.add_command(test_llm)
cli.add_command(ask)
cli.add_command(scan)
cli.add_command(fix)
cli.add_command(orchestrate)
cli.add_command(cleanup_services)
cli.add_command(projects_cmd)
cli.add_command(features)
