"""
Interactive shell (REPL) and menu for fixOS CLI.
Provides tab-completion, command history, quick menu, and natural language query support.
"""

from __future__ import annotations

import os
import shlex
import sys
from typing import Any

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style


def get_command_completer() -> NestedCompleter:
    """Build a nested completer for all fixOS commands and common options."""
    return NestedCompleter.from_nested_dict({
        "quick": {"--hours": None, "--json": None, "--deep": None, "--help": None},
        "fix": {
            "--modules": None,
            "--dry-run": None,
            "--json": None,
            "--yaml": None,
            "--help": None,
        },
        "cleanup": {
            "--docker-all": None,
            "--docker-old": None,
            "--docker-networks": None,
            "--docker-stale-services": None,
            "--orphaned-projects": None,
            "--ollama-old": None,
            "--dry-run": None,
            "--threshold": None,
            "-t": None,
            "--list": None,
            "--full": None,
            "--help": None,
        },
        "scan": {"--modules": None, "--show-raw": None, "--json": None, "--help": None},
        "quickfix": {"--help": None},
        "jetbrains": {"doctor": None, "--help": None},
        "projects": {"--help": None},
        "orchestrate": {"--dry-run": None, "--help": None},
        "watch": {"--help": None},
        "report": {"--help": None},
        "history": {"--help": None},
        "rollback": {"--help": None},
        "profile": {"--help": None},
        "llm": {"--free": None, "--help": None},
        "providers": {"--help": None},
        "token": {"set": None, "show": None, "clear": None, "--help": None},
        "config": {"show": None, "set": None, "init": None, "--help": None},
        "test-llm": {"--help": None},
        "ask": {"--dry-run": None, "--help": None},
        "help": None,
        "clear": None,
        "menu": None,
        "exit": None,
        "quit": None,
    })


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
    ]
    for num, cmd, desc in menu_items:
        num_styled = click.style(f"[{num}]", fg="yellow", bold=True)
        cmd_styled = click.style(f"{cmd:<18}", fg="green")
        click.echo(f"  {num_styled} {cmd_styled} {desc}")
    click.echo(
        f"  {click.style("[q]", fg="yellow", bold=True)} {click.style("exit / quit       ", fg="white")} Wyjście z programu"
    )
    click.echo()
    click.echo(
        click.style(
            "  💡 Wskazówka: wpisz numer [1-7], komendę lub zapytanie naturalne.",
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


MENU_SHORTCUTS = {
    "1": "quick",
    "2": "fix",
    "3": "cleanup",
    "4": "scan",
    "5": "jetbrains doctor",
    "6": "ask",
    "7": "config show",
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

    style = Style.from_dict({
        "prompt": "#00d7af bold",
    })

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
