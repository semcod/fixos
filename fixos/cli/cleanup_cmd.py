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
    click.echo(f"  Bezpieczne do usunięcia: {plan['safe_cleanup_gb']:.2f} GB")
    click.echo(f"  Wymaga przeglądu: {plan['requires_review_gb']:.2f} GB")
    click.echo()


def _display_service_item(svc: dict) -> None:
    """Display a single service item with details."""
    size_str = (
        f"{svc['size_gb']:.2f} GB"
        if svc["size_gb"] >= 1
        else f"{svc['size_mb']:.0f} MB"
    )
    safe_icon = " " if svc["safe_to_cleanup"] else " "
    safe_text = "(bezpieczne)" if svc["safe_to_cleanup"] else "(wymaga przeglądu)"

    click.echo(
        f"{safe_icon} {click.style(svc['name'], fg='yellow', bold=True)} - {size_str}"
    )
    click.echo(f"   {svc['description']}")
    paths = svc.get("details", {}).get("paths") or [svc["path"]]
    if len(paths) > 1:
        click.echo(f"   Ścieżki ({len(paths)}):")
        for path in paths:
            click.echo(f"     • {path}")
    else:
        click.echo(f"   Ścieżka: {svc['path']}")
    click.echo(f"   {safe_text}")

    # Show details for specific services
    if svc.get("details"):
        if svc["service_type"] == "docker" and svc["details"].get("components"):
            click.echo(f"   Komponenty: {svc['details']['components']}")
        elif svc["service_type"] == "ollama" and svc["details"].get("models"):
            models = svc["details"]["models"]
            if models:
                click.echo(
                    f"   Modele: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}"
                )
    click.echo()


def _execute_safe_cleanup(services: list, scanner) -> float:
    """Execute cleanup for safe-to-remove services. Returns total space freed in GB."""
    total_freed = 0.0
    for svc in services:
        svc_type = svc["service_type"]
        click.echo(f"Czyszczenie {svc_type}...")
        result = scanner.cleanup_service(svc_type, dry_run=False)
        if result["success"]:
            freed = result.get("space_freed_gb", 0)
            total_freed += freed
            click.echo(click.style(f"  Zwolniono {freed:.2f} GB", fg="green"))
        else:
            click.echo(
                click.style(f"  Błąd: {result.get('error', 'nieznany')}", fg="red")
            )
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


def _display_service_group(service_type: str, svcs: list, type_map: dict) -> None:
    """Display a single service group with cleanup commands and hints."""
    from fixos.diagnostics.service_cleanup import ServiceCleaner

    total_size = sum(s.get("size_gb", 0) for s in svcs)
    click.echo(f"\n  • {service_type.title()}: {total_size:.2f} GB")

    unique_commands = list(set(s["cleanup_command"] for s in svcs))
    for cmd in unique_commands[:2]:
        click.echo(f"    {cmd}")
    if len(unique_commands) > 2:
        click.echo(f"    ... (+{len(unique_commands) - 2} more commands)")

    service_enum = type_map.get(service_type.lower())
    if service_enum:
        hints = ServiceCleaner.get_cleanup_hints(service_enum, total_size)
        if hints:
            click.echo()
            for hint in hints:
                _format_hint_line(hint)


def _display_unsafe_services(services: list) -> None:
    """Display services that require manual review."""
    from fixos.diagnostics.service_scanner import ServiceType

    click.echo()
    click.echo(click.style("Usługi wymagające przeglądu:", fg="yellow"))

    service_groups: dict = {}
    for svc in services:
        service_type = svc.get("service_type", "unknown")
        if service_type not in service_groups:
            service_groups[service_type] = []
        service_groups[service_type].append(svc)

    type_map = {
        "flatpak": ServiceType.FLATPAK,
        "docker": ServiceType.DOCKER,
        "ollama": ServiceType.OLLAMA,
    }

    for service_type, svcs in service_groups.items():
        _display_service_group(service_type, svcs, type_map)

    click.echo()
    click.echo(
        click.style(
            "💡 Wskazówki: Powyższe komendy są bezpieczne i często odzyskują dużo miejsca",
            fg="green",
        )
    )


def _cleanup_single_service(
    service_name: str, scanner, json_output: bool, dry_run: bool
) -> None:
    """Handle cleanup of a single specific service."""
    if json_output:
        result = scanner.cleanup_service(service_name, dry_run=dry_run)
        import json

        click.echo(json.dumps(result, indent=2, default=str))
        return

    click.echo(click.style(f"Czyszczenie usługi: {service_name}", fg="yellow"))
    if dry_run:
        click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))

    result = scanner.cleanup_service(service_name, dry_run=dry_run)

    if result["success"]:
        click.echo(click.style(f"Zakończono czyszczenie {service_name}", fg="green"))
        if result["space_freed_gb"] > 0:
            click.echo(f"  Zwolniono: {result['space_freed_gb']:.2f} GB")
    else:
        click.echo(
            click.style(f"Błąd: {result.get('error', 'Nieznany błąd')}", fg="red")
        )
        if result.get("output"):
            click.echo(f"Output: {result['output']}")


# ── Interactive cleanup orchestration ─────────────────────────────────────


def _run_interactive_cleanup(plan: dict, list_only: bool, scanner) -> None:
    """Offer interactive safe cleanup and display unsafe services."""
    if not list_only and plan["safe_to_cleanup"]:
        safe_total = sum(s["size_gb"] for s in plan["safe_to_cleanup"])
        click.echo(click.style("Bezpieczne do wyczyszczenia:", fg="green"))
        for svc in plan["safe_to_cleanup"]:
            size_str = (
                f"{svc['size_gb']:.2f} GB"
                if svc["size_gb"] >= 1
                else f"{svc['size_mb']:.0f} MB"
            )
            click.echo(f"  • {svc['name']}: {size_str}")
        click.echo()
        if click.confirm(f"Wyczyścić bezpieczne usługi? (zwolni {safe_total:.2f} GB)"):
            _execute_safe_cleanup(plan["safe_to_cleanup"], scanner)
    if plan["requires_review"] and not list_only:
        _display_unsafe_services(plan["requires_review"])


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
