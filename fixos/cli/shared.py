"""
Shared utilities for fixOS CLI commands
"""

import click

from fixos import __version__

_BANNER_TEMPLATE = r"""
  ___  _       ___  ____
 / _(_)_  __  / _ \/ ___|
| |_| \ \/ / | | | \___ \
|  _| |>  <  | |_| |___) |
|_| |_/_/\_\  \___/|____/
  AI-powered OS Diagnostics  •  v{version}
"""


def get_banner() -> str:
    """Return the CLI banner with the installed package version."""
    return _BANNER_TEMPLATE.format(version=__version__)


BANNER = get_banner()

COMMON_OPTIONS = [
    click.option(
        "--provider",
        "-p",
        default=None,
        help="Provider LLM: gemini|openai|xai|openrouter|ollama",
    ),
    click.option(
        "--token",
        "-t",
        default=None,
        envvar="API_KEY",
        help="Klucz API (override .env)",
    ),
    click.option("--model", "-m", default=None, help="Nazwa modelu LLM"),
    click.option("--no-banner", is_flag=True, default=False),
]


def add_common_options(fn) -> object:
    """Decorator adding common LLM options to a Click command."""
    for opt in reversed(COMMON_OPTIONS):
        fn = opt(fn)
    return fn


def add_shared_options(func) -> object:
    """Shared options for both scan and fix commands."""
    func = click.option(
        "--show-raw",
        "show_raw",
        is_flag=True,
        default=False,
        help="Pokaż surowe dane diagnostyczne (JSON)",
    )(func)
    func = click.option(
        "--disc",
        is_flag=True,
        default=False,
        help="Analiza zajętości dysku + grupowanie przyczyn",
    )(func)
    func = click.option(
        "--disk",
        "disc",
        is_flag=True,
        default=False,
        help="Analiza zajętości dysku (alias do --disc)",
    )(func)
    func = click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="Symuluj wykonanie komend bez faktycznego uruchamiania",
    )(func)
    func = click.option(
        "--interactive/--no-interactive",
        default=True,
        help="Tryb interaktywny (pytaj przed każdą akcją)",
    )(func)
    func = click.option(
        "--json",
        "json_output",
        is_flag=True,
        default=False,
        help="Wyjście w formacie JSON",
    )(func)
    func = click.option(
        "--yaml",
        "yaml_output",
        is_flag=True,
        default=False,
        help="Wyjście w formacie YAML (pipe-safe: logi na stderr)",
    )(func)
    func = click.option(
        "--llm-fallback/--no-llm-fallback",
        default=True,
        help="Użyj LLM gdy heurystyki nie wystarczą",
    )(func)
    return func


class NaturalLanguageGroup(click.Group):
    """Click group that routes unknown commands to 'ask' command."""

    def resolve_command(self, ctx, args) -> tuple[str, click.Command, list[str]]:
        cmd_name = args[0] if args else None
        cmd = self.get_command(ctx, cmd_name) if cmd_name else None
        if cmd is None and args and not args[0].startswith("-"):
            return super().resolve_command(ctx, ["ask"] + args)
        return super().resolve_command(ctx, args)
