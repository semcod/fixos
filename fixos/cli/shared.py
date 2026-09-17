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
    """
    Click group that intelligently handles typos and routes natural language commands to 'ask'.
    """

    # Common action keywords that indicate a natural language prompt even if a single word
    _NL_ACTION_KEYWORDS = {
        "wylacz",
        "wyłącz",
        "wlacz",
        "włącz",
        "zatrzymaj",
        "usun",
        "usuń",
        "napraw",
        "naprawa",
        "zbadaj",
        "sprawdz",
        "sprawdź",
        "pokaz",
        "pokaż",
        "znajdz",
        "znajdź",
        "wyczysc",
        "wyczyść",
        "start",
        "stop",
        "kill",
        "rm",
        "delete",
        "clean",
        "fix",
        "scan",
        "show",
        "find",
        "list",
    }

    def resolve_command(self, ctx, args) -> tuple[str, click.Command, list[str]]:
        import difflib
        import sys

        cmd_name = args[0] if args else None
        cmd = self.get_command(ctx, cmd_name) if cmd_name else None

        if cmd is None and ctx.token_normalize_func is not None and cmd_name:
            norm_name = ctx.token_normalize_func(cmd_name)
            cmd = self.get_command(ctx, norm_name)
            if cmd is not None:
                cmd_name = norm_name

        if cmd is not None or not args or args[0].startswith("-"):
            return super().resolve_command(ctx, args)

        # 1. Check for command typos using fuzzy matching
        all_commands = self.list_commands(ctx)
        matches = difflib.get_close_matches(cmd_name, all_commands, n=3, cutoff=0.6)

        if matches:
            best_match = matches[0]
            # If running in an interactive terminal, offer to run the matched command
            if sys.stdin.isatty() and not getattr(ctx, "resilient_parsing", False):
                try:
                    if click.confirm(
                        click.style(
                            f"Nieznana komenda '{cmd_name}'. Czy chodziło o '{best_match}'?",
                            fg="yellow",
                        ),
                        default=True,
                    ):
                        return super().resolve_command(ctx, [best_match] + list(args[1:]))
                except (click.Abort, EOFError):
                    pass
            # In non-interactive mode or if rejected, fail cleanly with typo suggestion
            ctx.fail(f"No such command '{cmd_name}'. Did you mean '{best_match}'?")

        # 2. Check if this is a genuine natural language command:
        # - multiple arguments: e.g. `fixos wylacz kontenery`
        # - argument contains spaces: e.g. `fixos "wylacz wszystkie kontenery"`
        # - single word matches known natural language action keywords
        is_natural_language = (
            len(args) > 1
            or " " in cmd_name
            or cmd_name.lower() in self._NL_ACTION_KEYWORDS
        )

        if is_natural_language:
            return super().resolve_command(ctx, ["ask"] + args)

        # 3. Otherwise, unrecognized single token that is not NL nor a close match
        ctx.fail(f"No such command '{cmd_name}'.")

