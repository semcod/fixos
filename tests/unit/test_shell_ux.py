"""Interactive UX contracts: shell completion coverage and cleanup selection."""

import click
import pytest

from fixos.cli.cleanup_cmd import _parse_selection
from fixos.cli.main import cli
from fixos.cli.shell_cmd import (
    MENU_SHORTCUTS,
    get_command_completer,
)


def _words(node):
    """Unwrap a NestedCompleter node into its option names."""
    return set(getattr(node, "options", {}) or {})


class TestCompleterCoverage:
    """The shell completer must expose every registered command and option."""

    def test_all_commands_complete(self):
        options = _words(get_command_completer())
        for name in cli.commands:
            assert name in options, f"command '{name}' missing from completer"

    def test_all_options_complete(self):
        options = get_command_completer().options
        for name, command in cli.commands.items():
            words = _words(options.get(name))
            for param in getattr(command, "params", []):
                for opt in param.opts + param.secondary_opts:
                    assert opt in words, f"{name} {opt} missing from completer"

    def test_group_subcommands_complete(self):
        options = get_command_completer().options
        for name, command in cli.commands.items():
            if not isinstance(command, click.Group):
                continue
            words = _words(options.get(name))
            for sub_name in command.commands:
                assert sub_name in words, f"{name} {sub_name} missing"

    def test_shell_meta_words_present(self):
        options = _words(get_command_completer())
        for word in ("commands", "clear", "menu", "exit", "quit"):
            assert word in options

    def test_completer_survives_new_options(self):
        """Options added after this test (e.g. cleanup -c) complete automatically."""
        words = _words(get_command_completer().options["cleanup"])
        assert "-c" in words or "--category" in words
        assert "--docker-all" in words


class TestMenuShortcuts:
    """Menu shortcuts must resolve to real commands or handled meta words."""

    def test_every_shortcut_resolves(self):
        for shortcut, target in MENU_SHORTCUTS.items():
            if target == "commands":
                continue
            head = target.split()[0]
            assert head in cli.commands, f"shortcut [{shortcut}] -> '{target}'"

    def test_catalog_covers_every_command(self, capsys):
        from fixos.cli.shell_cmd import print_command_catalog

        print_command_catalog()
        out = capsys.readouterr().out
        for name in cli.commands:
            assert name in out, f"'{name}' absent from printed catalog"

    def test_displayed_numbers_execute_the_displayed_commands(self, capsys):
        import re

        from fixos.cli.shell_cmd import print_interactive_menu

        print_interactive_menu()
        out = capsys.readouterr().out
        for number, target in MENU_SHORTCUTS.items():
            assert re.search(rf"\[{number}\]\s+{re.escape(target)}\s", out)
        assert "[1-10]" in out
        assert MENU_SHORTCUTS["9"] == "cleanup --venvs-old"
        assert MENU_SHORTCUTS["10"] == "cleanup --tmp --retention 24h"

    def test_tmp_menu_number_dispatches_to_tmp_cleanup(self, monkeypatch):
        import importlib
        shell = importlib.import_module("fixos.cli.shell_cmd")
        inputs = iter(["10", "q"])
        class Session:
            def __init__(self, **kwargs):
                pass
            def prompt(self, *args):
                return next(inputs)
        called = []
        monkeypatch.setattr(shell, "PromptSession", Session)
        monkeypatch.setattr(cli, "main", lambda args, **kwargs: called.append(args))
        shell.run_interactive_shell()
        assert called == [["cleanup", "--tmp", "--retention", "24h"]]

    def test_welcome_lists_tmp_cleanup_and_policy(self, monkeypatch, capsys):
        import importlib
        main = importlib.import_module("fixos.cli.main")
        monkeypatch.setattr(main, "_print_quick_status", lambda: None)
        main._print_welcome()
        out = capsys.readouterr().out
        assert "fixos cleanup --tmp --retention 24h" in out
        assert "fixos cleanup --policy" in out


class TestParseSelection:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("", set()),
            ("none", set()),
            ("0", set()),
            ("all", {0, 1, 2, 3, 4}),
            ("1", {0}),
            ("1,3,5", {0, 2, 4}),
            ("2-4", {1, 2, 3}),
            ("1,3-4", {0, 2, 3}),
            (" 1 , 3 ", {0, 2}),
            ("9", set()),  # out of range ignored
            ("abc", set()),  # garbage ignored
            ("1,,2", {0, 1}),
            ("4-2", set()),  # reversed range yields nothing
        ],
    )
    def test_parse(self, raw, expected):
        assert _parse_selection(raw, 5) == expected

    def test_range_clamps_to_count(self):
        assert _parse_selection("3-99", 5) == {2, 3, 4}
