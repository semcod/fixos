"""Flatpak-specific cleanup CLI handlers."""

from __future__ import annotations

import click

from fixos.cli._cleanup_utils import (
    _format_bytes,
    _parse_selection,
    _parse_size_to_bytes,
)


def _cleanup_flatpak_detailed(scanner, json_output: bool, dry_run: bool) -> None:
    """
    Detailed interactive Flatpak cleanup with menu selection.

    Wyświetla menu z opcjami i pokazuje korzyści na bazie rzeczywistych danych.
    """
    from fixos.diagnostics.flatpak_analyzer import FlatpakAnalyzer

    analyzer = FlatpakAnalyzer()

    # Najpierw wykonaj pełną analizę
    click.echo(click.style("\n🔍 Analizuję Flatpak...", fg="cyan"))
    analysis = analyzer.analyze()

    # JSON output mode
    if json_output:
        import json

        click.echo(json.dumps(analysis, indent=2, default=str))
        return

    # Wyświetl podsumowanie stanu
    _display_flatpak_status(analysis)

    # Pobierz rekomendacje
    recommendations = analyzer.get_cleanup_recommendations()

    if not recommendations:
        click.echo(
            click.style(
                "\n✅ Brak rekomendacji czyszczenia - Flatpak jest w dobrym stanie.",
                fg="green",
            )
        )
        return

    # Wyświetl menu z opcjami
    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("📋 WYBIERZ OPCJE DO WYKONANIA", fg="cyan", bold=True))
    click.echo(click.style(f"{'=' * 60}", fg="cyan"))

    if dry_run:
        click.echo(
            click.style("\n[TRYB DRY-RUN] - brak faktycznych zmian\n", fg="yellow")
        )

    # Wyświetl każdą opcję z korzyściami
    total_potential_savings = 0
    for i, rec in enumerate(recommendations, 1):
        priority_icon = {
            "critical": "💣",
            "high": "🔥",
            "medium": "⚠️",
            "low": "💡",
        }.get(rec["priority"], "•")
        risk_color = {
            "none": "green",
            "low": "green",
            "medium": "yellow",
            "high": "red",
        }.get(rec["risk"], "white")

        click.echo(
            f"\n{click.style(f'[{i}]', fg='cyan', bold=True)} {priority_icon} {click.style(rec['description'], fg='yellow', bold=True)}"
        )
        click.echo(f"    Komenda: {click.style(rec['action'], fg='white', dim=True)}")

        # Korzyść na bazie rzeczywistych danych
        savings = rec.get("estimated_savings", "0 B")
        click.echo(f"    {click.style('Korzyść:', fg='green')} ~{savings}")
        total_potential_savings += _parse_size_to_bytes(savings)

        click.echo(
            f"    {click.style('Ryzyko:', fg='white')} {click.style(rec['risk'].upper(), fg=risk_color)}"
        )

        # Dodatkowe info
        if rec.get("items"):
            n_items = len(rec["items"])
            click.echo(
                f"    {click.style(f'Elementów: {n_items}', fg='white', dim=True)}"
            )

    # Podsumowanie potencjalnych korzyści
    click.echo(f"\n{click.style('-' * 60, fg='cyan')}")
    click.echo(
        f"💰 {click.style('ŁĄCZNA POTENCJALNA KORZYŚĆ:', fg='green', bold=True)} ~{_format_bytes(total_potential_savings)}"
    )
    click.echo(click.style(f"{'-' * 60}", fg="cyan"))

    # Menu wyboru
    click.echo(f"\n{click.style('Dostępne opcje:', fg='white', bold=True)}")
    click.echo(
        f"  {click.style('1,2,3...', fg='cyan')} - wybierz konkretne opcje (np. '1,3')"
    )
    click.echo(
        f"  {click.style('all', fg='green')}    - wykonaj wszystkie bezpieczne (ryzyko low/none)"
    )
    click.echo(f"  {click.style('critical', fg='red')} - wykonaj tylko krytyczne")
    click.echo(f"  {click.style('none', fg='yellow')}   - pomiń wszystko")
    click.echo(f"  {click.style('?', fg='white')}      - pokaż szczegóły każdej opcji")

    # Pytaj o wybór
    click.echo()
    selection = click.prompt(
        click.style("Twój wybór", fg="cyan"), default="none", show_default=False
    )

    # Obsłuż '?'
    if selection.strip() == "?":
        _display_detailed_recommendations(recommendations)
        selection = click.prompt(
            click.style("\nTwój wybór", fg="cyan"), default="none", show_default=False
        )

    # Parsuj wybór
    selected_indices = _parse_selection(
        selection,
        len(recommendations),
        priorities=[rec.get("priority", "") for rec in recommendations],
    )

    if not selected_indices:
        click.echo(click.style("\n⏭️ Nie wybrano żadnych akcji.", fg="yellow"))
        return

    # Wykonaj wybrane akcje
    results = {
        "executed": [],
        "skipped": [],
        "failed": [],
        "space_reclaimed": 0,
    }

    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("🚀 WYKONYWANIE WYBRANYCH AKCJI", fg="cyan", bold=True))
    click.echo(f"{click.style('=' * 60, fg='cyan')}\n")

    for idx in selected_indices:
        rec = recommendations[idx]
        click.echo(f"\n[{idx + 1}/{len(recommendations)}] {rec['description']}")

        if dry_run:
            click.echo(
                click.style(f"   [DRY-RUN] Wykonano by: {rec['action']}", fg="cyan")
            )
            results["executed"].append({"action": rec["action"], "dry_run": True})
            savings_bytes = _parse_size_to_bytes(rec.get("estimated_savings", "0 B"))
            results["space_reclaimed"] += savings_bytes
        else:
            click.echo(f"   🚀 Wykonuję: {rec['action']}")
            result = analyzer._execute_cleanup_action(rec)

            if result["success"]:
                results["executed"].append(
                    {
                        "action": rec["action"],
                        "output": result.get("output", ""),
                    }
                )
                results["space_reclaimed"] += result.get("bytes_reclaimed", 0)
                click.echo(click.style("   ✅ Sukces", fg="green"))
            else:
                results["failed"].append(
                    {
                        "action": rec["action"],
                        "error": result.get("error", "Unknown error"),
                    }
                )
                click.echo(
                    click.style(
                        f"   ❌ Błąd: {result.get('error', 'Unknown error')}", fg="red"
                    )
                )

    # Podsumowanie końcowe
    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("📊 PODSUMOWANIE", fg="cyan", bold=True))
    click.echo(click.style(f"{'=' * 60}", fg="cyan"))
    click.echo(f"   ✅ Wykonano: {len(results['executed'])}")
    click.echo(f"   ⏭️ Pominięto: {len(results['skipped'])}")
    click.echo(f"   ❌ Błędy: {len(results['failed'])}")

    freed_gb = results["space_reclaimed"] / (1024**3)
    if dry_run:
        click.echo(
            click.style(f"\n   💰 [DRY-RUN] Zwolniono by: {freed_gb:.2f} GB", fg="cyan")
        )
    else:
        click.echo(click.style(f"\n   💰 Odzyskano: {freed_gb:.2f} GB", fg="green"))

    click.echo(click.style("=" * 60 + "\n", fg="cyan"))


def _display_flatpak_status(analysis: dict) -> None:
    """Wyświetl status Flatpak z rzeczywistymi danymi."""
    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("📊 STATUS FLATPAK", fg="cyan", bold=True))
    click.echo(click.style(f"{'=' * 60}", fg="cyan"))

    # Aplikacje
    apps_count = len(analysis.get("installed_apps", []))
    apps_size = sum(a.get("size_bytes", 0) for a in analysis.get("installed_apps", []))
    click.echo(
        f"\n📱 Aplikacje: {click.style(str(apps_count), fg='yellow')} ({_format_bytes(apps_size)})"
    )

    # Runtimes
    runtimes_count = len(analysis.get("installed_runtimes", []))
    runtimes_size = sum(
        r.get("size_bytes", 0) for r in analysis.get("installed_runtimes", [])
    )
    click.echo(
        f"🔧 Runtime'y: {click.style(str(runtimes_count), fg='yellow')} ({_format_bytes(runtimes_size)})"
    )

    # Repo bloat
    repo_bloat = analysis.get("repo_bloat", {})
    if repo_bloat.get("bloat_detected"):
        click.echo(
            f"\n{click.style('⚠️  PROBLEM: Repo zajmuje za dużo miejsca!', fg='red', bold=True)}"
        )
        click.echo(f"   Repo: {_format_bytes(repo_bloat.get('repo_total_size', 0))}")
        click.echo(
            f"   Aplikacje+Runtime'y: {_format_bytes(repo_bloat.get('installed_size', 0))}"
        )
        click.echo(f"   Ratio: {repo_bloat.get('ratio', 0):.1f}x (powinno być ~1-1.5x)")
        click.echo(
            f"   {click.style('Marnotrawstwo:', fg='red')} {_format_bytes(repo_bloat.get('wasted_size', 0))}"
        )

    # Duplikaty
    duplicates = analysis.get("duplicate_apps", [])
    if duplicates:
        dup_size = sum(d.get("total_size", 0) for d in duplicates)
        click.echo(
            f"\n🔄 Duplikaty aplikacji: {click.style(str(len(duplicates)), fg='yellow')} ({_format_bytes(dup_size)})"
        )
        for dup in duplicates[:3]:
            click.echo(f"   • {dup.get('name', '?')} ({dup.get('count', 0)} wersje)")

    # Nieużywane runtime'y
    unused = analysis.get("unused_runtimes", [])
    if unused:
        unused_size = analysis.get("total_size_unused", 0)
        click.echo(
            f"\n🗑️ Nieużywane runtime'y: {click.style(str(len(unused)), fg='yellow')} ({_format_bytes(unused_size)})"
        )

    # Leftover data
    leftover = analysis.get("leftover_data", [])
    if leftover:
        leftover_size = analysis.get("total_size_leftover", 0)
        click.echo(
            f"\n📁 Dane po odinstalowanych: {click.style(str(len(leftover)), fg='yellow')} ({_format_bytes(leftover_size)})"
        )


def _display_detailed_recommendations(recommendations: list) -> None:
    """Wyświetl szczegółowe informacje o każdej rekomendacji."""
    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("📖 SZCZEGÓŁY REKOMENDACJI", fg="cyan", bold=True))
    click.echo(click.style(f"{'=' * 60}", fg="cyan"))

    for i, rec in enumerate(recommendations, 1):
        click.echo(
            f"\n{click.style(f'[{i}]', fg='cyan', bold=True)} {rec['description']}"
        )
        click.echo(click.style(f"{'-' * 50}", fg="white", dim=True))
        click.echo(f"\n{rec['explanation']}")

        if rec.get("items"):
            click.echo(f"\nElementy do usunięcia ({len(rec['items'])}):")
            for item in rec["items"][:10]:
                name = item.get("name", "?")
                size = item.get("size_human", "?")
                click.echo(f"  • {name} ({size})")
            if len(rec["items"]) > 10:
                click.echo(f"  ... i {len(rec['items']) - 10} więcej")
