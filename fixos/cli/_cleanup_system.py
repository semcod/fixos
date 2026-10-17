"""Full-system storage analysis and cleanup CLI handlers."""

from __future__ import annotations

import subprocess

import click

from fixos.cli._cleanup_utils import (
    _format_bytes,
    _build_dep_types,
    _parse_numeric_range_set,
)
from fixos.cli._cleanup_snap import _handle_snap_management
from fixos.cli._cleanup_home import _handle_home_analysis
from fixos.constants import (
    DEFAULT_COMMAND_TIMEOUT,
    DEV_PROJECT_OLD_DAYS,
    MIN_STALE_DAYS,
)


# ── Query handlers for interactive select mode ───────────────────────────


def _query_info(nums: str, analyzer) -> None:
    """Handle info:N query in select mode."""
    try:
        idx = int(nums[5:])
        if 1 <= idx <= len(analyzer.items):
            item = analyzer.items[idx - 1]
            click.echo(
                f"\n{click.style('📦 SZCZEGÓŁY ELEMENTU:', fg='yellow', bold=True)}"
            )
            click.echo(f"  Nazwa:     {item.name}")
            click.echo(f"  Ścieżka:   {item.path}")
            click.echo(f"  Rozmiar:   {_format_bytes(item.size_bytes)}")
            click.echo(f"  Kategoria: {item.category}")
            click.echo(f"  Ryzyko:    {item.risk}")
            click.echo(f"  Komenda:   {click.style(item.cleanup_command, fg='cyan')}")
            click.echo(f"  Opis:      {item.description}")
        else:
            click.echo(click.style(f"❌ Nieprawidłowy numer: {idx}", fg="red"))
    except ValueError:
        click.echo(click.style("❌ Format: info:N (np. info:5)", fg="red"))


def _query_path(nums: str, analyzer) -> None:
    """Handle path:N query in select mode."""
    import os

    try:
        idx = int(nums[5:])
        if 1 <= idx <= len(analyzer.items):
            item = analyzer.items[idx - 1]
            click.echo(f"\n{click.style('📁 ŚCIEŻKA:', fg='yellow')}")
            click.echo(f"  {item.path}")
            if os.path.exists(item.path):
                click.echo(click.style("  ✅ Istnieje", fg="green"))
            else:
                click.echo(click.style("  ⚠️ Nie istnieje", fg="yellow"))
        else:
            click.echo(click.style(f"❌ Nieprawidłowy numer: {idx}", fg="red"))
    except ValueError:
        click.echo(click.style("❌ Format: path:N (np. path:5)", fg="red"))


def _query_cmd(nums: str, analyzer) -> None:
    """Handle cmd:N query in select mode."""
    try:
        idx = int(nums[4:])
        if 1 <= idx <= len(analyzer.items):
            item = analyzer.items[idx - 1]
            click.echo(f"\n{click.style('🔧 KOMENDA CZYSZCZENIA:', fg='yellow')}")
            click.echo(f"  {click.style(item.cleanup_command, fg='cyan')}")
            if item.risk in ["none", "low"]:
                click.echo(click.style("  ✅ Bezpieczne", fg="green"))
            else:
                click.echo(click.style("  ⚠️ Wymaga ostrożności", fg="yellow"))
        else:
            click.echo(click.style(f"❌ Nieprawidłowy numer: {idx}", fg="red"))
    except ValueError:
        click.echo(click.style("❌ Format: cmd:N (np. cmd:5)", fg="red"))


def _query_filter(nums: str, analyzer) -> None:
    """Handle filter:TYPE query in select mode."""
    filter_type = nums[7:].strip()
    filtered_items = [
        item
        for item in analyzer.items
        if filter_type
        in (item.name.split(" (")[0] if " (" in item.name else item.name).lower()
        or filter_type in item.category.lower()
    ]
    if not filtered_items:
        click.echo(click.style(f"❌ Brak elementów typu '{filter_type}'", fg="red"))
        return
    click.echo(f"\n{click.style(f'🔍 FILTR: {filter_type}', fg='magenta', bold=True)}")
    risk_icons = {"none": "✅", "low": "🟢", "medium": "🟡", "high": "🔴"}
    for item in filtered_items[:50]:
        original_idx = analyzer.items.index(item) + 1
        click.echo(
            f"  [{original_idx:3d}] {risk_icons.get(item.risk, '•')} {item.name}: {_format_bytes(item.size_bytes)}"
        )
    click.echo(
        click.style(
            f"\n  💰 Łącznie: {_format_bytes(sum(i.size_bytes for i in filtered_items))}",
            fg="green",
        )
    )


_SELECT_QUERY_HANDLERS = [
    ("info:", _query_info),
    ("path:", _query_path),
    ("cmd:", _query_cmd),
    ("filter:", _query_filter),
]


def _handle_select_query(nums: str, analyzer) -> bool:
    """Handle a single interactive query (info:/path:/cmd:/filter:) in select mode.
    Returns True if a special command was handled, False if nums should be parsed as indices."""
    for prefix, handler in _SELECT_QUERY_HANDLERS:
        if nums.startswith(prefix):
            handler(nums, analyzer)
            return True
    return False


# ── Interactive select ────────────────────────────────────────────────────


def _handle_interactive_select(analyzer, dry_run: bool) -> list:
    """Interactive numbered item selection. Returns list of items to clean."""
    click.echo(
        f"\n{click.style('📋 WYBIERZ ELEMENTY DO USUNIĘCIA:', fg='green', bold=True)}"
    )
    click.echo(
        click.style("Podaj numery oddzielone przecinkami (np. 1,3,5-10,15)", fg="white")
    )
    click.echo(click.style("Dodatkowe opcje:", fg="white"))
    click.echo(f"  {click.style('info:N', fg='cyan')}    - pokaż szczegóły elementu N")
    click.echo(
        f"  {click.style('path:N', fg='cyan')}    - pokaż pełną ścieżkę elementu N"
    )
    click.echo(f"  {click.style('cmd:N', fg='cyan')}     - pokaż komendę odtworzenia")
    click.echo(
        f"  {click.style('filter:TYPE', fg='magenta')} - filtruj po typie (np. filter:venv)"
    )

    for i, item in enumerate(analyzer.items[:50], 1):
        risk_icon = {"none": "✅", "low": "🟢", "medium": "🟡", "high": "🔴"}.get(
            item.risk, "•"
        )
        click.echo(
            f"  [{i:3d}] {risk_icon} {item.name}: {_format_bytes(item.size_bytes)}"
        )
    if len(analyzer.items) > 50:
        click.echo(
            f"  ... i {len(analyzer.items) - 50} więcej (użyj filter:TYPE lub top:N)"
        )

    items_to_clean = []
    while True:
        nums = click.prompt(
            click.style(
                "\nWybierz numery (lub info:N/path:N/cmd:N/filter:TYPE)", fg="cyan"
            ),
            default="",
        )
        if not nums.strip():
            break
        nums = nums.strip().lower()
        if _handle_select_query(nums, analyzer):
            continue
        for i in _parse_numeric_range_set(nums):
            if 1 <= i <= len(analyzer.items):
                items_to_clean.append(analyzer.items[i - 1])
        if items_to_clean:
            break

    if not items_to_clean:
        click.echo(click.style("⏭️ Nie wybrano żadnych elementów.", fg="yellow"))
        return []

    items_to_clean = list(dict.fromkeys(items_to_clean))
    total_selected = sum(item.size_bytes for item in items_to_clean)
    click.echo(
        f"\n{click.style('📋 WYBRANE ELEMENTY DO USUNIĘCIA:', fg='red', bold=True)}"
    )
    for i, item in enumerate(items_to_clean, 1):
        risk_icon = {"none": "✅", "low": "🟢", "medium": "🟡", "high": "🔴"}.get(
            item.risk, "•"
        )
        click.echo(
            f"  {i:3d}. {risk_icon} {item.name}: {_format_bytes(item.size_bytes)}"
        )
        click.echo(f"       → {click.style(item.path, fg='cyan', dim=True)}")
    click.echo(
        f"\n{click.style('💰 Łącznie do usunięcia:', fg='red', bold=True)} {_format_bytes(total_selected)}"
    )

    if dry_run:
        click.echo(
            click.style("\n[DRY-RUN] - symulacja, nic nie zostanie usunięte", fg="cyan")
        )
        return items_to_clean
    if not click.confirm(
        click.style("\n⚠️ Potwierdzasz usunięcie tych elementów?", fg="yellow"),
        default=False,
    ):
        click.echo(click.style("⏭️ Anulowano.", fg="yellow"))
        return []
    return items_to_clean


# ── Filter helpers ────────────────────────────────────────────────────────


def _filter_by_age(analyzer, days: int, label: str) -> list:
    """Return items older than *days* and echo a summary."""
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days)
    items = [
        item
        for item in analyzer.items
        if hasattr(item, "last_modified")
        and item.last_modified
        and item.last_modified < cutoff
    ]
    click.echo(
        click.style(
            f"\n🕐 {label} (>{days} dni): {len(items)} sztuk, {_format_bytes(sum(i.size_bytes for i in items))}",
            fg="cyan",
        )
    )
    return items


def _filter_by_prefix_top(selection: str, analyzer) -> list:
    """Handle top:N prefix filter."""
    try:
        n = int(selection[4:])
        items = analyzer.items[:n]
        click.echo(
            click.style(
                f"\n🏆 Top {n} największych: {_format_bytes(sum(i.size_bytes for i in items))}",
                fg="yellow",
            )
        )
        return items
    except ValueError:
        click.echo(
            click.style("❌ Nieprawidłowy format. Użyj top:N (np. top:20)", fg="red")
        )
        return []


def _filter_by_prefix_category(selection: str, analyzer) -> list:
    """Handle category:NAME prefix filter."""
    selected_category = selection[9:].strip()
    items = [item for item in analyzer.items if item.category == selected_category]
    if not items:
        available = sorted({item.category for item in analyzer.items})
        click.echo(
            click.style(
                f"\n❌ Nie znaleziono kategorii '{selected_category}'", fg="red"
            )
        )
        click.echo(
            click.style(f"Dostępne kategorie: {', '.join(available)}", fg="white")
        )
        return []
    click.echo(
        click.style(
            f"\n📁 Kategoria '{selected_category}': {len(items)} elementów, {_format_bytes(sum(i.size_bytes for i in items))}",
            fg="blue",
        )
    )
    return items


def _filter_by_prefix_type(selection: str, analyzer) -> list:
    """Handle type:T1,T2 prefix filter."""
    selected_types = [t.strip() for t in selection[5:].split(",")]
    items = [
        item
        for item in analyzer.items
        if any(
            (item.name.split(" (")[0] if " (" in item.name else item.name) == st
            or st in (item.name.split(" (")[0] if " (" in item.name else item.name)
            for st in selected_types
        )
    ]
    if not items:
        click.echo(
            click.style(
                f"\n❌ Nie znaleziono typów: {', '.join(selected_types)}", fg="red"
            )
        )
        return []
    click.echo(
        click.style(
            f"\n📦 Typy [{', '.join(selected_types)}]: {len(items)} folderów, {_format_bytes(sum(i.size_bytes for i in items))}",
            fg="magenta",
        )
    )
    return items


def _filter_large(analyzer, threshold_bytes: int, label: str) -> list:
    """Filter items above threshold_bytes and print summary."""
    items = [item for item in analyzer.items if item.size_bytes > threshold_bytes]
    click.echo(
        click.style(
            f"\n🔴 {label}: {len(items)} sztuk, {_format_bytes(sum(i.size_bytes for i in items))}",
            fg="red",
        )
    )
    return items


_FILTER_PREFIX_DISPATCH = {
    "top:": _filter_by_prefix_top,
    "category:": _filter_by_prefix_category,
    "type:": _filter_by_prefix_type,
}


def _select_cleanup_items_by_filter(selection: str, analyzer, safe_items: list) -> list:
    """Map a filter keyword to a list of items from the analyzer."""
    if selection == "safe":
        return safe_items
    if selection == "all":
        return analyzer.items
    if selection == "large":
        return _filter_large(analyzer, 1024**3, "Duże elementy (>1 GB)")
    if selection == "huge":
        return _filter_large(analyzer, 5 * 1024**3, "Bardzo duże elementy (>5 GB)")
    if selection == "old":
        return _filter_by_age(analyzer, DEV_PROJECT_OLD_DAYS, "Stare elementy")
    if selection == "stale":
        return _filter_by_age(analyzer, MIN_STALE_DAYS, "Bardzo stare elementy")
    for prefix, handler in _FILTER_PREFIX_DISPATCH.items():
        if selection.startswith(prefix):
            return handler(selection, analyzer)
    return []


# ── Execution ─────────────────────────────────────────────────────────────


def _run_cleanup_item_cmd(cmd_args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd_args,
        capture_output=True,
        text=True,
        timeout=DEFAULT_COMMAND_TIMEOUT,
    )


def _execute_full_cleanup(items_to_clean: list, dry_run: bool) -> None:
    """Execute cleanup commands for a list of StorageItems."""
    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("🚀 WYKONYWANIE CZYSZCZENIA", fg="cyan", bold=True))
    click.echo(f"{click.style('=' * 60, fg='cyan')}\n")

    results = {"success": 0, "failed": 0, "space_reclaimed": 0}
    for item in items_to_clean:
        click.echo(f"\n• {item.name} ({_format_bytes(item.size_bytes)})")
        if dry_run:
            click.echo(
                click.style(
                    f"  [DRY-RUN] Wykonano by: {item.cleanup_command}", fg="cyan"
                )
            )
            results["success"] += 1
            results["space_reclaimed"] += item.size_bytes
            continue
        if item.risk == "medium":
            if not click.confirm(f"  Wykonać {item.cleanup_command}?", default=False):
                click.echo("  ⏭️ Pominięto")
                continue
        click.echo(f"  🚀 Wykonuję: {item.cleanup_command}")
        try:
            result = _run_cleanup_item_cmd(item.cleanup_command.split())
            if result.returncode == 0:
                click.echo(click.style("  ✅ Sukces", fg="green"))
                results["success"] += 1
                results["space_reclaimed"] += item.size_bytes
            else:
                click.echo(click.style(f"  ❌ Błąd: {result.stderr[:100]}", fg="red"))
                results["failed"] += 1
        except Exception as e:
            click.echo(click.style(f"  ❌ Błąd: {e}", fg="red"))
            results["failed"] += 1

    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("📊 PODSUMOWANIE", fg="cyan", bold=True))
    click.echo(click.style(f"{'=' * 60}", fg="cyan"))
    click.echo(f"   ✅ Sukces: {results['success']}")
    click.echo(f"   ❌ Błędy: {results['failed']}")
    if dry_run:
        click.echo(
            click.style(
                f"\n   💰 [DRY-RUN] Zwolniono by: {_format_bytes(results['space_reclaimed'])}",
                fg="cyan",
            )
        )
    else:
        click.echo(
            click.style(
                f"\n   💰 Odzyskano: {_format_bytes(results['space_reclaimed'])}",
                fg="green",
            )
        )
    click.echo(click.style("=" * 60 + "\n", fg="cyan"))


# ── Menu and dispatch ─────────────────────────────────────────────────────


def _show_dep_types(analyzer) -> None:
    """Display detailed breakdown of dev project dependency types."""
    dev_items = [item for item in analyzer.items if item.category == "dev_projects"]
    dep_types = _build_dep_types(dev_items)
    click.echo(f"\n{click.style('📦 SZCZEGÓŁY TYPÓW:', fg='magenta', bold=True)}")
    for dep_type, data in sorted(dep_types.items(), key=lambda x: -x[1]["total"]):
        click.echo(
            f"\n{click.style(dep_type, fg='yellow', bold=True)}: {len(data['items'])} folderów, {_format_bytes(data['total'])}"
        )
        for item in data["items"][:5]:
            click.echo(f"  • {item.path}: {_format_bytes(item.size_bytes)}")
        if len(data["items"]) > 5:
            click.echo(f"  ... i {len(data['items']) - 5} więcej")


def _display_full_system_menu(
    analyzer, analysis: dict, safe_items: list, medium_items: list, dry_run: bool
) -> str:
    """Display recommendations and menu for full system cleanup. Returns user selection."""
    click.echo(f"\n{click.style('=' * 60, fg='cyan')}")
    click.echo(click.style("📋 REKOMENDACJE", fg="cyan", bold=True))
    click.echo(click.style(f"{'=' * 60}", fg="cyan"))

    if dry_run:
        click.echo(
            click.style("\n[TRYB DRY-RUN] - brak faktycznych zmian\n", fg="yellow")
        )

    if safe_items:
        total_safe = sum(item.size_bytes for item in safe_items)
        click.echo(
            f"\n{click.style('✅ BEZPIECZNE (automatyczne):', fg='green', bold=True)}"
        )
        for item in safe_items[:10]:
            click.echo(f"  • {item.name}: {_format_bytes(item.size_bytes)}")
            click.echo(
                f"    → {click.style(item.cleanup_command, fg='cyan', dim=True)}"
            )
        click.echo(
            f"\n  💰 Łącznie: {click.style(_format_bytes(total_safe), fg='green')}"
        )

    if medium_items:
        total_medium = sum(item.size_bytes for item in medium_items)
        click.echo(
            f"\n{click.style('🟡 WYMAGA POTWIERDZENIA:', fg='yellow', bold=True)}"
        )
        for item in medium_items[:5]:
            click.echo(f"  • {item.name}: {_format_bytes(item.size_bytes)}")
            click.echo(
                f"    → {click.style(item.cleanup_command, fg='cyan', dim=True)}"
            )
        click.echo(
            f"\n  💰 Łącznie: {click.style(_format_bytes(total_medium), fg='yellow')}"
        )

    click.echo(f"\n{click.style('-' * 60, fg='cyan')}")
    click.echo(
        f"💰 {click.style('ŁĄCZNIE DO ODZYSKANIA:', fg='green', bold=True)} {analysis['total_reclaimable_human']}"
    )
    click.echo(click.style(f"{'-' * 60}", fg="cyan"))

    dev_items = [item for item in analyzer.items if item.category == "dev_projects"]
    if dev_items:
        dep_types = _build_dep_types(dev_items)
        click.echo(f"\n{click.style('📦 TYPY ZALEŻNOŚCI:', fg='magenta', bold=True)}")
        for dep_type, data in sorted(dep_types.items(), key=lambda x: -x[1]["total"]):
            click.echo(
                f"  {click.style(dep_type, fg='yellow')}: {len(data['items'])} folderów, {_format_bytes(data['total'])}"
            )

    click.echo(f"\n{click.style('Dostępne opcje:', fg='white', bold=True)}")
    click.echo(
        f"  {click.style('safe', fg='green')}             - wykonaj bezpieczne czyszczenie"
    )
    click.echo(
        f"  {click.style('all', fg='yellow')}              - wykonaj wszystko (z potwierdzeniem)"
    )
    click.echo(
        f"  {click.style('type:NAME', fg='magenta')}       - usuń wybrany typ (np. type:venv)"
    )
    click.echo(
        f"  {click.style('type:A,B,C', fg='magenta')}      - usuń wiele typów (np. type:venv,node_modules)"
    )
    click.echo(
        f"  {click.style('category:NAME', fg='blue')}      - usuń kategorię (np. category:dev_projects)"
    )
    click.echo(
        f"  {click.style('large', fg='red')}               - usuń tylko duże (>1 GB)"
    )
    click.echo(
        f"  {click.style('huge', fg='red')}                - usuń tylko bardzo duże (>5 GB)"
    )
    click.echo(
        f"  {click.style('old', fg='cyan')}                - usuń stare (>30 dni od modyfikacji)"
    )
    click.echo(
        f"  {click.style('stale', fg='cyan')}              - usuń bardzo stare (>90 dni)"
    )
    click.echo(
        f"  {click.style('top:N', fg='yellow')}             - usuń N największych (np. top:20)"
    )
    click.echo(
        f"  {click.style('types', fg='cyan')}              - pokaż szczegóły typów"
    )
    click.echo(
        f"  {click.style('select', fg='green')}            - wybierz interaktywnie (po numerach)"
    )
    click.echo(
        f"  {click.style('snap', fg='magenta')}            - zarządzaj pakietami Snap"
    )
    click.echo(
        f"  {click.style('home', fg='yellow')}             - analizuj duże pliki w home"
    )
    click.echo(f"  {click.style('none', fg='white')}              - pomiń")

    return (
        click.prompt(
            click.style("\nTwój wybór", fg="cyan"), default="none", show_default=False
        )
        .strip()
        .lower()
    )


def _dispatch_system_selection(
    selection: str, analyzer, safe_items: list, dry_run: bool
) -> None:
    """Route a system menu selection to the appropriate handler."""
    if selection == "types":
        _show_dep_types(analyzer)
        return
    if selection == "snap":
        _handle_snap_management(analyzer, dry_run)
        return
    if selection == "home":
        _handle_home_analysis(analyzer, dry_run)
        return
    if selection == "select":
        items_to_clean = _handle_interactive_select(analyzer, dry_run)
    else:
        items_to_clean = _select_cleanup_items_by_filter(
            selection, analyzer, safe_items
        )
    if items_to_clean:
        _execute_full_cleanup(items_to_clean, dry_run)


def _cleanup_full_system(json_output: bool, dry_run: bool) -> None:
    """
    Full system storage analysis and cleanup.

    Analizuje cały system: DNF, kernels, logs, Docker, Podman, cache, etc.
    """
    from fixos.diagnostics.storage_analyzer import StorageAnalyzer

    analyzer = StorageAnalyzer()
    click.echo(click.style("\n🔍 Analizuję system...", fg="cyan"))
    analysis = analyzer.analyze_full()

    if json_output:
        import json

        click.echo(json.dumps(analysis, indent=2, default=str))
        return

    click.echo(analyzer.get_summary())
    if not analysis["items"]:
        return

    safe_items = [item for item in analyzer.items if item.risk in ["none", "low"]]
    medium_items = [item for item in analyzer.items if item.risk == "medium"]

    selection = _display_full_system_menu(
        analyzer, analysis, safe_items, medium_items, dry_run
    )

    if selection in ["none", "n", ""]:
        click.echo(click.style("\n⏭️ Nie wybrano żadnych akcji.", fg="yellow"))
        return

    _dispatch_system_selection(selection, analyzer, safe_items, dry_run)
