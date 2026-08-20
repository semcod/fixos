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

from fixos.cli._cleanup_utils import _parse_numeric_range_set
from fixos.diagnostics.docker_startup_optimizer import (
    DEFAULT_DOCKER_STALE_SERVICE_DAYS,
    DockerStartupOptimizer,
)
from fixos.diagnostics.orphaned_workloads import (
    DEFAULT_ORPHANED_PROJECT_DAYS,
    DEFAULT_STALE_PROCESS_HOURS,
    OrphanedWorkloadCleaner,
)
from fixos.diagnostics.service_scanner import ServiceDataScanner
from fixos.constants import DEFAULT_CLEANUP_THRESHOLD_MB

# Re-export public symbols used by fixos.cli (backward-compat)
from fixos.cli._cleanup_flatpak import _cleanup_flatpak_detailed  # noqa: F401
from fixos.cli._cleanup_system import _cleanup_full_system
from fixos.diagnostics.service_cleanup import (
    DEFAULT_DOCKER_NETWORK_AGE_DAYS,
    DEFAULT_DOCKER_OLD_UNUSED_DAYS,
    DEFAULT_OLLAMA_OLD_UNUSED_DAYS,
    ServiceCleaner,
)


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


def _execute_planned_cleanup(scanner, svc: dict, *, dry_run: bool = False) -> dict:
    """Run a planned cleanup entry (including age-bounded docker/ollama actions)."""
    kind = svc.get("cleanup_kind")
    cleaner = ServiceCleaner(scanner)
    if kind == "ollama-old":
        return cleaner.cleanup_ollama_old_unused(
            days=int(svc.get("days") or DEFAULT_OLLAMA_OLD_UNUSED_DAYS),
            dry_run=dry_run,
        )
    if kind == "docker-unused":
        return cleaner.cleanup_docker_unused(
            dry_run=dry_run,
            include_networks=True,
        )
    if kind == "docker-old":
        return cleaner.cleanup_docker_old_unused(
            days=int(svc.get("days") or DEFAULT_DOCKER_OLD_UNUSED_DAYS),
            dry_run=dry_run,
            include_networks=True,
        )
    if kind == "docker-networks":
        planned_networks = (svc.get("details") or {}).get("orphan_networks") or []
        return cleaner.cleanup_docker_networks(
            days=int(svc.get("days") or DEFAULT_DOCKER_NETWORK_AGE_DAYS),
            dry_run=dry_run,
            network_ids=[network["id"] for network in planned_networks] or None,
        )
    return scanner.cleanup_service(
        svc["service_type"],
        dry_run=dry_run,
        planned_service=svc,
    )


def _execute_safe_cleanup(services: list, scanner) -> float:
    """Execute cleanup for safe-to-remove services. Returns total space freed in GB."""
    total_freed = 0.0
    for svc in services:
        click.echo(f"Czyszczenie {svc.get('name') or svc['service_type']}...")
        result = _execute_planned_cleanup(scanner, svc, dry_run=False)
        if result["success"]:
            freed = float(result.get("space_freed_gb", 0) or 0)
            total_freed += freed
            if freed > 0:
                click.echo(click.style(f"  Zwolniono {freed:.2f} GB", fg="green"))
            elif result.get("network_cleanup"):
                click.echo(
                    click.style(
                        "  Czyszczenie obrazów/cache zakończone; wynik sieci poniżej.",
                        fg="green",
                    )
                )
            else:
                click.echo(
                    click.style(
                        "  Brak mierzalnej zmiany rozmiaru (0.00 GB) — "
                        "komenda zakończyła się OK, ale cache mógł być już pusty "
                        "albo filtr wieku nic nie trafił.",
                        fg="yellow",
                    )
                )
                note = (result.get("output") or result.get("error") or "").strip()
                if note:
                    for line in note.splitlines()[:4]:
                        click.echo(f"    {line}")
        else:
            click.echo(click.style(f"  Błąd: {_error_message(result)}", fg="red"))
        network_result = result.get("network_cleanup")
        if network_result:
            _display_docker_network_result(
                network_result,
                dry_run=False,
                title="  Docker — osierocone sieci",
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
        item for item in entries if item.can_cleanup and item.cleanup_command.strip()
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


def _cleanup_docker_all_unused(scanner, json_output: bool, dry_run: bool) -> None:
    """Prune all unused Docker images/cache plus orphaned networks."""
    result = ServiceCleaner(scanner).cleanup_docker_unused(
        dry_run=dry_run,
        include_networks=True,
    )

    if json_output:
        import json

        click.echo(json.dumps(result, indent=2, default=str))
        return

    click.echo(
        click.style(
            "Docker — nieużywane obrazy, build cache i osierocone sieci",
            fg="yellow",
        )
    )
    click.echo(f"  Komenda obrazów/cache: {result.get('command')}")
    if dry_run:
        click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))

    if result.get("success"):
        if dry_run:
            click.echo(click.style("Symulacja zakończona", fg="green"))
            if result.get("estimated_max_gb", 0) > 0:
                click.echo(
                    f"  Maksymalnie Images+Build Cache: "
                    f"{result['estimated_max_gb']:.2f} GB"
                )
        else:
            click.echo(click.style("Zakończono czyszczenie Dockera", fg="green"))
            click.echo(f"  Zwolniono: {result.get('space_freed_gb', 0):.2f} GB")
    else:
        click.echo(click.style(f"Błąd: {_error_message(result)}", fg="red"))

    network_result = result.get("network_cleanup")
    if network_result:
        _display_docker_network_result(
            network_result,
            dry_run=dry_run,
            title="Docker — osierocone sieci znalezione przy czyszczeniu",
        )


def _cleanup_docker_old_unused(
    scanner, days: int, json_output: bool, dry_run: bool
) -> None:
    """Prune unused Docker images (and old build cache) older than N days."""
    cleaner = ServiceCleaner(scanner)
    try:
        result = cleaner.cleanup_docker_old_unused(
            days=days,
            dry_run=dry_run,
            include_networks=True,
        )
    except ValueError as exc:
        click.echo(click.style(f"Błąd: {exc}", fg="red"))
        return

    if json_output:
        import json

        click.echo(json.dumps(result, indent=2, default=str))
        return

    click.echo(
        click.style(
            f"Docker — nieużywane obrazy starsze niż {days} dni",
            fg="yellow",
        )
    )
    click.echo(f"  Komenda: {result.get('command')}")
    if dry_run:
        click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))

    if result.get("success"):
        if dry_run:
            click.echo(click.style("Symulacja zakończona", fg="green"))
            if result.get("output"):
                for line in str(result["output"]).splitlines():
                    click.echo(f"  {line}")
            if result.get("estimated_max_gb", 0) > 0:
                click.echo(
                    f"  Szacowane maksimum (Images+Build Cache reclaimable): "
                    f"{result['estimated_max_gb']:.2f} GB "
                    f"(filtr until zwykle usunie mniej)"
                )
        else:
            click.echo(click.style("Zakończono czyszczenie docker-old", fg="green"))
            if result.get("space_freed_gb", 0) > 0:
                click.echo(f"  Zwolniono: {result['space_freed_gb']:.2f} GB")
            elif result.get("output"):
                click.echo(f"  {result['output'].strip()[:500]}")
    else:
        click.echo(click.style(f"Błąd: {_error_message(result)}", fg="red"))
        if result.get("output"):
            click.echo(f"Output: {result['output']}")

    network_result = result.get("network_cleanup")
    if network_result:
        _display_docker_network_result(
            network_result,
            dry_run=dry_run,
            title="Docker — osierocone sieci znalezione przy czyszczeniu",
        )


def _display_docker_network_result(
    result: dict,
    *,
    dry_run: bool,
    title: str = "Docker — osierocone sieci",
) -> None:
    """Render a standalone or attached orphan-network cleanup result."""
    days = int(result.get("min_age_days") or 0)
    age_text = "bez limitu wieku" if days == 0 else f"starsze niż {days} dni"
    click.echo(click.style(f"{title} ({age_text})", fg="yellow"))
    candidates = result.get("candidates") or []
    if candidates:
        click.echo(f"  Kandydaci: {len(candidates)}")
        for network in candidates:
            subnets = ", ".join(network.get("subnets") or [])
            subnet_text = f", podsieć {subnets}" if subnets else ""
            click.echo(
                f"    • {network['name']} ({network['short_id']}{subnet_text}, "
                f"wiek {network['age_days']:.1f} dni)"
            )
    else:
        click.echo("  Brak osieroconych sieci spełniających kryteria.")

    if dry_run:
        click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))
        click.echo("  Test puli adresowej pominięty, ponieważ tworzyłby sieć testową.")
        return

    removed = result.get("removed") or []
    failed = result.get("failed") or []
    click.echo(f"  Usunięto: {len(removed)}")
    for network in removed:
        click.echo(f"    ✓ {network['name']}")
    for network in failed:
        click.echo(
            click.style(
                f"    Błąd {network['name']}: {network.get('error') or 'nieznany'}",
                fg="red",
            )
        )

    probe = result.get("pool_probe") or {}
    if probe.get("available") is True:
        click.echo(
            click.style(
                "  Pula adresowa: dostępna (test create/remove PASS)", fg="green"
            )
        )
    elif probe.get("available") is False:
        click.echo(
            click.style(
                f"  Pula adresowa nadal niedostępna: "
                f"{probe.get('error') or result.get('error') or 'nieznany błąd'}",
                fg="red",
            )
        )


def _cleanup_docker_networks(
    scanner, days: int, json_output: bool, dry_run: bool
) -> None:
    """Usuń sieci Docker bez endpointów i potwierdź dostępność puli."""
    cleaner = ServiceCleaner(scanner)
    try:
        result = cleaner.cleanup_docker_networks(days=days, dry_run=dry_run)
    except ValueError as exc:
        click.echo(click.style(f"Błąd: {exc}", fg="red"))
        return

    if json_output:
        import json

        click.echo(json.dumps(result, indent=2, default=str))
        return

    _display_docker_network_result(result, dry_run=dry_run)


def _display_stale_docker_candidates(candidates: list[dict], days: int) -> None:
    """Render repository evidence used to protect or select Docker services."""
    click.echo(
        click.style(
            f"Docker — usługi z repozytoriów nieaktywnych od {days}+ dni",
            fg="yellow",
        )
    )
    if not candidates:
        click.echo("  Brak usług spełniających wszystkie bezpieczne kryteria.")
        return
    for index, candidate in enumerate(candidates, 1):
        helpers = len(candidate.get("docker_exec_helpers") or [])
        click.echo(
            f"  [{index}] {candidate['name']} ({candidate['short_id']}) — "
            f"{candidate['inactivity_days']:.1f} dni, "
            f"stan={candidate['status']}, restart={candidate['restart_policy']}"
        )
        click.echo(
            f"      repo: {candidate['repository']}; docker exec: {helpers}"
        )


def _cleanup_docker_stale_services(
    days: int,
    json_output: bool,
    dry_run: bool,
    list_only: bool,
) -> None:
    """Interactively disable autostart and optionally stop exact candidates."""
    optimizer = DockerStartupOptimizer()
    try:
        scan = optimizer.scan(min_inactive_days=days)
    except (RuntimeError, ValueError) as exc:
        if json_output:
            import json

            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(click.style(f"Błąd: {exc}", fg="red"))
        return

    if json_output:
        import json

        click.echo(json.dumps(scan, indent=2, default=str))
        return

    candidates = scan["candidates"]
    _display_stale_docker_candidates(candidates, days)
    click.echo(
        f"  Helpery docker exec w systemie: {scan['docker_exec_helper_count']}"
    )
    if not candidates:
        return
    if dry_run or list_only:
        mode = "DRY-RUN" if dry_run else "LISTA"
        click.echo(
            click.style(f"[TRYB {mode}] - brak zmian w Dockerze", fg="cyan")
        )
        return

    raw_selection = click.prompt(
        "Wybierz numery usług (np. 1,3-5 lub all; 0 pomija)",
        default="0",
        show_default=True,
    ).strip()
    if raw_selection.lower() == "all":
        selected_numbers = set(range(1, len(candidates) + 1))
    else:
        selected_numbers = _parse_numeric_range_set(raw_selection)
        selected_numbers = {
            number for number in selected_numbers if 1 <= number <= len(candidates)
        }
    if not selected_numbers:
        click.echo(click.style("Pominięto usługi Docker.", fg="yellow"))
        return

    selected = [candidates[number - 1] for number in sorted(selected_numbers)]
    click.echo("Wybrane usługi:")
    for candidate in selected:
        click.echo(f"  • {candidate['name']} ({candidate['short_id']})")
    if not click.confirm(
        "Wyłączyć ich autostart (ustawić restart=no)?",
        default=False,
    ):
        click.echo(click.style("Pominięto zmiany Dockera.", fg="yellow"))
        return
    stop_running = click.confirm(
        "Zatrzymać teraz wybrane aktywne usługi?",
        default=False,
    )
    result = optimizer.optimize(
        [candidate["id"] for candidate in selected],
        min_inactive_days=days,
        apply=True,
        stop_running=stop_running,
    )
    for changed in result["changed"]:
        state = changed.get("status") or "nieznany"
        click.echo(
            click.style(
                f"  ✓ {changed['name']}: restart=no, stan={state}", fg="green"
            )
        )
    for failed in result["failed"]:
        click.echo(
            click.style(
                f"  Błąd {failed.get('name') or failed['id'][:12]}: "
                f"{failed.get('error') or 'nieznany błąd'}",
                fg="red",
            )
        )
    if result["success"]:
        click.echo(click.style("Optymalizacja usług Docker zakończona.", fg="green"))


def _display_orphaned_candidates(scan: dict) -> list[tuple[str, dict]]:
    """Render one exact selection list for Docker and process-tree candidates."""
    click.echo(click.style("Osierocone obciążenia projektów", fg="yellow"))
    combined: list[tuple[str, dict]] = []
    for candidate in scan["docker_candidates"]:
        combined.append(("docker", candidate))
        click.echo(
            f"  [{len(combined)}] Docker {candidate['name']} "
            f"({candidate['short_id']}) — {candidate['age_days']:.1f} dni, "
            f"restart={candidate['restart_policy']}, stan={candidate['status']}"
        )
        click.echo(f"      brak katalogu: {candidate['working_dir']}")
    for candidate in scan["process_candidates"]:
        combined.append(("process", candidate))
        ports = ",".join(str(port) for port in candidate["listen_ports"]) or "brak"
        click.echo(
            f"  [{len(combined)}] Proces {candidate['reason']} PID "
            f"{candidate['root_pid']} — {candidate['age_hours']:.1f} h, "
            f"procesy={candidate['process_count']}, RAM={candidate['memory_mb']:.1f} MB"
        )
        click.echo(
            f"      porty={ports}, aktywne połączenia="
            f"{candidate['established_connections']}"
        )
    if not combined:
        click.echo("  Brak obciążeń spełniających bezpieczne kryteria.")
    return combined


def _cleanup_orphaned_projects(
    days: int,
    process_hours: float,
    json_output: bool,
    dry_run: bool,
    list_only: bool,
) -> None:
    """Interactively clean exact missing-project containers and process trees."""
    cleaner = OrphanedWorkloadCleaner()
    try:
        scan = cleaner.scan(
            min_age_days=days,
            min_process_hours=process_hours,
        )
    except (RuntimeError, ValueError) as exc:
        if json_output:
            import json

            click.echo(json.dumps({"success": False, "error": str(exc)}))
        else:
            click.echo(click.style(f"Błąd: {exc}", fg="red"))
        return

    if json_output:
        import json

        click.echo(json.dumps(scan, indent=2, default=str))
        return

    combined = _display_orphaned_candidates(scan)
    if not combined:
        return
    if dry_run or list_only:
        mode = "DRY-RUN" if dry_run else "LISTA"
        click.echo(
            click.style(
                f"[TRYB {mode}] - brak zmian w Dockerze i procesach",
                fg="cyan",
            )
        )
        return

    raw_selection = click.prompt(
        "Wybierz numery obciążeń (np. 1,3-5 lub all; 0 pomija)",
        default="0",
        show_default=True,
    ).strip()
    if raw_selection.lower() == "all":
        selected_numbers = set(range(1, len(combined) + 1))
    else:
        selected_numbers = {
            number
            for number in _parse_numeric_range_set(raw_selection)
            if 1 <= number <= len(combined)
        }
    if not selected_numbers:
        click.echo(click.style("Pominięto osierocone obciążenia.", fg="yellow"))
        return

    selected = [combined[number - 1] for number in sorted(selected_numbers)]
    docker_selected = [item for kind, item in selected if kind == "docker"]
    process_selected = [item for kind, item in selected if kind == "process"]
    if docker_selected and not click.confirm(
        "Wyłączyć autostart i zatrzymać wybrane kontenery (bez usuwania danych)?",
        default=False,
    ):
        docker_selected = []
    force_processes = False
    if process_selected and not click.confirm(
        "Zakończyć łagodnie wybrane drzewa procesów?",
        default=False,
    ):
        process_selected = []
    elif process_selected:
        force_processes = click.confirm(
            "Wymusić zakończenie procesów, które nie wyjdą łagodnie?",
            default=False,
        )
    if not docker_selected and not process_selected:
        click.echo(click.style("Nie wykonano zmian.", fg="yellow"))
        return

    result = cleaner.cleanup(
        docker_ids=[item["id"] for item in docker_selected],
        process_identities=[
            (item["root_pid"], item["create_time"]) for item in process_selected
        ],
        min_age_days=days,
        min_process_hours=process_hours,
        apply=True,
        force_processes=force_processes,
    )
    for changed in result["docker_changed"]:
        click.echo(
            click.style(
                f"  ✓ Docker {changed['name']}: restart=no, "
                f"stan={changed['status']}",
                fg="green",
            )
        )
    for changed in result["processes_changed"]:
        click.echo(
            click.style(
                f"  ✓ Proces PID {changed['root_pid']}: zakończono "
                f"{len(changed['target_pids'])} procesów",
                fg="green",
            )
        )
    for failed in result["failed"]:
        target = failed.get("name") or failed.get("root_pid") or failed.get("id")
        message = failed.get("error") or "; ".join(failed.get("errors") or ())
        click.echo(click.style(f"  Błąd {target}: {message}", fg="red"))
    if result["success"]:
        click.echo(
            click.style(
                "Czyszczenie osieroconych obciążeń zakończone; dane zachowano.",
                fg="green",
            )
        )


def _cleanup_ollama_old_unused(
    scanner, days: int, json_output: bool, dry_run: bool
) -> None:
    """Remove Ollama models not modified for more than N days."""
    cleaner = ServiceCleaner(scanner)
    try:
        result = cleaner.cleanup_ollama_old_unused(days=days, dry_run=dry_run)
    except ValueError as exc:
        click.echo(click.style(f"Błąd: {exc}", fg="red"))
        return

    if json_output:
        import json

        click.echo(json.dumps(result, indent=2, default=str))
        return

    click.echo(
        click.style(
            f"Ollama — modele niezmieniane od {days}+ dni",
            fg="yellow",
        )
    )
    if result.get("command"):
        click.echo(f"  Komenda: {result['command']}")
    if dry_run:
        click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))

    if result.get("success"):
        if dry_run:
            click.echo(click.style("Symulacja zakończona", fg="green"))
            if result.get("output"):
                for line in str(result["output"]).splitlines():
                    click.echo(f"  {line}")
            if result.get("estimated_max_gb", 0) > 0:
                click.echo(
                    f"  Szacowane zwolnienie: {result['estimated_max_gb']:.2f} GB"
                )
            if result.get("skipped_running"):
                click.echo(
                    "  Pominięto uruchomione: " + ", ".join(result["skipped_running"])
                )
        else:
            click.echo(click.style("Zakończono czyszczenie ollama-old", fg="green"))
            if result.get("space_freed_gb", 0) > 0:
                click.echo(f"  Zwolniono: {result['space_freed_gb']:.2f} GB")
            if result.get("output"):
                click.echo(f"  {result['output'].strip()[:500]}")
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
        label = f"  {svc['name']} ({_size_str(svc)}) [{_selection_description(svc)}]"
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
        result = _execute_planned_cleanup(scanner, svc, dry_run=False)
        if result["success"]:
            freed = float(result.get("space_freed_gb", 0))
            total_freed += freed
            click.echo(click.style(f"  Zwolniono {freed:.2f} GB", fg="green"))
        else:
            click.echo(click.style(f"  Błąd: {_error_message(result)}", fg="red"))
        network_result = result.get("network_cleanup")
        if network_result:
            _display_docker_network_result(
                network_result,
                dry_run=False,
                title="  Docker — osierocone sieci",
            )
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
            click.echo()
            click.echo(
                click.style(
                    "Uwaga: listy poniżej pochodzą ze skanu sprzed czyszczenia — "
                    "uruchom ponownie `fixos cleanup --list`, by zobaczyć aktualny stan.",
                    fg="cyan",
                )
            )
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
    help=(
        "Wyczyść konkretną usługę "
        "(docker, docker-all, docker-old, docker-networks, "
        "docker-stale-services, orphaned-projects, ollama-old, npm, ...)"
    ),
)
@click.option(
    "--docker-old",
    "docker_old",
    is_flag=True,
    default=False,
    help=(
        "Usuń nieużywane obrazy Docker i build cache starsze niż --days "
        "oraz wszystkie osierocone sieci; "
        f"domyślnie {DEFAULT_DOCKER_OLD_UNUSED_DAYS} dni, bez wolumenów"
    ),
)
@click.option(
    "--docker-all",
    "docker_all",
    is_flag=True,
    default=False,
    help=(
        "Usuń wszystkie nieużywane obrazy, build cache i osierocone sieci; "
        "nie usuwa kontenerów ani wolumenów"
    ),
)
@click.option(
    "--docker-networks",
    "docker_networks",
    is_flag=True,
    default=False,
    help=(
        "Usuń niestandardowe sieci Docker bez endpointów i sprawdź pulę adresową; "
        "chroni bridge/host/none oraz wszystkie sieci używane przez kontenery"
    ),
)
@click.option(
    "--docker-stale-services",
    "docker_stale_services",
    is_flag=True,
    default=False,
    help=(
        "Wybierz usługi z czystych repozytoriów Git nieaktywnych od --days dni; "
        f"domyślnie {DEFAULT_DOCKER_STALE_SERVICE_DAYS} dni; "
        "wyłączenie autostartu i zatrzymanie wymagają potwierdzeń"
    ),
)
@click.option(
    "--orphaned-projects",
    "orphaned_projects",
    is_flag=True,
    default=False,
    help=(
        "Wybierz kontenery Compose, których katalog projektu nie istnieje od "
        f"co najmniej {DEFAULT_ORPHANED_PROJECT_DAYS} dni, oraz stare drzewa "
        "agentów IDE/serwerów developerskich; zachowuje dane i chroni bieżące IDE/Codex"
    ),
)
@click.option(
    "--process-hours",
    default=DEFAULT_STALE_PROCESS_HOURS,
    type=float,
    show_default=True,
    help="Minimalny wiek jawnie wybieranych agentów IDE i serwerów developerskich",
)
@click.option(
    "--ollama-old",
    "ollama_old",
    is_flag=True,
    default=False,
    help=(
        "Usuń modele Ollama niezmieniane od --days dni "
        f"(domyślnie {DEFAULT_OLLAMA_OLD_UNUSED_DAYS}); pomija modele aktualnie uruchomione"
    ),
)
@click.option(
    "--days",
    default=None,
    type=int,
    help=(
        "Wiek w dniach dla --docker-old "
        f"(domyślnie {DEFAULT_DOCKER_OLD_UNUSED_DAYS}), --docker-networks "
        f"(domyślnie {DEFAULT_DOCKER_NETWORK_AGE_DAYS}, czyli wszystkie nieużywane), "
        "--docker-stale-services "
        f"(domyślnie {DEFAULT_DOCKER_STALE_SERVICE_DAYS}) "
        "lub --orphaned-projects "
        f"(domyślnie {DEFAULT_ORPHANED_PROJECT_DAYS}) "
        "lub --ollama-old "
        f"(domyślnie {DEFAULT_OLLAMA_OLD_UNUSED_DAYS})"
    ),
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
    threshold,
    services,
    json_output,
    cleanup,
    docker_old,
    docker_all,
    docker_networks,
    docker_stale_services,
    orphaned_projects,
    process_hours,
    ollama_old,
    days,
    dry_run,
    list_only,
    full_analysis,
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
      fixos cleanup -c docker --dry-run  # tylko cache buildów >7 dni
      fixos cleanup --docker-all --dry-run
      # wszystkie unused images/cache + osierocone sieci
      fixos cleanup --docker-old --days 30 --dry-run
      # stare obrazy/cache + osierocone sieci
      fixos cleanup --docker-networks --dry-run
      # sieci bez endpointów; wykonanie kończy test puli adresowej
      fixos cleanup --docker-stale-services --dry-run
      # podgląd usług z repozytoriów nieaktywnych od 3+ dni
      fixos cleanup --docker-stale-services --days 7
      # wybór usług, potwierdzenie restart=no i opcjonalnego zatrzymania
      fixos cleanup --orphaned-projects --days 3 --dry-run
      # brakujące katalogi Compose i stare lokalne drzewa procesów
      fixos cleanup --orphaned-projects --days 3 --process-hours 12
      # dokładny wybór; zatrzymuje obciążenia, zachowuje kontenery i wolumeny
      fixos cleanup --ollama-old --days 90 --dry-run
      # modele Ollama niezmieniane od 90+ dni
      fixos cleanup -c ollama-old
      fixos cleanup --full              # pełna analiza systemu
    """
    if full_analysis:
        _cleanup_full_system(json_output, dry_run)
        return

    scanner = ServiceDataScanner(threshold_mb=threshold)

    want_docker_old = docker_old or (cleanup == "docker-old")
    want_docker_all = docker_all or cleanup in {"docker-all", "docker-unused"}
    want_docker_networks = docker_networks or (cleanup == "docker-networks")
    want_docker_stale_services = docker_stale_services or (
        cleanup == "docker-stale-services"
    )
    want_orphaned_projects = orphaned_projects or cleanup == "orphaned-projects"
    want_ollama_old = ollama_old or (cleanup == "ollama-old")
    if want_docker_old and want_docker_all:
        click.echo(
            click.style(
                "Wybierz jeden zakres obrazów: --docker-old albo -c docker-all.",
                fg="red",
            )
        )
        return
    if want_ollama_old and (want_docker_old or want_docker_all or want_docker_networks):
        click.echo(
            click.style(
                "Czyszczenie Ollama i Dockera uruchom jako osobne akcje.",
                fg="red",
            )
        )
        return
    if want_docker_stale_services and (
        want_docker_old
        or want_docker_all
        or want_docker_networks
        or want_ollama_old
    ):
        click.echo(
            click.style(
                "Optymalizację usług uruchom osobno od czyszczenia danych Dockera/Ollama.",
                fg="red",
            )
        )
        return
    if want_orphaned_projects and (
        want_docker_old
        or want_docker_all
        or want_docker_networks
        or want_docker_stale_services
        or want_ollama_old
    ):
        click.echo(
            click.style(
                "Czyszczenie osieroconych projektów uruchom jako osobną akcję.",
                fg="red",
            )
        )
        return
    if docker_stale_services and cleanup and cleanup != "docker-stale-services":
        click.echo(
            click.style(
                "--docker-stale-services nie można łączyć z innym -c/--cleanup.",
                fg="red",
            )
        )
        return
    if orphaned_projects and cleanup and cleanup != "orphaned-projects":
        click.echo(
            click.style(
                "--orphaned-projects nie można łączyć z innym -c/--cleanup.",
                fg="red",
            )
        )
        return
    if (
        docker_networks
        and cleanup
        and cleanup
        not in {"docker-all", "docker-unused", "docker-old", "docker-networks"}
    ):
        click.echo(
            click.style(
                "--docker-networks można łączyć tylko z docker-all lub docker-old.",
                fg="red",
            )
        )
        return
    if want_docker_all:
        _cleanup_docker_all_unused(scanner, json_output, dry_run)
        return
    if want_docker_old:
        effective_days = days if days is not None else DEFAULT_DOCKER_OLD_UNUSED_DAYS
        _cleanup_docker_old_unused(scanner, effective_days, json_output, dry_run)
        return
    if want_docker_networks:
        effective_days = days if days is not None else DEFAULT_DOCKER_NETWORK_AGE_DAYS
        _cleanup_docker_networks(scanner, effective_days, json_output, dry_run)
        return
    if want_docker_stale_services:
        effective_days = (
            days if days is not None else DEFAULT_DOCKER_STALE_SERVICE_DAYS
        )
        _cleanup_docker_stale_services(
            effective_days,
            json_output,
            dry_run,
            list_only,
        )
        return
    if want_orphaned_projects:
        effective_days = days if days is not None else DEFAULT_ORPHANED_PROJECT_DAYS
        _cleanup_orphaned_projects(
            effective_days,
            process_hours,
            json_output,
            dry_run,
            list_only,
        )
        return
    if want_ollama_old:
        effective_days = days if days is not None else DEFAULT_OLLAMA_OLD_UNUSED_DAYS
        _cleanup_ollama_old_unused(scanner, effective_days, json_output, dry_run)
        return

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
