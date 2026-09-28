"""Inventory-first stale virtualenv cleanup flow."""

import json
import sys
from pathlib import Path

import click

from fixos.cli._cleanup_utils import _format_bytes, _parse_numeric_range_set
from fixos.diagnostics.venv_cleanup import remove_venvs, scan_venvs


def _cleanup_venvs(json_output, dry_run, list_only, yes, *, days=None, path=None):
    interactive = sys.stdin.isatty() and not (
        json_output or dry_run or list_only or yes
    )
    if days is None:
        days = (
            click.prompt(
                "Okres nieaktywności w dniach", default=30, type=click.IntRange(min=1)
            )
            if interactive
            else 30
        )
    if days < 1:
        raise click.BadParameter(
            "Okres musi wynosić co najmniej 1 dzień", param_hint="--days"
        )
    base = Path(path or "~/github").expanduser()
    if not json_output:
        click.echo(f"Skanowanie projektów w {base}, okres: > {days} dni…")
    try:
        report = scan_venvs(base, days)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(report, ensure_ascii=True, indent=2))
        return
    click.echo(f"Znaleziono środowisk venv/.venv: {report['found']}")
    click.echo(
        f"Łączny zmierzony rozmiar: {_format_bytes(report['total_bytes'])}; "
        f"nieznany rozmiar: {report['unknown_sizes']}"
    )
    click.echo(
        f"Do usunięcia: {report['eligible']}; zajęte miejsce: {_format_bytes(report['bytes'])}"
    )
    click.echo(
        "Ocena użycia: daty plików i widoczne procesy użytkownika; nie jest pełną historią użycia."
    )
    candidates = [v for v in report["items"] if v["eligible"]]
    for number, item in enumerate(candidates, 1):
        click.echo(f"  [{number}] {item['path']!a}: {_format_bytes(item['bytes'])}")
    for item in report["items"]:
        if not item["eligible"]:
            click.echo(f"  Chronione {item['path']!a}: {', '.join(item['reasons'])}")
    if report["errors"]:
        click.echo(
            f"Niepełna obserwacja procesów ({len(report['errors'])}); usuwanie zablokowane."
        )
    if dry_run or list_only:
        click.echo("DRY-RUN — bez usuwania." if dry_run else "LISTA — bez usuwania.")
        return
    if not candidates:
        return
    if yes:
        selected = candidates
    else:
        raw = click.prompt("Wybierz numery (np. 1,3-5), all lub 0", default="0")
        numbers = (
            set(range(1, len(candidates) + 1))
            if raw.strip().lower() == "all"
            else _parse_numeric_range_set(raw)
        )
        if any(n < 0 or n > len(candidates) for n in numbers):
            raise click.BadParameter("Numer spoza listy")
        selected = [v for n, v in enumerate(candidates, 1) if n in numbers]
        if not selected or not click.confirm(
            f"Usunąć {len(selected)} środowisk ({_format_bytes(sum(v['bytes'] for v in selected))})? "
            "Zależności trzeba będzie zainstalować ponownie",
            default=False,
        ):
            click.echo("Anulowano — niczego nie usunięto.")
            return
    removed = 0
    size = 0
    failed = 0
    groups = {}
    for item in selected:
        groups.setdefault(item["project"], []).append(item)
    for group in groups.values():
        group_removed = 0
        try:
            for item in remove_venvs(group, days):
                removed += 1
                group_removed += 1
                size += item["bytes"]
                click.echo(f"Usunięto: {item['path']!a}")
        except (OSError, ValueError) as exc:
            failed += len(group) - group_removed
            click.echo(f"Przerwano projekt {group[0]['project']!a}: {exc}")
    click.echo(
        f"Usunięto {removed}/{len(selected)}; rozmiar usuniętych środowisk ze skanu: {_format_bytes(size)}"
    )
    if failed:
        raise click.ClickException(
            f"Nie usunięto {failed} środowisk; sprawdź powody i ponów skan."
        )
