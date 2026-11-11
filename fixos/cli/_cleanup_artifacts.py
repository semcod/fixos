"""Inventory-first reclamation of content-addressed stores and build caches."""

import json
import sys
from pathlib import Path

import click

from fixos.cli._cleanup_utils import _format_bytes, _parse_numeric_range_set
from fixos.diagnostics.artifact_store import (
    remove_artifacts,
    scan_artifact_stores,
    scan_build_caches,
    scan_system_targets,
)


def _cleanup_artifacts(
    json_output,
    dry_run,
    list_only,
    yes,
    *,
    paths=None,
    min_age_days=None,
    receipt_dir=None,
    include_build_caches=False,
    include_system=False,
):
    interactive = sys.stdin.isatty() and not (
        json_output or dry_run or list_only or yes
    )
    if min_age_days is None:
        min_age_days = (
            click.prompt(
                "Minimalny wiek wpisu w dniach",
                default=1,
                type=click.IntRange(min=0),
            )
            if interactive
            else 1
        )
    if min_age_days < 0:
        raise click.BadParameter(
            "Wiek musi wynosić co najmniej 0 dni", param_hint="--artifacts-min-age-days"
        )
    roots = [Path(item).expanduser() for item in (paths or [])]
    if not roots and not include_system:
        raise click.UsageError(
            "--artifacts wymaga co najmniej jednej ścieżki "
            "(np. --artifacts ~/github/paxlet-com/artifacts) lub --artifacts-system-wide"
        )
    missing = [str(item) for item in roots if not item.exists()]
    if missing:
        raise click.ClickException(f"Nie znaleziono ścieżek: {', '.join(missing)}")
    if not json_output:
        click.echo(
            f"Skanowanie magazynów artefaktów w {', '.join(str(item) for item in roots)}; "
            f"okres: >= {min_age_days} dni"
        )
    try:
        report = (
            scan_artifact_stores(roots, min_age_days=min_age_days)
            if roots
            else {
                "roots": [],
                "found": 0,
                "eligible": 0,
                "bytes": 0,
                "total_bytes": 0,
                "items": [],
            }
        )
        if include_build_caches:
            caches = scan_build_caches(roots, min_age_days=max(min_age_days, 1))
            report["items"].extend(caches["items"])
            report["found"] += caches["found"]
            report["total_bytes"] += caches["total_bytes"]
            if caches["eligible"]:
                report["eligible"] += caches["eligible"]
                report["bytes"] += caches["bytes"]
        if include_system:
            system = scan_system_targets(min_age_days=min_age_days)
            report["items"].extend(system["items"])
            report["found"] += system["found"]
            report["total_bytes"] += system["total_bytes"]
            if system["eligible"]:
                report["eligible"] += system["eligible"]
                report["bytes"] += system["bytes"]
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(report, ensure_ascii=True, indent=2))
        return
    click.echo(f"Znaleziono wpisów: {report['found']}")
    click.echo(f"Łączny rozmiar: {_format_bytes(report['total_bytes'])}")
    click.echo(
        f"Do odzyskania: {report['eligible']}; zajęte miejsce: {_format_bytes(report['bytes'])}"
    )
    click.echo(
        "Referencje: skan manifestów (digest w treści i ścieżki bezwzględne), symlinki "
        "i indeks Git. Dane prywatne użytkownika i magazyny poświadczeń są zawsze chronione."
    )
    candidates = [item for item in report["items"] if item["eligible"]]
    for number, item in enumerate(candidates, 1):
        click.echo(f"  [{number}] {item['path']!a}: {_format_bytes(item['bytes'])}")
    for item in report["items"]:
        if not item["eligible"]:
            click.echo(f"  Chronione {item['path']!a}: {', '.join(item['reasons'])}")
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
        selected = [item for n, item in enumerate(candidates, 1) if n in numbers]
        if not selected or not click.confirm(
            f"Usunąć {len(selected)} wpisów "
            f"({_format_bytes(sum(item['bytes'] for item in selected))})? "
            "Wpisy bez referencji trzeba będzie odtworzyć lub pobrać ponownie",
            default=False,
        ):
            click.echo("Anulowano — niczego nie usunięto.")
            return
    result = remove_artifacts(selected, receipt_dir=receipt_dir)
    click.echo(
        f"Usunięto {len(result['removed'])}/{len(selected)}; "
        f"zwolniono {_format_bytes(result['freed_bytes'])}"
    )
    if result.get("receipt"):
        click.echo(f"Receipt: {result['receipt']}")
    if result["skipped"]:
        for item in result["skipped"]:
            click.echo(f"  Pominięto {item['path']!a}: {', '.join(item['reasons'])}")
        raise click.ClickException(
            f"Nie usunięto {len(result['skipped'])} wpisów; sprawdź powody i ponów skan."
        )
