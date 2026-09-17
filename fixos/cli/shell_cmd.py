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
    menu_items = [
        ("1", "quick", "Szybka analiza systemu (CPU/RAM/dysk)"),
        ("2", "fix", "Diagnoza i sesja naprawcza z AI (HITL)"),
        ("3", "cleanup", "Czyszczenie dysku i usług (Docker, cache, logi)"),
        ("4", "scan", "Diagnostyka systemu bez AI"),
        ("5", "jetbrains doctor", "Diagnoza PyCharm, WebStorm, IDEA"),
        ("6", "ask", "Zadaj pytanie / polecenie w języku naturalnym"),
        ("7", "config show", "Podgląd konfiguracji i aktywny model"),
        ("8", "commands", "Pełna lista wszystkich komend i opcji"),
    ]
    for num, cmd, desc in menu_items:
        num_styled = click.style(f"[{num}]", fg="yellow", bold=True)
        cmd_styled = click.style(f"{cmd:<18}", fg="green")
        click.echo(f"  {num_styled} {cmd_styled} {desc}")
    q_styled = click.style("[q]", fg="yellow", bold=True)
    exit_styled = click.style("exit / quit       ", fg="white")
    click.echo(f"  {q_styled} {exit_styled} Wyjście z programu")
    click.echo()
    click.echo(
        click.style(
            "  💡 Wskazówka: wpisz numer [1-8], komendę lub zapytanie naturalne.",
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
        except Exception:
            short = ""
        name_styled = click.style(f"{name:<14}", fg="green")
        click.echo(f"  {name_styled} {short}")
        if isinstance(command, click.Group):
            for sub_name in sorted(command.commands):
                sub = command.commands[sub_name]
                try:
                    sub_short = sub.get_short_help_str().splitlines()[0]
                except Exception:
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


MENU_SHORTCUTS = {
    "1": "quick",
    "2": "fix",
    "3": "cleanup",
    "4": "scan",
    "5": "jetbrains doctor",
    "6": "ask",
    "7": "config show",
    "8": "commands",
}


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
            if user_input == "6":
                try:
                    query = session.prompt([("class:prompt", "zapytaj AI > ")]).strip()
                    if query:
                        user_input = f"ask {shlex.quote(query)}"
                    else:
                        continue
                except (KeyboardInterrupt, EOFError):
                    continue
            elif MENU_SHORTCUTS[user_input] == "commands":
                print_command_catalog()
                continue
            else:
                user_input = MENU_SHORTCUTS[user_input]

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
        except Exception as e:
            click.echo(click.style(f"Błąd wykonania: {e}", fg="red"))
            click.echo()
