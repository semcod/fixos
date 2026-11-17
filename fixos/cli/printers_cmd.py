"""``fixos printers`` — diagnose and repair printing (CUPS / Windows spooler)."""

from __future__ import annotations

import json
import subprocess

import click

from fixos.plugins.base import Severity

_COLORS = {
    Severity.CRITICAL: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
    Severity.OK: "green",
}


@click.command("printers")
@click.option("--fix", "apply_fix", is_flag=True, help="Wykonaj proponowane naprawy")
@click.option("--yes", "-y", is_flag=True, help="Nie pytaj przed każdą naprawą")
@click.option(
    "--scan",
    is_flag=True,
    help="Przeskanuj lokalną sieć /24, by odnaleźć drukarkę po adresie MAC",
)
@click.option(
    "--test-print", "test_queue", default=None, help="Wydrukuj stronę testową"
)
@click.option("--json", "as_json", is_flag=True, help="Wynik w formacie JSON")
def printers(apply_fix, yes, scan, test_queue, as_json) -> None:
    """
    Diagnostyka i naprawa drukarek (Linux/macOS: CUPS, Windows: Spooler).

    \b
    Wykrywa m.in. nierozwiązywalną nazwę drukarki sieciowej (np. BRN…),
    nieosiągalny port, wstrzymane kolejki, zablokowane zadania oraz
    przestarzały sterownik, gdy drukarka obsługuje IPP Everywhere.

    \b
    Przykłady:
      fixos printers                       # diagnoza
      fixos printers --scan                # szukaj drukarki w sieci po MAC
      fixos printers --fix                 # napraw (z potwierdzeniem)
      fixos printers --test-print NAZWA    # strona testowa
    """
    from fixos.plugins.builtin.printers import Plugin

    plugin = Plugin(sweep=scan)
    result = plugin.diagnose()

    if as_json:
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        _render(result)

    failed = 0
    if apply_fix:
        for finding in result.findings:
            if not finding.command or finding.severity not in (
                Severity.CRITICAL,
                Severity.WARNING,
            ):
                continue
            click.echo(
                f"\n→ {finding.title}\n  {click.style(finding.command, fg='cyan')}"
            )
            if not yes and not click.confirm("  Wykonać?", default=True):
                continue
            proc = subprocess.run(
                finding.command, check=False, shell=True, text=True, capture_output=True
            )
            if proc.returncode == 0:
                click.echo(click.style("  OK", fg="green"))
            else:
                failed += 1
                click.echo(
                    click.style(
                        f"  FAIL ({proc.returncode}): {proc.stderr[:300]}", fg="red"
                    )
                )

    if test_queue:
        ok, message = plugin.test_print(test_queue)
        click.echo(
            click.style(f"\nStrona testowa: {message}", fg="green" if ok else "red")
        )
        failed += 0 if ok else 1

    if failed:
        raise SystemExit(1)


def _render(result) -> None:
    queues = result.raw_data.get("queues", [])
    click.echo(click.style(f"Drukarki ({len(queues)}):", fg="cyan", bold=True))
    for queue in queues:
        address = queue.get("address") or queue.get("located_address") or "?"
        click.echo(f"  • {queue['name']}  {queue['uri']}  [{address}]")
        if queue.get("model"):
            click.echo(f"      sterownik: {queue['model']}")
    if not result.findings:
        click.echo(click.style("\nBrak problemów.", fg="green"))
    for finding in result.findings:
        color = _COLORS.get(finding.severity, "white")
        click.echo(
            "\n"
            + click.style(
                f"[{finding.severity.value.upper()}] {finding.title}", fg=color
            )
        )
        click.echo(f"  {finding.description}")
        if finding.suggestion:
            click.echo(f"  Sugestia: {finding.suggestion}")
        if finding.command:
            click.echo(f"  Naprawa: {click.style(finding.command, fg='cyan')}")
