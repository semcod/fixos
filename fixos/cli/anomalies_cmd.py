"""`fixos anomalies`: report host anomalies, remove only selected stale data."""

from __future__ import annotations

import json
from pathlib import Path

import click

from fixos.cli._cleanup_utils import _format_bytes
from fixos.diagnostics.host_anomalies import GIB, remove_paths, scan_all

_ORDER = {"high": 0, "medium": 1, "review": 2, "safe": 3, "low": 4, "protected": 5}


@click.command("anomalies")
@click.option("--json", "json_output", is_flag=True, help="Wynik maszynowy JSON.")
@click.option(
    "--min-size-gb",
    type=click.FloatRange(min=0.01),
    default=1.0,
    show_default=True,
    help="Minimalny rozmiar katalogu stanu lub indeksu IDE.",
)
@click.option(
    "--min-age-days",
    type=click.IntRange(min=1),
    default=14,
    show_default=True,
    help="Katalog stanu jest kandydatem, gdy nic w nim nie zmieniono tyle dni.",
)
@click.option(
    "--remove",
    "remove",
    multiple=True,
    type=click.Path(path_type=Path),
    help="Usuń wskazany katalog; tylko jeśli bieżący skan oznacza go jako usuwalny.",
)
@click.option(
    "--remove-safe",
    is_flag=True,
    help="Usuń wszystkie pozycje 'safe' (indeksy IDE, gdy IDE nie działa).",
)
@click.option("--dry-run", is_flag=True, help="Pokaż, co zostałoby usunięte.")
def anomalies(json_output, min_size_gb, min_age_days, remove, remove_safe, dry_run):
    """Wykrywa anomalie hosta, których nie widzi zwykłe czyszczenie cache.

    \b
    Sprawdza: usługi systemd w pętli restartów, logi kontenerów bez rotacji,
    duże nieużywane katalogi w ~/.local/state i ~/.local/share, indeksy IDE
    oraz procesy zombie i grupy osieroconych procesów.

    \b
    Przykłady:
      fixos anomalies                       # raport
      fixos anomalies --json                # raport maszynowy
      fixos anomalies --remove-safe         # usuń indeksy niedziałających IDE
      fixos anomalies --remove ~/.local/state/x/backups --dry-run
    """
    report = scan_all(min_bytes=int(min_size_gb * GIB), min_age_days=min_age_days)
    findings = report["findings"]
    targets = [path.expanduser() for path in remove]
    if remove_safe:
        targets += [
            Path(f["subject"])
            for f in findings
            if f["removable"] and f["severity"] == "safe"
        ]
    if targets:
        if dry_run:
            report["would_remove"] = [
                str(path)
                for path in targets
                if any(f["removable"] and f["subject"] == str(path) for f in findings)
            ]
        else:
            report["removal"] = remove_paths(
                targets,
                findings,
                receipt_dir=Path.home() / ".local/state/fixos/receipts",
            )
    if json_output:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if not findings:
        click.echo("Nie wykryto anomalii.")
    for item in sorted(findings, key=lambda f: _ORDER.get(f["severity"], 9)):
        click.echo(f"[{item['severity']}] {item['category']}: {item['subject']}")
        click.echo(f"    {item['detail']}")
        for command in item["suggested_commands"]:
            click.echo(f"    $ {command}")
    click.echo(
        f"\nDo odzyskania po przeglądzie: {_format_bytes(report['reclaimable_bytes'])}"
    )
    for path in report.get("would_remove", []):
        click.echo(f"[DRY-RUN] rm -rf {path}")
    removal = report.get("removal")
    if removal:
        for item in removal["removed"]:
            click.echo(f"usunięto: {item['path']}")
        for item in removal["refused"]:
            click.echo(f"pominięto: {item['path']} ({item['reason']})")
        click.echo(f"Zwolniono: {_format_bytes(removal['freed_bytes'])}")
