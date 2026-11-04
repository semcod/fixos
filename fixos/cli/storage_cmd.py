"""Read-only storage review and local, portable reports. No LLM imports."""

import csv
import html
import io
import json
import math
from pathlib import Path

import click

from fixos.diagnostics.large_files import analyze_large_files


def _cell(value: object) -> str:
    text = str(value)
    return (
        "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else text
    )


def _size(value: int | None) -> str:
    return "?" if value is None else f"{value / 10**9:.3f} GB"


def _display(value: object) -> str:
    text = str(value)
    return (
        text.encode("unicode_escape").decode("ascii")
        if any(ord(c) < 32 or ord(c) == 127 for c in text)
        else text
    )


def render_table(report: dict) -> str:
    scan = report["scan"]
    lines = [
        f"Fixos storage — reguły lokalne, bez LLM; próg >{report['min_bytes_exclusive'] / 10**6:g} MB",
        f"Skan: {scan['status']}; wpisy: {scan['entries_scanned']}; duże pliki: {scan['unique_large_files']}; pokazano: {len(report['files'])}",
        f"Budżet wyczerpany: {scan['budget_exhausted']}; błędy: {scan['errors']}; ucięta lista wyników: {report['results_truncated']}",
        f"Widoczność procesów: {report['process_probe']['status']}; swap: {report['swap_probe']['status']}",
        f"Pominięto: symlinki {scan['symlinks_skipped']}, inne systemy plików {scan['mounts_skipped']}, wirtualne systemy plików {scan['pseudo_filesystems_skipped']}",
        "Rozmiary: GB=10^9 B; logiczny / przydzielone bloki. Odzysk pozostaje niepotwierdzony.",
    ]
    for filesystem in report["filesystems"]:
        lines.append(
            f"Wolne dla użytkownika {_display(filesystem['path'])}: {_size(filesystem['available_bytes'])}; niedostępne/rezerwa: {_size(filesystem['unavailable_or_reserved_bytes'])}"
        )
    order = {"review": 0, "manager-review": 1, "protected": 2}
    for group in sorted(
        report["groups"],
        key=lambda g: (
            order[g["decision"]],
            -(g["allocated_bytes"] or 0),
            g["location"],
        ),
    ):
        lines.append(
            f"\n{group['decision']} | {group['kind']} | {group['files']} plików | {_size(group['logical_bytes'])} / {_size(group['allocated_bytes'])} | {_display(group['location'])}"
        )
        paths = set(group["paths"])
        for row in report["files"]:
            if row["path"] not in paths:
                continue
            lines.append(
                f"  {_size(row['logical_bytes'])} / {_size(row['allocated_bytes'])} | właściciel: {_display(row['owner'])} | mtime: {row['age_days']:g} dni | {_display(row['path'])}"
            )
            lines.append(f"    {row['rule_id']}: " + " ".join(row["reasons"]))
            lines.append("    Dalej: " + row["next_step"])
    if report["process_probe"]["open_deleted_files"]:
        lines.append(
            f"\nOtwarte usunięte pliki: {report['process_probe']['open_deleted_files']}, zaobserwowane bloki: {_size(report['process_probe']['open_deleted_allocated_bytes'])}. Sprawdź usługę i rotację; sam unlink już nie pomoże."
        )
    if not report["files"]:
        lines.append(
            "Brak dużych plików w zaobserwowanym zakresie. Sprawdź status i ograniczenia skanu."
        )
    for error in scan["error_samples"]:
        lines.append(f"Błąd odczytu errno={error['errno']}: {_display(error['path'])}")
    lines.extend("\n" + note for note in report["notes"])
    return "\n".join(lines) + "\n"


def render_html(report: dict) -> str:
    """Portable grouped review with local filtering and an inert selection export."""
    escape = html.escape
    summary = escape(render_table(report).split("\n\n", 1)[0])
    sections = []
    order = {"review": 0, "manager-review": 1, "protected": 2}
    for group in sorted(
        report["groups"],
        key=lambda g: (
            order[g["decision"]],
            -(g["allocated_bytes"] or 0),
            g["location"],
        ),
    ):
        rows = []
        for row in report["files"]:
            if row["path"] not in group["paths"]:
                continue
            reasons = "".join(f"<li>{escape(reason)}</li>" for reason in row["reasons"])
            rows.append(
                '<article><label><input type="checkbox" class="pick" '
                f'data-path="{escape(row["path"], quote=True)}"> Do dalszego przeglądu</label>'
                f"<p><code>{escape(row['path'])}</code></p>"
                f"<p>{_size(row['logical_bytes'])} logicznie / {_size(row['allocated_bytes'])} bloków · "
                f"{escape(row['owner'])} · mtime {row['age_days']:g} dni · {row['link_count']} linków</p>"
                f"<ul>{reasons}</ul><p>Dalej: {escape(row['next_step'])}</p></article>"
            )
        opened = " open" if group["decision"] == "review" else ""
        sections.append(
            f'<details class="group" data-decision="{escape(group["decision"])}"{opened}>'
            f"<summary>{escape(group['decision'])} · {escape(group['kind'])} · {group['files']} plików · "
            f"{_size(group['allocated_bytes'])} bloków · {escape(group['location'])}</summary>"
            + "".join(rows)
            + "</details>"
        )
    return (
        '<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        "<title>Fixos — przegląd dużych plików</title><style>body{max-width:1200px;margin:2em auto;padding:1em;font:16px/1.5 system-ui}"
        "pre,code{white-space:pre-wrap;overflow-wrap:anywhere}details,article{border:1px solid #aaa;padding:1em;margin:.6em 0}"
        "summary{cursor:pointer}input[type=search]{width:50%;padding:.5em}[hidden]{display:none}</style>"
        "<h1>Fixos — przegląd dużych plików</h1><p>Reguły lokalne bez LLM. Wybór tworzy listę do przeglądu; nie usuwa danych.</p>"
        '<label>Filtr <input id="query" type="search" placeholder="Ścieżka, typ lub uzasadnienie"></label> '
        '<select id="decision"><option value="">Wszystkie grupy</option value="review">Do decyzji</option>'
        '<option value="manager-review">Sprawdź menedżera</option><option value="protected">Chronione</option></select> '
        '<button id="export">Pobierz wybrane propozycje</button>'
        f"<pre>{summary}</pre>"
        + "".join(sections)
        + '<script>const q=document.getElementById("query"),d=document.getElementById("decision");'
        'function filter(){for(const g of document.querySelectorAll(".group"))'
        "{g.hidden=(d.value&&g.dataset.decision!==d.value)||!g.textContent.toLocaleLowerCase().includes(q.value.toLocaleLowerCase());}}"
        'q.addEventListener("input",filter);d.addEventListener("change",filter);'
        'document.getElementById("export").addEventListener("click",()=>{'
        'const paths=Array.from(document.querySelectorAll(".pick:checked"),e=>e.dataset.path);'
        'const url=URL.createObjectURL(new Blob([JSON.stringify({schema:"fixos.storage-review-selection/v1",paths,authorizedDelete:false},null,2)],{type:"application/json"}));'
        'const a=document.createElement("a");a.href=url;a.download="fixos-review-selection.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});'
        "</script></html>\n"
    )


def render_report(report: dict, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output_format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(
            [
                "path",
                "kind",
                "decision",
                "owner",
                "logical_bytes",
                "allocated_bytes",
                "link_count",
                "age_days",
                "rule_id",
                "reasons",
                "next_step",
                "scan_status",
                "process_visibility",
            ]
        )
        for row in report["files"]:
            keys = [
                "path",
                "kind",
                "decision",
                "owner",
                "logical_bytes",
                "allocated_bytes",
                "link_count",
                "age_days",
                "rule_id",
            ]
            writer.writerow(
                [_cell(row[key]) if row[key] is not None else "" for key in keys]
                + [
                    _cell(" ".join(row["reasons"])),
                    _cell(row["next_step"]),
                    report["scan"]["status"],
                    report["process_probe"]["status"],
                ]
            )
        return stream.getvalue()
    if output_format == "html":
        return render_html(report)
    return render_table(report)


@click.command("storage")
@click.argument(
    "paths", nargs=-1, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--min-mb",
    default=500.0,
    type=click.FloatRange(min=0),
    show_default=True,
    help="Ściśle powyżej progu, MB=1000000 B.",
)
@click.option(
    "--limit",
    default=50,
    type=click.IntRange(1, 1000),
    show_default=True,
    help="Największe pliki w przeskanowanym zakresie.",
)
@click.option(
    "--max-seconds",
    default=30.0,
    type=click.FloatRange(min=0.01, max=3600),
    show_default=True,
)
@click.option(
    "--max-entries",
    default=200_000,
    type=click.IntRange(1, 5_000_000),
    show_default=True,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv", "html"]),
    default="table",
)
@click.option(
    "--json", "json_output", is_flag=True, help="Wyjście JSON bez dodatkowego tekstu."
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Zapisz raport w nowym pliku; istniejący plik jest chroniony.",
)
def storage(
    paths, min_mb, limit, max_seconds, max_entries, output_format, json_output, output
):
    """Diagnozuj duże pliki i pogrupuj decyzje bez kasowania i bez LLM.

    Domyślnie skanuje HOME, na jednym systemie plików. Podaj / dla hosta lub
    konkretne katalogi dla szybszej analizy. Budżet i błędy są jawne.
    """
    if json_output:
        if output_format not in {"table", "json"}:
            raise click.UsageError("--json nie łączy się z innym --format.")
        output_format = "json"
    if not math.isfinite(min_mb) or not math.isfinite(max_seconds):
        raise click.UsageError("Próg i budżet muszą być liczbami skończonymi.")
    try:
        report = analyze_large_files(
            list(paths) or [Path.home()],
            min_bytes=int(min_mb * 10**6),
            limit=limit,
            max_seconds=max_seconds,
            max_entries=max_entries,
        )
        rendered = render_report(report, output_format)
        if output:
            with output.open("x", encoding="utf-8", newline="") as destination:
                destination.write(rendered)
            click.echo(f"Raport: {output}", err=True)
        else:
            click.echo(rendered, nl=False)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
