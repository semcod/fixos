"""
Interactive shell (REPL) and menu for fixOS CLI.
Provides tab-completion, command history, quick menu, and natural language query support.
"""

from __future__ import annotations

import os
import shlex
from typing import Any

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

MENU_ITEMS = (
    ("1", "quick", "Szybki wynik bez LLM + trend CPU/RAM/dysku"),
    ("2", "fix", "Diagnostyka + sesja naprawcza z AI (HITL)"),
    ("3", "scan", "Diagnostyka systemu bez AI"),
    ("4", "quickfix", "Naprawy offline bez API (baza znanych bugów)"),
    ("5", "cleanup", "Skanuj i czyść dane usług (Docker, Ollama)"),
    (
        "6",
        "cleanup --tmp --retention 24h",
        "Wybierz stare pliki z /tmp; usunięcie wymaga potwierdzenia",
    ),
    ("7", "cleanup --policy", "Cele czyszczenia, retencja i chronione dane"),
    ("8", "cleanup --docker-all", "Usuń unused images/cache i osierocone sieci"),
    ("9", "cleanup --docker-old", "Usuń stare obrazy/cache i osierocone sieci"),
    (
        "10",
        "cleanup --docker-networks",
        "Usuń nieużywane sieci i sprawdź pulę adresową",
    ),
    (
        "11",
        "cleanup --docker-buildcache",
        "Cache wszystkich builderów buildx + wiszące obrazy <none>",
    ),
    (
        "12",
        "cleanup --docker-stale-services",
        "Wybierz stare usługi, wyłącz autostart i opcjonalnie zatrzymaj",
    ),
    (
        "13",
        "cleanup --orphaned-projects",
        "Wybierz obciążenia projektów, których katalog już nie istnieje",
    ),
    (
        "14",
        "cleanup --list-orphan-pins",
        "Zarządzaj trwałą ochroną zachowanych projektów Compose",
    ),
    (
        "15",
        "jetbrains doctor",
        "Diagnozuj JVM, EDT i logi IDE bez zamykania okien",
    ),
    ("16", "cleanup --ollama-old", "Usuń modele Ollama niezmieniane od 90+ dni"),
    (
        "17",
        "cleanup --snap-old",
        "Usuń wyłączone rewizje snapów (stare wersje .snap)",
    ),
    (
        "18",
        "cleanup --journal",
        "Przytnij dziennik systemd (journalctl --vacuum)",
    ),
    ("19", "cleanup --user-cache", "Wybierz i usuń duże katalogi z ~/.cache"),
    (
        "20",
        "cleanup --jetbrains",
        "Stare wersje IDE z Toolbox i cache JetBrains",
    ),
    (
        "21",
        "cleanup --libvirt",
        "Obrazy VM niepodpięte pod żadną domenę libvirt",
    ),
    (
        "22",
        "cleanup --gitive",
        "Stare izolowane workspace'y gitive-isolated",
    ),
    (
        "23",
        "cleanup --venvs-old",
        "Stare venv/.venv: podsumowanie i wybór okresu (30 dni)",
    ),
    (
        "24",
        "projects",
        "Skanuj projekty dev (venv, node_modules, ~/github/*/*)",
    ),
    ("25", "orchestrate", "Zaawansowana orkiestracja napraw (graf problemów)"),
    ("26", "watch", "Monitoring w tle z powiadomieniami"),
    ("27", "report", "Eksport diagnostyki do HTML/Markdown/JSON"),
    ("28", "history", "Historia sesji naprawczych"),
    ("29", "rollback", "Cofanie operacji (undo/list/show)"),
    ("30", "profile", "Profile diagnostyczne (server/desktop/dev)"),
    ("31", "llm", "Lista providerów LLM + linki do kluczy API"),
    ("32", "token set", "Zapisz klucz API (auto-detekcja providera)"),
    ("33", "config show", "Pokaż konfigurację"),
    ("34", "test-llm", "Test połączenia z LLM"),
    ("35", "ask", "Zadaj pytanie / polecenie w języku naturalnym"),
    ("36", "commands", "Pełna lista wszystkich komend i opcji"),
)
MENU_SHORTCUTS = {number: command for number, command, _ in MENU_ITEMS}


def _command_completion_words(command: click.Command) -> dict[str, Any] | None:
    """Collect subcommand and option words for one click command."""
    words: dict[str, Any] = {}
    if isinstance(command, click.Group):
        for name in sorted(command.commands):
            words[name] = _command_completion_words(command.commands[name])
    for param in getattr(command, "params", []):
        for opt in list(getattr(param, "opts", [])) + list(
            getattr(param, "secondary_opts", [])
        ):
            words.setdefault(opt, None)
    return words or None


def get_command_completer() -> NestedCompleter:
    """Build a nested completer from the live click command tree."""
    from fixos.cli.main import cli

    words: dict[str, Any] = {
        name: _command_completion_words(command)
        for name, command in sorted(cli.commands.items())
    }
    words.update(
        {"commands": None, "clear": None, "menu": None, "exit": None, "quit": None}
    )
    return NestedCompleter.from_nested_dict(words)


def print_interactive_menu() -> None:
    """Display the interactive quick menu."""
    click.echo()
    click.echo(click.style("═" * 60, fg="cyan"))
    click.echo(click.style("  🎮 FIXOS INTERACTIVE SHELL", fg="cyan", bold=True))
    click.echo(click.style("═" * 60, fg="cyan"))
    click.echo()
    for num, cmd, desc in MENU_ITEMS:
        num_styled = click.style(f"[{num:>2}]", fg="yellow", bold=True)
        cmd_styled = click.style(f"{cmd:<34}", fg="green")
        click.echo(f"  {num_styled} {cmd_styled} {desc}")
    q_styled = click.style("[ q]", fg="yellow", bold=True)
    exit_styled = click.style("exit / quit                       ", fg="white")
    click.echo(f"  {q_styled} {exit_styled} Wyjście z programu")
    click.echo()
    click.echo(
        click.style(
            f"  💡 Wskazówka: wpisz numer [1-{len(MENU_ITEMS)}], komendę lub zapytanie naturalne.",
            fg="bright_black",
        )
    )
    click.echo(
        click.style(
            "     Działa autouzupełnianie TAB i historia strzałkami ↑ / ↓.",
            fg="bright_black",
        )
    )
    click.echo(click.style("─" * 60, fg="cyan"))
    click.echo()


def print_command_catalog() -> None:
    """Print every registered command with its one-line help."""
    from fixos.cli.main import cli

    click.echo(click.style("  📚 Wszystkie komendy fixos:", fg="cyan", bold=True))
    click.echo()
    for name in sorted(cli.commands):
        command = cli.commands[name]
        try:
            short = command.get_short_help_str().splitlines()[0]
        except (AttributeError, IndexError):
            short = ""
        name_styled = click.style(f"{name:<14}", fg="green")
        click.echo(f"  {name_styled} {short}")
        if isinstance(command, click.Group):
            for sub_name in sorted(command.commands):
                sub = command.commands[sub_name]
                try:
                    sub_short = sub.get_short_help_str().splitlines()[0]
                except (AttributeError, IndexError):
                    sub_short = ""
                click.echo(f"    {sub_name:<12} {sub_short}")
    click.echo()
    click.echo(
        click.style(
            "  💡 Każdą komendę możesz uruchomić z flagą --help, np. `cleanup --help`.",
            fg="bright_black",
        )
    )
    click.echo()


@click.command("shell")
@click.pass_context
def shell_cmd(ctx) -> None:
    """Uruchom interaktywny shell fixOS z menu i autouzupełnianiem TAB."""
    run_interactive_shell(ctx)


def run_interactive_shell(ctx: click.Context | None = None) -> None:
    """Run the main interactive prompt loop."""
    from fixos.cli.main import cli

    print_interactive_menu()

    history_file = os.path.expanduser("~/.fixos_history")
    history = FileHistory(history_file)
    completer = get_command_completer()

    style = Style.from_dict(
        {
            "prompt": "#00d7af bold",
        }
    )

    session = PromptSession(
        history=history,
        completer=completer,
        style=style,
    )

    while True:
        try:
            user_input = session.prompt([("class:prompt", "fixos > ")]).strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            click.echo("\nDo widzenia!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "exit"):
            click.echo("Do widzenia!")
            break

        if user_input.lower() in ("menu", "help"):
            print_interactive_menu()
            continue

        if user_input.lower() == "clear":
            click.clear()
            continue

        if user_input.lower() == "commands":
            print_command_catalog()
            continue

        # Check menu shortcuts
        if user_input in MENU_SHORTCUTS:
            target = MENU_SHORTCUTS[user_input]
            if target == "ask":
                try:
                    query = session.prompt([("class:prompt", "zapytaj AI > ")]).strip()
                    if query:
                        user_input = f"ask {shlex.quote(query)}"
                    else:
                        continue
                except (KeyboardInterrupt, EOFError):
                    continue
            elif target == "commands":
                print_command_catalog()
                continue
            else:
                user_input = target

        try:
            args = shlex.split(user_input)
            if not args:
                continue
            click.echo()
            cli.main(args, prog_name="fixos", standalone_mode=False)
            click.echo()
        except SystemExit:
            click.echo()
        except click.ClickException as e:
            e.show()
            click.echo()
        except Exception as e:  # noqa: BLE001 — keep the interactive shell alive after command failure
            click.echo(click.style(f"Błąd wykonania: {e}", fg="red"))
            click.echo()
