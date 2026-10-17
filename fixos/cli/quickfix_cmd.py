"""
Quickfix command for fixOS CLI - heuristic fixes without LLM
"""

import click
import subprocess
from fixos.plugins.base import Severity


@click.command("quickfix")
@click.option("--dry-run", is_flag=True, default=False, help="Symuluj bez wykonania")
@click.option("--modules", "-m", default=None, help="Moduły: audio,disk,security,...")
def quickfix(dry_run, modules) -> None:
    """
    Natychmiastowe naprawy bez API — baza znanych bugów.

    \b
    Działa offline, zero tokenów. Używa wbudowanych heurystyk
    do naprawy typowych problemów.

    \b
    Przykłady:
      fixos quickfix                    # napraw wszystko co można
      fixos quickfix --dry-run          # podgląd bez wykonywania
      fixos quickfix -m audio,disk      # tylko audio i dysk
    """
    from fixos.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    registry.discover()

    mods = modules.split(",") if modules else None
    click.echo(click.style("Szybka diagnostyka (bez LLM)...", fg="cyan"))

    results = registry.run(modules=mods)
    fixes_found = 0
    fixes_applied = 0

    def _run_quickfix_command(command: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

    for result in results:
        for finding in result.findings:
            if finding.command:
                fixes_found += 1
                click.echo(
                    f"\n  [{finding.severity.value.upper()}] "
                    f"{click.style(finding.title, fg='yellow')}"
                )
                click.echo(f"    {finding.description}")
                if finding.suggestion:
                    click.echo(f"    Sugestia: {finding.suggestion}")
                click.echo(f"    Komenda: {click.style(finding.command, fg='cyan')}")

                if dry_run:
                    click.echo(click.style("    [DRY-RUN] — pominięto", fg="yellow"))
                else:
                    if finding.severity in (Severity.CRITICAL, Severity.WARNING):
                        if click.confirm("    Wykonać?"):
                            try:
                                proc = _run_quickfix_command(finding.command)
                                if proc.returncode == 0:
                                    click.echo(click.style("    OK", fg="green"))
                                    fixes_applied += 1
                                else:
                                    click.echo(
                                        click.style(
                                            f"    FAIL (exit {proc.returncode}): {proc.stderr[:200]}",
                                            fg="red",
                                        )
                                    )
                            except Exception as e:
                                click.echo(click.style(f"    Błąd: {e}", fg="red"))

    click.echo(click.style("\nPodsumowanie quickfix:", fg="cyan"))
    click.echo(f"  Znalezione naprawy: {fixes_found}")
    if not dry_run:
        click.echo(f"  Wykonane: {fixes_applied}")
    click.echo()
