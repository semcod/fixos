"""
Cleanup command for fixOS CLI - service data cleanup with detailed flatpak support.

Sub-modules (split from the original monolith):
  _cleanup_utils.py   – shared parsers & formatters
  _cleanup_flatpak.py – Flatpak-specific cleanup
  _cleanup_snap.py    – Snap package management
  _cleanup_home.py    – Home directory analysis
  _cleanup_system.py  – Full-system analysis, filtering, interactive select
"""

import click

from fixos.diagnostics.service_scanner import ServiceDataScanner
from fixos.constants import DEFAULT_CLEANUP_THRESHOLD_MB

# Re-export public symbols used by fixos.cli (backward-compat)
from fixos.cli._cleanup_flatpak import _cleanup_flatpak_detailed  # noqa: F401
from fixos.cli._cleanup_system import _cleanup_full_system


# ── Service display helpers ───────────────────────────────────────────────


def _display_cleanup_summary(plan: dict, threshold: int) -> None:
    """Display cleanup plan summary header."""
    click.echo(click.style(f"\nSkanowanie usług (próg: {threshold} MB)...", fg="cyan"))
    click.echo(click.style(f"{'═' * 60}", fg="cyan"))

    if plan["services_found"] == 0:
        click.echo(click.style("\nNie znaleziono usług powyżej progu.", fg="green"))
        return

    click.echo(f"Znaleziono {plan['services_found']} usług:")
    click.echo(f"  Całkowity rozmiar: {plan['total_size_gb']:.2f} GB")
    click.echo(
        click.style(
            f"  Bezpieczne do usunięcia: {plan['safe_cleanup_gb']:.2f} GB", fg="green"
        )
    )
    click.echo(
        click.style(
            f"  Do rozważenia: {plan['requires_review_gb']:.2f} GB", fg="yellow"
        )
    )
    click.echo(
        click.style(
            f"  Chronione/mieszane (nie do automatycznego usunięcia): "
            f"{plan.get('dangerous_gb', 0):.2f} GB",
            fg="red",
            bold=True,
        )
    )
    reclaimable = plan.get("manager_reported_reclaimable_gb", 0)
    if reclaimable:
        click.echo(
            click.style(
                f"  Odzyskiwalne wg menedżerów usług (informacyjnie, nie plan "
                f"automatyczny): {reclaimable:.2f} GB",
                fg="cyan",
            )
        )
    click.echo()


_RISK_LABELS = {
    "safe": ("(bezpieczne)", "green"),
    "review": ("(do rozważenia)", "yellow"),
    "dangerous": ("(CHRONIONE — dane rzeczywiste lub mieszane)", "red"),
}


def _display_service_item(svc: dict) -> None:
    """Display a single service item with details."""
    size_str = (
        f"{svc['size_gb']:.2f} GB"
        if svc["size_gb"] >= 1
        else f"{svc['size_mb']:.0f} MB"
    )
    risk = svc.get("risk_level") or ("safe" if svc["safe_to_cleanup"] else "review")
    safe_text, safe_color = _RISK_LABELS.get(risk, _RISK_LABELS["review"])

    click.echo(f"  {click.style(svc['name'], fg='yellow', bold=True)} - {size_str}")
    click.echo(f"   {svc['description']}")
    paths = svc.get("details", {}).get("paths") or [svc["path"]]
    if len(paths) > 1:
        click.echo(f"   Ścieżki ({len(paths)}):")
        for path in paths:
            click.echo(f"     • {path}")
    else:
        click.echo(f"   Ścieżka: {svc['path']}")
    click.echo(
        f"   {click.style(safe_text, fg=safe_color, bold=(risk == 'dangerous'))}"
    )

    # Show details for specific services
    if svc.get("details"):
        if svc["service_type"] == "docker" and svc["details"].get("components"):
            usage = svc["details"].get("usage", {})
            if usage:
                click.echo("   Docker (łącznie / aktywne / rozmiar / odzyskiwalne):")
                for kind, row in usage.items():
                    click.echo(
                        f"     • {kind}: {row.get('total', 0)} / "
                        f"{row.get('active', 0)} / {row.get('size_gb', 0):.2f} GB / "
                        f"{row.get('reclaimable_gb', 0):.2f} GB"
                    )
            else:
                click.echo(f"   Komponenty: {svc['details']['components']}")
        elif svc["service_type"] == "ollama" and svc["details"].get("models"):
            models = svc["details"]["models"]
            if models:
                click.echo(
                    f"   Modele: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}"
                )
    click.echo()


def _error_message(result: dict) -> str:
    """Human-readable failure reason, even when the command's own stderr was
    empty (e.g. suppressed with 2>/dev/null inside the cleanup command
    itself) — a bare nonzero exit code beats a silently blank "Błąd: "."""
    error = result.get("error")
    if error:
        return error
    returncode = result.get("returncode")
    if returncode is not None:
        return f"polecenie zakończyło się kodem {returncode} bez komunikatu błędu"
    return "nieznany błąd"


def _execute_safe_cleanup(services: list, scanner) -> float:
    """Execute cleanup for safe-to-remove services. Returns total space freed in GB."""
    total_freed = 0.0
    for svc in services:
        svc_type = svc["service_type"]
        click.echo(f"Czyszczenie {svc_type}...")
        result = scanner.cleanup_service(
            svc_type,
            dry_run=False,
            planned_service=svc,
        )
        if result["success"]:
            freed = result.get("space_freed_gb", 0)
            total_freed += freed
            click.echo(click.style(f"  Zwolniono {freed:.2f} GB", fg="green"))
        else:
            click.echo(click.style(f"  Błąd: {_error_message(result)}", fg="red"))
    return total_freed


def _format_hint_line(hint: str) -> None:
    """Print a single cleanup hint line with appropriate styling."""
    if hint.startswith("  "):
        click.echo(click.style(hint, fg="cyan"))
    elif hint.startswith("🔥") or hint.startswith("🐳") or hint.startswith("🤖"):
        click.echo(click.style(f"\n    {hint}", fg="yellow", bold=True))
    elif hint.startswith("💡"):
        click.echo(click.style(f"    {hint}", fg="green"))
    elif hint.startswith("⚠️"):
        click.echo(click.style(f"    {hint}", fg="red"))
    elif hint.startswith("📊"):
        click.echo(click.style(f"    {hint}", fg="blue"))
    else:
        click.echo(click.style(f"    {hint}", fg="white"))


def _display_service_group(
    service_type: str,
    svcs: list,
    type_map: dict,
    *,
    show_cleanup_commands: bool = True,
) -> None:
    """Display a single service group with cleanup commands and hints."""
    from fixos.diagnostics.service_cleanup import ServiceCleaner

    total_size = sum(s.get("size_gb", 0) for s in svcs)
    click.echo(f"\n  • {service_type.title()}: {total_size:.2f} GB")

    command_key = "cleanup_command" if show_cleanup_commands else "preview_command"
    unique_commands = sorted(
        {s.get(command_key, "") for s in svcs if s.get(command_key)}
    )
    if unique_commands:
        label = "Komenda" if show_cleanup_commands else "Bezpieczny podgląd"
        click.echo(f"    {label}:")
        for cmd in unique_commands[:2]:
            click.echo(f"      {cmd}")
        if len(unique_commands) > 2:
            click.echo(f"      ... (+{len(unique_commands) - 2} more commands)")

    service_enum = type_map.get(service_type.lower())
    if service_enum:
        hints = ServiceCleaner.get_cleanup_hints(service_enum, total_size)
        if hints:
            click.echo()
            for hint in hints:
                _format_hint_line(hint)


def _group_by_service_type(services: list) -> dict:
    groups: dict = {}
    for svc in services:
        service_type = svc.get("service_type", "unknown")
        groups.setdefault(service_type, []).append(svc)
    return groups


def _display_unsafe_services(services: list) -> None:
    """Display services that are worth a look before deleting (reinstallable
    apps, long-unused tool data, unrecognized cache directories)."""
    from fixos.diagnostics.service_scanner import ServiceType

    click.echo()
    click.echo(click.style("Do rozważenia (nie usuwane automatycznie):", fg="yellow"))

    type_map = {
        "flatpak": ServiceType.FLATPAK,
        "generic_cache": ServiceType.GENERIC_CACHE,
    }

    for service_type, svcs in _group_by_service_type(services).items():
        _display_service_group(service_type, svcs, type_map)

    click.echo()
    click.echo(
        click.style(
            "💡 Wskazówki: Powyższe komendy są zwykle bezpieczne (usuwają nieużywane "
            "wersje/runtime) i mogą odzyskać dużo miejsca — warto jednak zerknąć "
            "zanim je uruchomisz",
            fg="green",
        )
    )


def _display_dangerous_services(services: list) -> None:
    """Display services holding real installed application data (models,
    containers/volumes, editor extensions, VM disks) rather than a cache.

    Never auto-cleaned in bulk. Shown separately with an explicit warning so
    it can't be mistaken for one of the "safe" cache entries.
    """
    from fixos.diagnostics.service_scanner import ServiceType

    if not services:
        return

    click.echo()
    click.echo(
        click.style(
            "⚠️  Chronione lub mieszane dane (wymaga świadomego wyboru elementów):",
            fg="red",
            bold=True,
        )
    )
    click.echo(
        click.style(
            "   Ta grupa może łączyć dane aktywne z cache (np. Docker) albo "
            "zawierać modele AI, wolumeny, dyski maszyn wirtualnych i "
            "rozszerzenia. fixOS pokazuje bezpieczny podgląd, ale nie proponuje "
            "już zbiorczego kasowania całej grupy.",
            fg="red",
        )
    )

    type_map = {
        "docker": ServiceType.DOCKER,
        "containerd": ServiceType.CONTAINERD,
        "podman": ServiceType.PODMAN,
        "ollama": ServiceType.OLLAMA,
        "lmstudio": ServiceType.LMSTUDIO,
        "huggingface": ServiceType.HUGGINGFACE,
        "jupyter": ServiceType.JUPYTER,
        "minikube": ServiceType.MINIKUBE,
        "appimage": ServiceType.APPIMAGE,
        "virtualbox": ServiceType.VBOX,
        "vmware": ServiceType.VMWARE,
        "steam": ServiceType.STEAM,
        "cursor": ServiceType.CURSOR,
        "vscode": ServiceType.VSCODE,
    }

    for service_type, svcs in _group_by_service_type(services).items():
        _display_service_group(
            service_type,
            svcs,
            type_map,
            show_cleanup_commands=False,
        )

    click.echo()
    click.echo(
        click.style(
            "   Aby usunąć pojedynczą usługę świadomie: "
            "fixos cleanup -c <usluga> (poprzedź --dry-run, by zobaczyć co zrobi)",
            fg="yellow",
        )
    )


def _single_service_target(service_name: str, scanner) -> dict | None:
    """Resolve ``cleanup -c NAME`` to the safest executable scanned entry.

    Some service types expose both rebuildable cache and protected data.  The
    direct command must pin execution to the cache entry instead of warning
    about extensions/models and then letting a rescan pick whichever entry is
    largest.
    """
    from fixos.diagnostics.service_scanner import ServiceType

    try:
        service_enum = ServiceType(service_name)
    except ValueError:
        return None

    entries = scanner.scan_service(service_enum)
    if not entries:
        return None

    risk_order = {"safe": 0, "review": 1, "dangerous": 2}
    executable = [
        item
        for item in entries
        if item.can_cleanup and item.cleanup_command.strip()
    ]
    candidates = executable or entries
    selected = min(
        candidates,
        key=lambda item: (risk_order.get(item.risk_level, 1), -item.size_mb),
    )
    return {
        "service_type": selected.service_type.value,
        "name": selected.name,
        "path": selected.path,
        "size_mb": selected.size_mb,
        "size_gb": selected.size_gb,
        "description": selected.description,
        "can_cleanup": selected.can_cleanup,
        "cleanup_command": selected.cleanup_command,
        "preview_command": selected.preview_command,
        "safe_to_cleanup": selected.safe_to_cleanup,
        "risk_level": selected.risk_level,
        "impact": selected.impact,
        "items_count": selected.items_count,
        "details": selected.details,
    }


def _cleanup_single_service(
    service_name: str, scanner, json_output: bool, dry_run: bool
) -> None:
    """Handle cleanup of a single specific service."""
    target = _single_service_target(service_name, scanner)

    if json_output:
        result = scanner.cleanup_service(
            service_name,
            dry_run=dry_run,
            planned_service=target,
        )
        import json

        click.echo(json.dumps(result, indent=2, default=str))
        return

    if target is None:
        click.echo(
            click.style(
                f"Nie znaleziono danych {service_name} powyżej progu.",
                fg="yellow",
            )
        )
        return

    if not target["can_cleanup"] or not target["cleanup_command"].strip():
        click.echo(
            click.style(
                f"{target['name']}: zbiorcze czyszczenie jest wyłączone, "
                "ponieważ wpis zawiera chronione dane.",
                fg="yellow",
                bold=True,
            )
        )
        if target.get("preview_command"):
            click.echo(f"  Bezpieczny podgląd: {target['preview_command']}")
        click.echo("  Usuń ręcznie tylko konkretny, wcześniej sprawdzony element.")
        return

    if not dry_run and target.get("risk_level") == "dangerous":
        click.echo(
            click.style(
                f"⚠️  {target['name']} zawiera dane mieszane. fixOS wykona "
                "wyłącznie ograniczoną operację pokazaną poniżej:",
                fg="red",
                bold=True,
            )
        )
        click.echo(f"  {target['cleanup_command']}")
        if not click.confirm(f"Wykonać ograniczone czyszczenie {target['name']}?"):
            click.echo("Anulowano.")
            return

    click.echo(click.style(f"Czyszczenie usługi: {target['name']}", fg="yellow"))
    if dry_run:
        click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))

    result = scanner.cleanup_service(
        service_name,
        dry_run=dry_run,
        planned_service=target,
    )

    if result["success"]:
        if dry_run:
            click.echo(
                click.style(f"Symulacja dla {service_name} zakończona", fg="green")
            )
            if result.get("output"):
                click.echo(f"  {result['output']}")
            if result["space_freed_gb"] > 0:
                estimate = (
                    f"  Szacowane maksimum do odzyskania: "
                    f"{result['space_freed_gb']:.2f} GB"
                )
                if service_name == "docker":
                    estimate += (
                        " (cały odzyskiwalny cache buildów wg Docker; "
                        "filtr >7 dni zwykle usunie mniej)"
                    )
                click.echo(estimate)
        else:
            click.echo(
                click.style(f"Zakończono czyszczenie {service_name}", fg="green")
            )
            if result["space_freed_gb"] > 0:
                click.echo(f"  Zwolniono: {result['space_freed_gb']:.2f} GB")
    else:
        click.echo(click.style(f"Błąd: {_error_message(result)}", fg="red"))
        if result.get("output"):
            click.echo(f"Output: {result['output']}")


# ── Interactive cleanup orchestration ─────────────────────────────────────


def _size_str(svc: dict) -> str:
    return (
        f"{svc['size_gb']:.2f} GB"
        if svc["size_gb"] >= 1
        else f"{svc['size_mb']:.0f} MB"
    )


def _select_safe_services(safe_services: list) -> tuple[str, list]:
    """Choose bulk-safe cleanup, full individual selection, or no cleanup."""
    click.echo(click.style("Bezpieczne do wyczyszczenia:", fg="green"))
    for svc in safe_services:
        click.echo(f"  • {svc['name']}: {_size_str(svc)}")
    safe_total = sum(s["size_gb"] for s in safe_services)

    click.echo()
    click.echo("Co wyczyścić?")
    click.echo(f"  [1] Wszystkie bezpieczne (zwolni {safe_total:.2f} GB)")
    click.echo("  [2] Wybierz pojedyncze spośród wszystkich usług")
    click.echo("  [0] Nic — pomiń")
    choice = click.prompt(
        "Wybór", type=click.Choice(["0", "1", "2"]), default="1", show_choices=False
    )

    if choice == "0":
        return "none", []
    if choice == "1":
        return "safe", safe_services
    return "individual", []


def _selection_description(svc: dict) -> str:
    risk = svc.get("risk_level", "review")
    labels = {
        "safe": "bezpieczne cache",
        "review": "do rozważenia",
        "dangerous": "CHRONIONE/mieszane",
    }
    description = labels.get(risk, "do rozważenia")
    if risk == "dangerous" and svc["service_type"] == "docker":
        reclaimable = svc.get("details", {}).get("usage", {}).get("Build Cache", {})
        reclaimable_gb = float(reclaimable.get("reclaimable_gb", 0))
        if reclaimable_gb:
            description += (
                f"; Docker raportuje {reclaimable_gb:.2f} GB odzyskiwalnego "
                "cache buildów, filtr >7 dni zwykle usunie mniej"
            )
    return description


def _select_individual_services(services: list) -> list:
    """Offer every scanned, executable entry in its displayed order."""
    click.echo(
        click.style(
            "Wybierz kolejno spośród wszystkich możliwych usług:",
            fg="cyan",
        )
    )
    selected = []
    for svc in services:
        label = (
            f"  {svc['name']} ({_size_str(svc)}) " f"[{_selection_description(svc)}]"
        )
        if not svc.get("can_cleanup") or not svc.get("cleanup_command", "").strip():
            click.echo(f"{label} — brak bezpiecznej operacji zbiorczej")
            preview = svc.get("preview_command")
            if preview:
                click.echo(f"    Podgląd: {preview}")
            continue
        if click.confirm(label, default=False):
            selected.append(svc)
    return selected


def _execute_individual_cleanup(services: list, scanner) -> float:
    """Execute hand-picked entries with an extra gate for protected data."""
    total_freed = 0.0
    for svc in services:
        risk = svc.get("risk_level", "review")
        if risk == "dangerous":
            click.echo(
                click.style(
                    f"⚠️  {svc['name']} zawiera dane chronione lub mieszane. "
                    "Operacji nie da się automatycznie cofnąć.",
                    fg="red",
                    bold=True,
                )
            )
            if not click.confirm(
                f"Potwierdź wykonanie dokładnie dla: {svc['name']}",
                default=False,
            ):
                click.echo(f"  Pominięto {svc['name']}.")
                continue

        click.echo(f"Czyszczenie {svc['name']}...")
        result = scanner.cleanup_service(
            svc["service_type"],
            dry_run=False,
            planned_service=svc,
        )
        if result["success"]:
            freed = float(result.get("space_freed_gb", 0))
            total_freed += freed
            click.echo(click.style(f"  Zwolniono {freed:.2f} GB", fg="green"))
        else:
            click.echo(click.style(f"  Błąd: {_error_message(result)}", fg="red"))
    return total_freed


def _run_interactive_cleanup(plan: dict, list_only: bool, scanner) -> None:
    """Offer interactive safe cleanup and display unsafe services."""
    if not list_only and plan["services"]:
        if plan["safe_to_cleanup"]:
            mode, selected = _select_safe_services(plan["safe_to_cleanup"])
        else:
            mode, selected = "individual", []
        if mode == "individual":
            selected = _select_individual_services(plan["services"])
            if selected:
                _execute_individual_cleanup(selected, scanner)
            else:
                click.echo(click.style("Pominięto czyszczenie.", fg="yellow"))
            return
        if selected:
            _execute_safe_cleanup(selected, scanner)
        elif mode == "none":
            click.echo(click.style("Pominięto czyszczenie.", fg="yellow"))
    if plan["requires_review"] and not list_only:
        _display_unsafe_services(plan["requires_review"])
    if plan.get("dangerous") and not list_only:
        _display_dangerous_services(plan["dangerous"])


# ── Main CLI command ──────────────────────────────────────────────────────


@click.command("cleanup")
@click.option(
    "--threshold",
    "-t",
    default=DEFAULT_CLEANUP_THRESHOLD_MB,
    type=int,
    help=f"Próg wielkości w MB (domyślnie {DEFAULT_CLEANUP_THRESHOLD_MB}MB)",
)
@click.option(
    "--services",
    "-s",
    default=None,
    help="Usługi do przeskanowania: docker,ollama,npm,pip,... (domyślnie wszystkie)",
)
@click.option(
    "--json", "json_output", is_flag=True, default=False, help="Wyjście w formacie JSON"
)
@click.option(
    "--cleanup",
    "-c",
    default=None,
    help="Wyczyść konkretną usługę (docker, ollama, npm, ...)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Symuluj czyszczenie bez faktycznego usuwania",
)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    default=False,
    help="Tylko wyświetl listę bez interakcji",
)
@click.option(
    "--full",
    "-f",
    "full_analysis",
    is_flag=True,
    default=False,
    help="Pełna analiza systemu (DNF, kernels, logs, Docker, cache)",
)
def cleanup_services(
    threshold, services, json_output, cleanup, dry_run, list_only, full_analysis
) -> None:
    """
    Skanuje i czyści dane usług przekraczające próg.

    \b
    Wyszukuje dane usług (Docker, Ollama, npm, pip, yarn, pnpm, conda,
    gradle, cargo, go, flutter, android, chrome, vscode, huggingface,
    terraform, snap, flatpak, brew, nix, i wiele innych) które zajmują
    więcej miejsca niż podany próg (domyślnie 500MB) i pozwala je usunąć.

    \b
    Przykłady:
      fixos cleanup                    # skanuj wszystkie usługi
      fixos cleanup -t 1000           # próg 1000MB (1GB)
      fixos cleanup -s docker,ollama  # tylko Docker i Ollama
      fixos cleanup --list              # tylko lista, bez czyszczenia
      fixos cleanup -c docker --dry-run  # symulacja czyszczenia Dockera
      fixos cleanup --full              # pełna analiza systemu
    """
    if full_analysis:
        _cleanup_full_system(json_output, dry_run)
        return

    scanner = ServiceDataScanner(threshold_mb=threshold)

    if cleanup:
        if cleanup == "flatpak":
            _cleanup_flatpak_detailed(scanner, json_output, dry_run)
        else:
            _cleanup_single_service(cleanup, scanner, json_output, dry_run)
        return

    service_filter = services.split(",") if services else None
    plan = scanner.get_cleanup_plan(selected_services=service_filter)

    if json_output:
        import json

        click.echo(json.dumps(plan, indent=2, default=str))
        return

    _display_cleanup_summary(plan, threshold)
    if plan["services_found"] == 0:
        return

    for svc in plan["services"]:
        _display_service_item(svc)

    _run_interactive_cleanup(plan, list_only, scanner)
