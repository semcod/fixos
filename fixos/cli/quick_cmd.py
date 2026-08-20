"""Fast heuristic diagnostics command."""

from __future__ import annotations

import json
import sys
from typing import Any

import click


def _human_bytes(value: int | float, *, signed: bool = False) -> str:
    sign = ""
    amount = float(value)
    if signed:
        sign = "+" if amount > 0 else ("−" if amount < 0 else "")
        amount = abs(amount)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            precision = 0 if unit in ("B", "KB") else 2
            return f"{sign}{amount:.{precision}f} {unit}"
        amount /= 1024
    return f"{sign}{amount:.2f} TB"


def render_quick_snapshot(snapshot: dict[str, Any], *, compact: bool = False) -> None:
    """Render the quick snapshot in a stable, readable form."""
    resources = snapshot["resources"]
    context = snapshot["context"]
    safe = snapshot["safe_reclaim"]
    growth = snapshot["growth"]

    click.echo()
    click.echo(click.style("Szybka analiza lokalna", fg="cyan", bold=True))
    stack = ", ".join(context["tech_stack"]) or "brak wykrytego stosu"
    click.echo(
        f"  System: {context['distribution']} · profil {context['profile']} · {stack}"
    )
    click.echo(
        "  Zasoby: "
        f"CPU {resources['cpu']['percent']:.0f}% · "
        f"RAM {resources['memory']['percent']:.0f}% · "
        f"dysk {resources['disk']['percent']:.0f}% "
        f"({_human_bytes(resources['disk']['free_bytes'])} wolne)"
    )
    complete_note = "" if safe["measurement_complete"] else " (częściowy pomiar)"
    click.echo(
        click.style(
            f"  Bezpieczne cache: do {_human_bytes(safe['estimated_max_bytes'])}"
            f"{complete_note}",
            fg="green",
            bold=True,
        )
    )

    if not compact:
        for item in safe["items"][:6]:
            if item["size_bytes"] <= 0:
                continue
            click.echo(f"    • {item['label']}: {_human_bytes(item['size_bytes'])}")
        incomplete = [
            item["label"]
            for item in safe["items"] + snapshot["review"]
            if not item.get("complete", True)
        ]
        if incomplete:
            click.echo(
                click.style(
                    f"    Niezmierzone w krótkim budżecie: {', '.join(incomplete)}",
                    fg="yellow",
                )
            )
        review = [item for item in snapshot["review"] if item["size_bytes"] > 0]
        if review:
            review_text = ", ".join(
                f"{item['label']} ({_human_bytes(item['size_bytes'])})"
                for item in review[:3]
            )
            click.echo(
                click.style(
                    f"  Do decyzji: {review_text}",
                    fg="yellow",
                )
            )

    if growth["status"] == "baseline_created":
        click.echo(f"  Trend: {growth['message']}")
    else:
        click.echo(
            f"  Zmiana od {growth['since']}: "
            f"dysk {_human_bytes(growth['disk_delta_bytes'], signed=True)}, "
            f"RAM {_human_bytes(growth['memory_delta_bytes'], signed=True)}"
        )
        if growth["cache_growth"]:
            labels = {
                item["id"]: item["label"] for item in safe["items"] + snapshot["review"]
            }
            growing = ", ".join(
                f"{labels.get(item['id'], item['id'])} "
                f"{_human_bytes(item['delta_bytes'], signed=True)}"
                for item in growth["cache_growth"][:3]
            )
            click.echo(f"  Urosło: {growing}")
        today = growth.get("today", {})
        if (
            not compact
            and today.get("status") == "compared"
            and today.get("since") != growth.get("since")
        ):
            click.echo(
                f"  Dzisiaj od {today['since']}: "
                f"dysk {_human_bytes(today['disk_delta_bytes'], signed=True)}, "
                f"RAM {_human_bytes(today['memory_delta_bytes'], signed=True)}"
            )

    for alert in snapshot["alerts"]:
        color = "red" if alert["severity"] == "critical" else "yellow"
        click.echo(
            click.style(f"  {alert['severity'].upper()}: {alert['message']}", fg=color)
        )
    top_processes = resources.get("top_processes", [])
    if top_processes:
        click.echo("  Najbardziej obciążające procesy teraz:")
        limit = 3 if compact else 5
        for item in top_processes[:limit]:
            click.echo(
                f"    • {item['name']} (PID {item['pid']}): "
                f"CPU {item['cpu_percent']:.1f}% · "
                f"RAM {item['memory_percent']:.1f}%"
            )
    click.echo(f"  Wynik w {snapshot['duration_ms']} ms (bez LLM).")


def _run_deep_analysis() -> dict[str, Any]:
    from fixos.diagnostics.service_scanner import ServiceDataScanner

    scanner = ServiceDataScanner()
    return scanner.get_cleanup_plan()


def _display_deep_plan(plan: dict[str, Any]) -> None:
    from fixos.cli.cleanup_cmd import _display_cleanup_summary, _display_service_item
    from fixos.constants import DEFAULT_CLEANUP_THRESHOLD_MB

    _display_cleanup_summary(plan, DEFAULT_CLEANUP_THRESHOLD_MB)
    for service in plan.get("services", []):
        _display_service_item(service)
    click.echo(
        click.style(
            "To był tylko podgląd. Aby wybrać czyszczenie: fixos cleanup",
            fg="cyan",
        )
    )


def _is_interactive_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


@click.command("quick")
@click.option(
    "--hours",
    type=click.IntRange(1, 168),
    default=6,
    show_default=True,
    help="Okno historii używane do porównania wzrostu zasobów.",
)
@click.option("--json", "json_output", is_flag=True, help="Zwróć wynik jako JSON.")
@click.option(
    "--deep",
    is_flag=True,
    help="Po szybkim wyniku wykonaj pełny, wolniejszy skan usług i danych.",
)
@click.option(
    "--no-save",
    is_flag=True,
    help="Nie zapisuj tego pomiaru w lokalnej historii trendów.",
)
def quick(hours: int, json_output: bool, deep: bool, no_save: bool) -> None:
    """Natychmiastowa analiza CPU, RAM, dysku, cache i ostatnich przyrostów.

    Nie używa LLM i nie skanuje rekurencyjnie całego systemu. Pierwsze
    uruchomienie tworzy punkt odniesienia; kolejne pokazują, co przyrosło.
    """
    from fixos.diagnostics.quick_snapshot import collect_quick_snapshot

    snapshot = collect_quick_snapshot(hours=hours, save=not no_save)
    if json_output and not deep:
        click.echo(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return

    if not json_output:
        render_quick_snapshot(snapshot)

    wants_deep = deep
    if not wants_deep and not json_output and _is_interactive_terminal():
        click.echo()
        wants_deep = click.confirm(
            "Uruchomić teraz analizę głęboką? Może potrwać kilka minut",
            default=False,
        )

    if wants_deep:
        if not json_output:
            click.echo(click.style("\nUruchamiam analizę głęboką...", fg="yellow"))
        plan = _run_deep_analysis()
        if json_output:
            click.echo(
                json.dumps(
                    {"quick": snapshot, "deep_cleanup_plan": plan},
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        else:
            _display_deep_plan(plan)
    elif not json_output:
        click.echo(
            click.style(
                "Analiza głęboka jest opcjonalna: fixos quick --deep",
                fg="cyan",
            )
        )
