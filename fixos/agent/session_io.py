"""
UI/IO operations for HITL session.
All terminal output and input handling.
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from ..utils.terminal import (
    render_md as _render_md,
    console,
    print_cmd_block as _print_cmd_block_rich,
    print_stdout_box,
    print_stderr_box,
)
from ..platform_utils import cancel_signal_timeout, setup_signal_timeout
from .session_core import (
    DiagnosticChoice,
    RemediationAction,
    select_recommended_actions,
)

if TYPE_CHECKING:
    from .session_core import CmdResult


# Global reference to timeout handler and session for reinstatement
_timeout_handler = None
_timeout_seconds = None
_session_ref = None


@contextmanager
def suspend_timeout() -> object:
    """Context manager to temporarily suspend session timeout during user input."""
    global _timeout_handler, _timeout_seconds, _session_ref
    try:
        # Cancel the active timeout
        cancel_signal_timeout()
        yield
    finally:
        # Reinstate timeout with remaining time
        if _timeout_handler and _session_ref:
            from . import get_remaining_time

            remaining = get_remaining_time(_session_ref)
            if remaining > 0:
                setup_signal_timeout(remaining, _timeout_handler)


def _setup_timeout_ref(session, seconds: int, handler) -> None:
    """Store timeout handler, session, and seconds for later reinstatement."""
    global _timeout_handler, _timeout_seconds, _session_ref
    _timeout_handler = handler
    _timeout_seconds = seconds
    _session_ref = session


def print_session_header(
    os_info: dict, pkg_manager: str, model: str, timeout: int, remaining_fn
) -> None:
    """Print session header with system info."""
    from rich.panel import Panel

    header = Text()
    header.append(f"👤 HUMAN-IN-THE-LOOP  |  Model: {model}\n", style="bold cyan")
    header.append(
        f"🖥️  OS: {os_info['system']} {os_info['release']}  |  PM: {pkg_manager}\n",
        style="cyan",
    )
    header.append(f"⏰ Limit tury LLM: {fmt_time(timeout)}", style="dim")
    console.print()
    console.print(Panel(header, border_style="cyan"))


def fmt_time(s: int) -> str:
    """Format seconds as HH:MM:SS."""
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def print_action_menu(
    fixes: list, remaining: int, total_tokens: int, completed_count: int = 0
) -> None:
    """Print the refreshed interactive menu of remaining choices."""
    console.print()
    console.print(
        Rule(
            f"[bold cyan]📋 DOSTĘPNE AKCJE[/bold cyan]  [dim]⏰ {fmt_time(remaining)}  ~{total_tokens} tokenów[/dim]",
            style="cyan",
        )
    )
    if fixes:
        current_finding = None
        for i, action in enumerate(fixes, 1):
            if isinstance(action, DiagnosticChoice):
                label = Text("  ")
                label.append(f"[{i}]", style="bold yellow")
                label.append("  ")
                if action.severity != "UNSPECIFIED":
                    label.append(f"{action.severity}  ", style="bold red")
                label.append(f"Problem {action.source_number}: {action.title}")
                console.print(label)
                console.print(
                    "     [dim cyan]Wybierz ten skrót, aby przygotować "
                    "plan naprawy tylko dla tego problemu.[/dim cyan]"
                )
            elif isinstance(action, RemediationAction):
                if action.finding_ref != current_finding:
                    current_finding = action.finding_ref
                    finding = Text()
                    finding.append(f"\n  {action.severity} ", style="bold red")
                    finding.append(action.finding_title, style="bold")
                    finding.append(
                        f"  [{action.category} · {action.finding_ref}]", style="dim"
                    )
                    console.print(finding)

                label = Text("  ")
                label.append(f"[{i}]", style="bold yellow")
                label.append("  ")
                if action.recommended:
                    label.append("ZALECANE  ", style="bold green")
                label.append(action.label)
                label.append(f"  ryzyko: {action.risk}", style="dim")
                console.print(label)

                targets = Text("     Cele/ścieżki: ", style="bold cyan")
                if action.affected_targets:
                    targets.append("  •  ".join(action.affected_targets))
                else:
                    targets.append(
                        "niezadeklarowane przez odpowiedź legacy; "
                        "sprawdź komendę poniżej",
                        style="bold yellow",
                    )
                console.print(targets)
                effect = Text("     Skutek: ", style="bold cyan")
                effect.append(action.explanation)
                console.print(effect)
                if action.evidence:
                    evidence = Text("     Dowody: ", style="bold cyan")
                    evidence.append("  •  ".join(action.evidence))
                    console.print(evidence)

                command_lines = []
                for step, command in enumerate(action.commands, 1):
                    command_lines.append(f"# krok {step}/{len(action.commands)}")
                    command_lines.append(command)
                console.print(
                    Panel(
                        Syntax(
                            "\n".join(command_lines),
                            "bash",
                            theme="monokai",
                            word_wrap=True,
                        ),
                        title=Text("Dokładne komendy naprawcze", style="bold cyan"),
                        border_style="dim cyan",
                        padding=(0, 1),
                    )
                )
                if action.verification:
                    console.print(
                        Text(
                            "     Weryfikacja (tylko odczyt): "
                            + "  →  ".join(action.verification),
                            style="dim cyan",
                        )
                    )
            else:
                cmd, comment = action
                label = comment if comment else (
                    f"{cmd[:55]}..." if len(cmd) > 55 else cmd
                )
                console.print(f"  [bold yellow][{i}][/bold yellow] {label}")
                console.print(
                    Panel(
                        Syntax(cmd, "bash", theme="monokai", word_wrap=True),
                        border_style="dim cyan",
                        padding=(0, 1),
                    )
                )
        console.print()
        if all(isinstance(action, RemediationAction) for action in fixes):
            recommended_count = len(select_recommended_actions(fixes))
            console.print(
                "  [bold yellow][A][/bold yellow]  Wykonaj zalecany zestaw dla "
                f"każdego problemu ({recommended_count} zestawów)"
            )
        elif not any(isinstance(action, DiagnosticChoice) for action in fixes):
            console.print(
                f"  [bold yellow][A][/bold yellow]  Wykonaj wszystkie ({len(fixes)} komend)"
            )
        console.print("  [bold yellow][S][/bold yellow]  Pomiń wszystkie")
        console.print(
            f"  [dim]Pozostałe opcje: {len(fixes)}. Wybierz jeden skrót; "
            "po sukcesie lista zostanie odświeżona.[/dim]"
        )
    else:
        if completed_count:
            console.print("  [green](wszystkie optymalizacje zostały zakończone)[/green]")
        else:
            console.print("  [dim](brak wykrytych optymalizacji do wyboru)[/dim]")
    console.print()
    console.print(
        "  [bold yellow][D][/bold yellow]           Opisz własny problem / co chcesz zmienić"
    )
    console.print("  [bold yellow][!cmd][/bold yellow]        Wykonaj własną komendę")
    console.print("  [bold yellow][search <q>][/bold yellow]  Szukaj zewnętrznie")
    console.print(
        "  [bold yellow][?][/bold yellow]           Zapytaj o więcej szczegółów"
    )
    console.print("  [bold yellow][Q][/bold yellow]           Zakończ sesję")
    console.print(Rule(style="cyan"))


def ask_user_problem() -> str:
    """Interactively asks the user to describe their problem."""
    body = Text()
    body.append(
        "Napisz co chcesz naprawić, zmienić lub co nie działa.\n", style="white"
    )
    body.append("Możesz pisać po polsku lub angielsku.\n\n", style="dim")
    body.append("Przykłady:\n", style="bold cyan")
    body.append(
        "  - 'brak dźwięku po aktualizacji'\n"
        "  - 'chcę przyspieszyć uruchamianie systemu'\n"
        "  - 'wifi nie działa po uśpieniu'\n"
        "  - 'chcę zainstalować sterowniki NVIDIA'\n"
        "  - 'dysk jest prawie pełny, co usunąć'\n"
        "  - 'jak skonfigurować firewall'",
        style="dim",
    )
    console.print()
    console.print(
        Panel(
            body,
            title="[bold cyan]💬 OPISZ SWÓJ PROBLEM[/bold cyan]",
            border_style="cyan",
        )
    )
    try:
        with suspend_timeout():
            return console.input("  [bold cyan]Twój problem:[/bold cyan] ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def print_cmd_preview(cmd: str, comment: str = "") -> None:
    """Shows command in a clear block before execution."""
    _print_cmd_block_rich(cmd, comment=comment)


def print_cmd_result(result: "CmdResult") -> None:
    """Shows command result with colorized markdown."""
    from rich.text import Text

    if result.skipped:
        console.print(Text(f"⏭️  Pominięto: `{result.cmd}`", style="dim"))
        return

    if result.ok:
        console.print(Text(f"✅  {result.cmd}", style="bold green"))
    else:
        console.print(
            Text(f"❌  (kod {result.returncode})  {result.cmd}", style="bold red")
        )

    if result.stdout.strip():
        print_stdout_box(result.stdout, max_lines=40)
    elif not result.ok and not result.stderr.strip():
        console.print("[dim](brak stdout)[/dim]")

    if result.stderr.strip() and not result.ok:
        print_stderr_box(result.stderr)
    console.print()


def print_session_summary(
    messages_count: int, elapsed: int, total_tokens: int, executed: list
) -> None:
    """Print session summary."""
    ok_count = sum(1 for r in executed if r.ok)
    console.print(
        f"\n  [bold cyan]📊 Sesja:[/bold cyan] {messages_count} tur | {fmt_time(elapsed)} | "
        f"~{total_tokens} tokenów | [green]{ok_count}[/green]/[red]{len(executed)}[/red] komend OK"
    )


def print_thinking() -> None:
    """Print 'Analyzing...' indicator."""
    console.print("\n  [dim]🧠 Analizuję...[/dim]", end="")


def clear_thinking() -> None:
    """Clear the 'Analyzing...' indicator."""
    console.print(f"\r{' ' * 30}\r", end="")


def print_llm_reply(reply: str) -> None:
    """Render LLM reply with markdown formatting."""
    console.print(Rule(style="dim cyan"))
    _render_md(reply)
    console.print(Rule(style="dim cyan"))


def print_llm_error(e: Exception) -> None:
    """Print LLM error message."""
    console.print(f"\n  [bold red]❌ Błąd LLM:[/bold red] {e}")


def print_blocked_command(cmd: str, reason: str) -> None:
    """Print blocked dangerous command warning."""
    console.print(f"\n  [bold red]⛔ ZABLOKOWANO:[/bold red] {reason}")
    console.print(f"  Komenda: [cyan]`{cmd}`[/cyan]")


def print_timeout() -> None:
    """Print session timeout message."""
    console.print("\n\n  [bold yellow]⏰ Sesja wygasła.[/bold yellow]")


def print_session_ended() -> None:
    """Print session ended message."""
    console.print("\n  [bold green]✅ Sesja zakończona.[/bold green]")


def print_session_interrupted() -> None:
    """Print session interrupted message."""
    console.print("\n  Sesja przerwana.")


def print_executing_all(count: int) -> None:
    """Print executing all recommended command sets message."""
    console.print(
        f"\n  [bold cyan]▶️  Wykonuję {count} zalecanych zestawów...[/bold cyan]\n"
    )


def print_no_commands() -> None:
    """Print no commands available message."""
    console.print("  [dim]Brak komend do wykonania.[/dim]")


def print_select_one() -> None:
    """Explain that diagnosis-only choices must be focused individually."""
    console.print(
        "  [yellow]Wybierz numer jednej optymalizacji; najpierw zostanie "
        "przygotowany jej plan naprawy.[/yellow]"
    )


def print_invalid_option(user_in: str, max_option: int) -> None:
    """Print invalid option message."""
    console.print(
        f"  [yellow]Brak skrótu [{user_in}]. Dostępne skróty: 1–{max_option}[/yellow]"
    )


def print_no_results() -> None:
    """Print no search results message."""
    console.print("  [dim]Brak wyników.[/dim]")


def print_searching() -> None:
    """Print searching message."""
    console.print("  [yellow]🔎 Szukam zewnętrznie...[/yellow]")


def ask_execute_prompt() -> str:
    """Ask user if they want to execute a command."""
    with suspend_timeout():
        return console.input("  [bold]Wykonać?[/bold] \\[Y/n]: ").strip().lower()


def ask_low_confidence_search() -> bool:
    """Ask user if they want to search when LLM is uncertain."""
    with suspend_timeout():
        return console.input(
            "\n  [dim]💡 LLM niepewny – szukać zewnętrznie? [y/N]:[/dim] "
        ).strip().lower() in ("y", "yes", "tak")


def ask_send_data() -> bool:
    """Ask user if they want to send data to LLM."""
    with suspend_timeout():
        ans = console.input("\n  Czy wysłać te dane do LLM? \\[Y/n]: ").strip().lower()
    return ans not in ("n", "no", "nie")


def get_user_input(remaining: int) -> str:
    """Get user input with prompt."""
    try:
        with suspend_timeout():
            return console.input(
                f"\n  [bold cyan]fixos [{fmt_time(remaining)}] ❯[/bold cyan] "
            ).strip()
    except (EOFError, KeyboardInterrupt):
        return ""
