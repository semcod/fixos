"""
Main CLI entry point for fixOS
"""

import click

from fixos import __version__
from fixos.cli.shared import BANNER, LazyCommandDict, NaturalLanguageGroup
from fixos.config import FixOsConfig

LAZY_COMMANDS: dict[str, tuple[str, str]] = {
    "ask": ("fixos.cli.ask_cmd", "ask"),
    "cleanup": ("fixos.cli.cleanup_cmd", "cleanup_services"),
    "config": ("fixos.cli.config_cmd", "config"),
    "dashboard": ("fixos.cli.dashboard", "dashboard_cmd"),
    "features": ("fixos.cli.features_cmd", "features"),
    "fix": ("fixos.cli.fix_cmd", "fix"),
    "history": ("fixos.cli.history_cmd", "history"),
    "jetbrains": ("fixos.cli.jetbrains_cmd", "jetbrains"),
    "llm": ("fixos.cli.provider_cmd", "llm_providers"),
    "orchestrate": ("fixos.cli.orchestrate_cmd", "orchestrate"),
    "profile": ("fixos.cli.profile_cmd", "profile"),
    "projects": ("fixos.cli.projects_cmd", "projects_cmd"),
    "providers": ("fixos.cli.provider_cmd", "providers"),
    "quick": ("fixos.cli.quick_cmd", "quick"),
    "quickfix": ("fixos.cli.quickfix_cmd", "quickfix"),
    "report": ("fixos.cli.report_cmd", "report"),
    "rollback": ("fixos.cli.rollback_cmd", "rollback"),
    "scan": ("fixos.cli.scan_cmd", "scan"),
    "shell": ("fixos.cli.shell_cmd", "shell_cmd"),
    "test-llm": ("fixos.cli.provider_cmd", "test_llm"),
    "token": ("fixos.cli.token_cmd", "token"),
    "watch": ("fixos.cli.watch_cmd", "watch"),
}



@click.group(cls=NaturalLanguageGroup, invoke_without_command=True)
@click.pass_context
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Symuluj bez wykonania (dla komend naturalnych)",
)
@click.option(
    "--interactive/--no-interactive",
    "-i",
    "interactive_mode",
    default=None,
    help="Uruchom interaktywny shell przy wywołaniu bez podkomendy",
)
@click.option("--version", "-v", is_flag=True, default=False, help="Pokaż wersję fixos")
def cli(ctx, dry_run, interactive_mode, version) -> None:
    """
    fixos – AI-powered diagnostyka i naprawa Linux, Windows, macOS.

    \b
    Szybki start:
      fixos                       # interaktywne menu i shell w terminalu
      fixos shell                 # dedykowany interaktywny shell (REPL)
      fixos quick                 # wynik w kilka sekund, bez LLM
      fixos token set AIzaSy...   # opcjonalnie: zapisz token Gemini
      fixos fix                   # pogłębiona diagnostyka + naprawa

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
        import sys

        is_tty = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
        should_run_interactive = interactive_mode is True or (
            interactive_mode is None and is_tty
        )
        if should_run_interactive:
            from fixos.cli.shell_cmd import run_interactive_shell

            run_interactive_shell(ctx)


def _print_welcome() -> None:
    """Display welcome screen when no subcommand is specified."""
    click.echo(click.style(BANNER, fg="cyan"))
    _print_quick_status()

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
        ("fixos shell", "", "Interaktywny shell z autouzupełnianiem TAB i menu"),
        ("fixos quick", "", "Szybki wynik bez LLM + trend CPU/RAM/dysku"),
        ("fixos fix", "", "Diagnostyka + sesja naprawcza z AI (HITL)"),
        ("fixos scan", "", "Diagnostyka systemu bez AI"),
        ("fixos quickfix", "", "Naprawy offline bez API (baza znanych bugów)"),
        ("fixos cleanup", "", "Skanuj i czyść dane usług (Docker, Ollama)"),
        (
            "fixos cleanup --tmp --retention 24h",
            "",
            "Wybierz stare pliki z /tmp; usunięcie wymaga potwierdzenia",
        ),
        ("fixos cleanup --policy", "", "Cele czyszczenia, retencja i chronione dane"),
        (
            "fixos cleanup --docker-all",
            "",
            "Usuń unused images/cache i osierocone sieci",
        ),
        (
            "fixos cleanup --docker-old",
            "",
            "Usuń stare obrazy/cache i osierocone sieci",
        ),
        (
            "fixos cleanup --docker-networks",
            "",
            "Usuń nieużywane sieci i sprawdź pulę adresową",
        ),
        (
            "fixos cleanup --docker-buildcache",
            "",
            "Cache wszystkich builderów buildx + wiszące obrazy <none>",
        ),
        (
            "fixos cleanup --docker-stale-services",
            "",
            "Wybierz stare usługi, wyłącz autostart i opcjonalnie zatrzymaj",
        ),
        (
            "fixos cleanup --orphaned-projects",
            "",
            "Wybierz obciążenia projektów, których katalog już nie istnieje",
        ),
        (
            "fixos cleanup --list-orphan-pins",
            "",
            "Zarządzaj trwałą ochroną zachowanych projektów Compose",
        ),
        (
            "fixos jetbrains doctor",
            "",
            "Diagnozuj JVM, EDT i logi IDE bez zamykania okien",
        ),
        (
            "fixos cleanup --ollama-old",
            "",
            "Usuń modele Ollama niezmieniane od 90+ dni",
        ),
        (
            "fixos cleanup --snap-old",
            "",
            "Usuń wyłączone rewizje snapów (stare wersje .snap)",
        ),
        (
            "fixos cleanup --journal",
            "",
            "Przytnij dziennik systemd (journalctl --vacuum)",
        ),
        (
            "fixos cleanup --user-cache",
            "",
            "Wybierz i usuń duże katalogi z ~/.cache",
        ),
        (
            "fixos cleanup --jetbrains",
            "",
            "Stare wersje IDE z Toolbox i cache JetBrains",
        ),
        (
            "fixos cleanup --libvirt",
            "",
            "Obrazy VM niepodpięte pod żadną domenę libvirt",
        ),
        (
            "fixos cleanup --gitive",
            "",
            "Stare izolowane workspace'y gitive-isolated",
        ),
        (
            "fixos cleanup --venvs-old",
            "",
            "Stare venv/.venv: podsumowanie i wybór okresu (30 dni)",
        ),
        (
            "fixos projects",
            "",
            "Skanuj projekty dev (venv, node_modules, ~/github/*/*)",
        ),
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
        cmd_styled = click.style(f"{cmd:<32}", fg="yellow")
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
            f"{click.style('     fixos cleanup --docker-old --dry-run', fg='yellow')} # stare nieużywane obrazy Docker"
        )
        click.echo(
            f"{click.style('     fixos cleanup --ollama-old --dry-run', fg='yellow')} # stare modele Ollama (90+ dni)"
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


def _print_quick_status() -> None:
    """Best-effort quick result; a welcome screen must never fail on telemetry."""
    try:
        from fixos.cli.quick_cmd import render_quick_snapshot
        from fixos.diagnostics.quick_snapshot import collect_quick_snapshot

        render_quick_snapshot(collect_quick_snapshot(), compact=True)
    except Exception as exc:  # noqa: BLE001 - welcome banner must never crash the CLI
        click.echo(
            click.style(
                f"Szybka analiza chwilowo niedostępna: {exc}",
                fg="yellow",
            )
        )


def main() -> None:
    """Entry point for fixOS CLI."""
    cli()


@click.command("help")
@click.argument("command", required=False)
@click.pass_context
def help_cmd(ctx, command) -> None:
    """Pokaż pomoc: fixos help [KOMENDA]."""
    root = ctx.find_root()
    if not command:
        click.echo(root.get_help())
        return
    target = root.command.get_command(root, command)
    if target is None:
        raise click.UsageError(f"Nieznana komenda: {command}", ctx=ctx)
    with click.Context(target, info_name=command, parent=root) as sub:
        click.echo(target.get_help(sub))


cli.add_command(help_cmd)
cli.commands = LazyCommandDict(LAZY_COMMANDS, cli.commands)


def __getattr__(name: str):
    if name in cli.commands:
        return cli.commands[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

