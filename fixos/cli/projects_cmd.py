"""
Projects command for fixOS CLI - developer project artifact scanner.

Walks a workspace tree (default ~/github/*/*), finds removable per-project
build/environment artifacts (venv/.venv, node_modules, compiler/lint
caches, build output), and flags the ones untouched for a long time.
"""

import json as json_module
import re
import subprocess
from pathlib import Path

import click

from fixos.constants import (
    PROJECT_SCAN_DEFAULT_PATH,
    PROJECT_SCAN_MAX_DEPTH,
    PROJECT_SCAN_STALE_DAYS,
    PROJECT_SCAN_THRESHOLD_MB,
)
from fixos.diagnostics.docker_network_cleanup import DockerNetworkCleaner
from fixos.diagnostics.project_scanner import ProjectArtifact, scan_all, summarize


# ── Display helpers ────────────────────────────────────────────────────────


def _size_str(size_mb: float) -> str:
    return f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.0f} MB"


def _short_project_path(path: str) -> str:
    """Last two path components (e.g. 'semcod/fixOS') so long project lists
    stay scannable instead of repeating the full home-directory prefix."""
    parts = Path(path).parts
    return str(Path(*parts[-2:])) if len(parts) >= 2 else path


def _age_str(a: ProjectArtifact) -> str:
    if a.days_since_modified is None:
        return ""
    if a.stale:
        return click.style(f" — nieużywany {a.days_since_modified} dni", fg="red")
    return f" — {a.days_since_modified} dni temu"


def _artifact_to_dict(a: ProjectArtifact) -> dict:
    return {
        "project_name": a.project_name,
        "project_path": a.project_path,
        "artifact_name": a.artifact_name,
        "artifact_path": a.artifact_path,
        "size_mb": a.size_mb,
        "size_gb": a.size_gb,
        "description": a.description,
        "ecosystem": a.ecosystem,
        "risk_level": a.risk_level,
        "days_since_modified": a.days_since_modified,
        "stale": a.stale,
        "cleanup_command": a.cleanup_command,
    }


def _display_summary(
    artifacts: list, base: Path, threshold: int, stale_days: int
) -> None:
    stats = summarize(artifacts)
    click.echo(
        click.style(
            f"\nSkanowanie projektów w {base} (próg: {threshold} MB)...", fg="cyan"
        )
    )
    click.echo(click.style("═" * 60, fg="cyan"))
    click.echo(
        f"Znaleziono {len(artifacts)} artefaktów w {stats['projects_count']} projektach:"
    )
    click.echo(f"  Całkowity rozmiar: {stats['total_gb']:.2f} GB")
    click.echo(click.style(f"  Bezpieczne: {stats['safe_gb']:.2f} GB", fg="green"))
    click.echo(
        click.style(f"  Do rozważenia: {stats['review_gb']:.2f} GB", fg="yellow")
    )
    click.echo(
        click.style(
            f"  Nieużywane od >{stale_days} dni: {stats['stale_gb']:.2f} GB", fg="red"
        )
    )
    if stats["duplicate_venv_projects"]:
        click.echo()
        click.echo(
            click.style(
                f"  ⚠ {len(stats['duplicate_venv_projects'])} projekt(ów) ma więcej niż "
                "jeden virtualenv naraz (np. venv + .venv) — zbędne duplikaty:",
                fg="yellow",
            )
        )
        for path in stats["duplicate_venv_projects"]:
            click.echo(f"    • {path}")
    click.echo()


def _display_artifact_item(a: ProjectArtifact) -> None:
    badge = "(bezpieczne)" if a.risk_level == "safe" else "(do rozważenia)"
    badge_color = "green" if a.risk_level == "safe" else "yellow"
    click.echo(
        f"  {click.style(a.project_name, fg='yellow', bold=True)}/{a.artifact_name} "
        f"- {_size_str(a.size_mb)}{_age_str(a)}"
    )
    click.echo(f"   {a.description}")
    click.echo(f"   Ścieżka: {a.artifact_path}")
    click.echo(f"   {click.style(badge, fg=badge_color)}")
    click.echo()


# ── Selection + execution ──────────────────────────────────────────────────


_ECOSYSTEM_LABELS = {
    "python": "Python (venv, __pycache__, pytest/mypy/ruff/tox cache)",
    "node": "Node.js (node_modules, next/nuxt/turbo/parcel cache)",
    "rust": "Rust (target)",
    "generic": "Build output (dist, build)",
}


def _group_by(artifacts: list, key_fn) -> dict:
    groups: dict = {}
    for a in artifacts:
        groups.setdefault(key_fn(a), []).append(a)
    return groups


def _compose_project_name(project_path: str) -> str | None:
    """Conservative Docker Compose name derived from a project directory."""
    basename = Path(project_path).name.lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "", basename).lstrip("_-")
    return normalized or None


def _cleanup_project_networks(project_paths: set[str], dry_run: bool) -> dict:
    """Remove unused Compose networks belonging to selected projects only."""
    compose_projects = sorted(
        {
            name
            for project_path in project_paths
            if (name := _compose_project_name(project_path)) is not None
        }
    )
    if not compose_projects:
        return {"success": True, "candidates": [], "removed": [], "failed": []}

    cleaner = DockerNetworkCleaner()
    preview = cleaner.cleanup(
        dry_run=True,
        verify_pool=False,
        compose_projects=compose_projects,
    )
    if preview.get("error"):
        click.echo(
            click.style(
                f"Nie udało się sprawdzić sieci Docker: {preview['error']}", fg="red"
            )
        )
        return preview

    candidates = preview.get("candidates") or []
    if not candidates:
        click.echo("Brak nieużywanych sieci Docker powiązanych z wybranymi projektami.")
        return preview

    click.echo(
        click.style(
            "\nNieużywane sieci Docker powiązane z wybranymi projektami:",
            fg="yellow",
            bold=True,
        )
    )
    for network in candidates:
        subnet_text = ", ".join(network.get("subnets") or []) or "brak podsieci"
        click.echo(
            f"  • {network['name']} ({network['short_id']}, {subnet_text}, "
            f"projekt Compose: {network.get('compose_project')})"
        )

    if dry_run:
        click.echo("[DRY RUN] Sieci nie zostaną usunięte.")
        return preview

    if not click.confirm(
        f"Usunąć te nieużywane sieci Docker ({len(candidates)})?",
        default=False,
    ):
        click.echo(click.style("Pominięto usuwanie sieci Docker.", fg="yellow"))
        return preview

    result = cleaner.cleanup(
        dry_run=False,
        verify_pool=True,
        compose_projects=compose_projects,
        network_ids=[network["id"] for network in candidates],
    )
    for network in result.get("removed") or []:
        click.echo(click.style(f"  Usunięto sieć {network['name']}", fg="green"))
    for network in result.get("failed") or []:
        click.echo(
            click.style(
                f"  Nie usunięto {network['name']}: {network.get('error')}", fg="red"
            )
        )

    probe = result.get("pool_probe") or {}
    if probe.get("available") is True:
        click.echo(click.style("  Pula adresowa Docker jest dostępna.", fg="green"))
    elif probe.get("available") is False:
        click.echo(
            click.style(
                f"  Pula adresowa nadal niedostępna: {probe.get('error')}", fg="red"
            )
        )
    return result


def _pick_from_groups(groups: dict, label_fn=str) -> list:
    """Numbered, size-sorted list of groups; user types comma-separated
    indices (e.g. '1,3,5'), 'all', or Enter to pick nothing."""
    items = sorted(
        groups.items(), key=lambda kv: sum(a.size_mb for a in kv[1]), reverse=True
    )
    for i, (key, group_artifacts) in enumerate(items, start=1):
        total = sum(a.size_mb for a in group_artifacts)
        click.echo(
            f"  [{i}] {label_fn(key)} — {_size_str(total)} ({len(group_artifacts)} art.)"
        )

    raw = click.prompt(
        "Numery po przecinku (np. 1,3,5), 'all' dla wszystkich, Enter by pominąć",
        default="",
        show_default=False,
    ).strip()
    if not raw:
        return []
    if raw.lower() == "all":
        return [a for _, group in items for a in group]

    selected = []
    for token in raw.split(","):
        token = token.strip()
        if not token.isdigit():
            continue
        idx = int(token) - 1
        if 0 <= idx < len(items):
            selected.extend(items[idx][1])
    return selected


def _select_artifacts(artifacts: list) -> list:
    """Ask what to clean: everything, a group by some criterion, hand-picked
    items, or none."""
    total = sum(a.size_mb for a in artifacts)
    stale = [a for a in artifacts if a.stale]
    stale_total = sum(a.size_mb for a in stale)

    click.echo("Co wyczyścić?")
    click.echo(f"  [1] Wszystkie bezpieczne ({_size_str(total)})")
    options = ["0", "1"]
    if stale:
        click.echo(
            f"  [2] Tylko dawno nieużywane ({_size_str(stale_total)}, {len(stale)} art.)"
        )
        options.append("2")
    click.echo("  [3] Wybierz wg ekosystemu (Python/Node/Rust/...)")
    click.echo("  [4] Wybierz wg projektu")
    click.echo("  [5] Wybierz pojedyncze artefakty")
    click.echo("  [0] Nic — pomiń")
    options += ["3", "4", "5"]

    choice = click.prompt(
        "Wybór", type=click.Choice(options), default="1", show_choices=False
    )

    if choice == "0":
        return []
    if choice == "1":
        return artifacts
    if choice == "2":
        return stale
    if choice == "3":
        groups = _group_by(artifacts, lambda a: a.ecosystem)
        return _pick_from_groups(groups, label_fn=lambda k: _ECOSYSTEM_LABELS.get(k, k))
    if choice == "4":
        groups = _group_by(artifacts, lambda a: a.project_path)
        return _pick_from_groups(groups, label_fn=_short_project_path)

    click.echo(click.style("Wybierz artefakty do wyczyszczenia:", fg="cyan"))
    selected = []
    for a in artifacts:
        label = f"  {a.project_name}/{a.artifact_name} ({_size_str(a.size_mb)}{_age_str(a)})"
        if click.confirm(label):
            selected.append(a)
    return selected


def _execute_cleanup(artifacts: list, dry_run: bool) -> float:
    total_freed = 0.0
    for a in artifacts:
        label = f"{a.project_name}/{a.artifact_name}"
        if dry_run:
            click.echo(f"[DRY RUN] {label}: would run {a.cleanup_command}")
            continue

        click.echo(f"Czyszczenie {label}...")
        result = subprocess.run(
            a.cleanup_command, shell=True, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            total_freed += a.size_gb
            click.echo(click.style(f"  Zwolniono {a.size_gb:.2f} GB", fg="green"))
        else:
            error = result.stderr.strip() or f"kod wyjścia {result.returncode}"
            click.echo(click.style(f"  Błąd: {error}", fg="red"))
    return total_freed


# ── Main CLI command ────────────────────────────────────────────────────────


@click.command("projects")
@click.option(
    "--path",
    "-p",
    default=None,
    help=f"Katalog bazowy do przeskanowania (domyślnie {PROJECT_SCAN_DEFAULT_PATH})",
)
@click.option(
    "--threshold",
    "-t",
    default=PROJECT_SCAN_THRESHOLD_MB,
    type=int,
    help=f"Próg wielkości w MB (domyślnie {PROJECT_SCAN_THRESHOLD_MB}MB)",
)
@click.option(
    "--stale-days",
    default=PROJECT_SCAN_STALE_DAYS,
    type=int,
    help=f"Po ilu dniach bez zmian artefakt jest 'nieużywany' (domyślnie {PROJECT_SCAN_STALE_DAYS})",
)
@click.option(
    "--only-stale",
    is_flag=True,
    default=False,
    help="Pokaż tylko dawno nieużywane artefakty",
)
@click.option(
    "--max-depth",
    default=PROJECT_SCAN_MAX_DEPTH,
    type=int,
    help="Maksymalna głębokość szukania projektów (domyślnie 4, np. ~/github/org/repo)",
)
@click.option(
    "--json", "json_output", is_flag=True, default=False, help="Wyjście w formacie JSON"
)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    default=False,
    help="Tylko wyświetl listę bez interakcji",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Symuluj czyszczenie bez faktycznego usuwania",
)
@click.option(
    "--docker-networks",
    is_flag=True,
    default=False,
    help=(
        "Po czyszczeniu usuń za potwierdzeniem nieużywane sieci Docker Compose "
        "powiązane z wybranymi projektami"
    ),
)
def projects_cmd(
    path,
    threshold,
    stale_days,
    only_stale,
    max_depth,
    json_output,
    list_only,
    dry_run,
    docker_networks,
) -> None:
    """
    Skanuje projekty deweloperskie (np. ~/github/*/*) w poszukiwaniu
    usuwalnych artefaktów: venv/.venv, node_modules, cache kompilacji/lint,
    build/dist — i oznacza te, które dawno nie były używane.

    \b
    Przykłady:
      fixos projects                          # skanuj ~/github
      fixos projects --path ~/work            # inny katalog bazowy
      fixos projects --only-stale             # tylko dawno nieużywane
      fixos projects --list                   # tylko lista, bez czyszczenia
      fixos projects --dry-run                # podgląd bez usuwania
      fixos projects --only-stale --docker-networks --dry-run
      # stare artefakty oraz należące do ich projektów sieci Compose
    """
    base = (
        Path(path).expanduser()
        if path
        else Path(PROJECT_SCAN_DEFAULT_PATH).expanduser()
    )
    if not base.exists():
        click.echo(click.style(f"Katalog {base} nie istnieje.", fg="red"))
        return

    artifacts = scan_all(
        base, threshold_mb=threshold, stale_days=stale_days, max_depth=max_depth
    )
    if only_stale:
        artifacts = [a for a in artifacts if a.stale]

    if json_output:
        click.echo(
            json_module.dumps([_artifact_to_dict(a) for a in artifacts], indent=2)
        )
        return

    if not artifacts:
        click.echo(
            click.style(
                f"\nNie znaleziono artefaktów powyżej progu w {base}.", fg="green"
            )
        )
        return

    _display_summary(artifacts, base, threshold, stale_days)
    for a in artifacts:
        _display_artifact_item(a)

    if list_only:
        return

    selected_safe: list[ProjectArtifact] = []
    safe = [a for a in artifacts if a.risk_level == "safe"]
    if safe:
        if dry_run:
            selected_safe = safe
            _execute_cleanup(safe, dry_run=True)
        else:
            selected_safe = _select_artifacts(safe)
            if selected_safe:
                freed = _execute_cleanup(selected_safe, dry_run=False)
                click.echo(
                    click.style(
                        f"\nŁącznie zwolniono: {freed:.2f} GB", fg="green", bold=True
                    )
                )
            else:
                click.echo(click.style("Pominięto czyszczenie.", fg="yellow"))

    if docker_networks and selected_safe:
        _cleanup_project_networks(
            {artifact.project_path for artifact in selected_safe},
            dry_run=dry_run,
        )
    elif docker_networks:
        click.echo(
            click.style(
                "Brak wybranych projektów — pominięto usuwanie sieci Docker.",
                fg="yellow",
            )
        )

    review = [a for a in artifacts if a.risk_level == "review"]
    if review:
        click.echo()
        click.echo(
            click.style(
                "Do rozważenia (mogą zawierać coś, co chcesz zachować, np. wynik builda):",
                fg="yellow",
            )
        )
        for a in review:
            click.echo(
                f"  • {a.project_name}/{a.artifact_name}: {_size_str(a.size_mb)}{_age_str(a)}"
            )
            click.echo(f"    rm -rf {a.artifact_path}")
