"""Selective removal of unused (dangling) Docker volumes.

Volumes hold real data, so nothing here is bulk: candidates are listed with
name, Compose project and age, the user picks them, and each one is checked
again right before ``docker volume rm``. ``--yes`` never selects volumes whose
name looks like stored data (databases, git mirrors, backups, ...).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import click

from fixos.cli import _cleanup_space as space
from fixos.cli._cleanup_utils import _format_bytes

# Name tokens that usually mean irreplaceable data rather than a cache.
_DATA_TOKENS = re.compile(
    r"(?:^|[_.-])(mirror|git|gitea|onedev|repo|repos|postgres|postgresql|pg|"
    r"mysql|mariadb|mongo|mongodb|redis|db|database|backup|backups|minio|s3|"
    r"vault|secrets?|keycloak|grafana|prometheus|influx|elastic|opensearch|"
    r"nextcloud|uploads|media|webui|openwebui|open-webui|n8n|storage|certs|"
    r"letsencrypt|wordpress|mattermost|synapse|chat-history)(?:$|[_.-])",
    re.IGNORECASE,
)
_INSPECT_BATCH = 100


def _docker_lines(args: list[str], timeout: int = 30) -> list[str] | None:
    try:
        result = space._run_cmd(["docker", *args], timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line.strip()]


def _is_unused(name: str) -> bool:
    """Re-check right before removal: still dangling and no container (even stopped)."""
    dangling = _docker_lines(["volume", "ls", "-q", "-f", "dangling=true", "-f", f"name=^{name}$"])
    containers = _docker_lines(["ps", "-aq", "--filter", f"volume={name}"])
    return dangling is not None and name in dangling and containers == []


def _age_days(created_at: str, now: datetime) -> float | None:
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (now - created).total_seconds() / 86400


_SIZE_WORKERS = 8


def _du_batch(command: list[str], paths: list[str]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    try:
        result = space._run_cmd([*command, "-sbl0", "--", *paths], timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return sizes
    for record in result.stdout.split("\0"):
        size, sep, path = record.partition("\t")
        if sep and size.isdigit():
            sizes[path] = int(size)
    return sizes


def _volume_sizes(mountpoints: list[str]) -> dict[str, int]:
    """Sizes via ``du`` in parallel batches; root-owned volumes use ``sudo -n``.

    ``sudo -n`` never prompts: without passwordless sudo the size stays unknown.
    Unreadable mountpoints go straight to ``sudo -n``, so a partial size of an
    unreadable directory is never reported.
    """
    readable = [m for m in mountpoints if os.access(m, os.R_OK | os.X_OK)]
    privileged = [m for m in mountpoints if m not in set(readable)]
    jobs = [(["du"], readable[i::_SIZE_WORKERS]) for i in range(_SIZE_WORKERS)]
    jobs += [(["sudo", "-n", "du"], privileged[i::_SIZE_WORKERS]) for i in range(_SIZE_WORKERS)]
    jobs = [(command, paths) for command, paths in jobs if paths]
    sizes: dict[str, int] = {}
    if not jobs:
        return sizes
    with ThreadPoolExecutor(max_workers=min(_SIZE_WORKERS, len(jobs))) as pool:
        for result in pool.map(lambda job: _du_batch(*job), jobs):
            sizes.update(result)
    return sizes


def _unused_volumes(
    days: float | None, match: list[str], now: datetime | None = None
) -> list[dict] | None:
    names = _docker_lines(["volume", "ls", "-q", "-f", "dangling=true"])
    if names is None:
        return None
    now = now or datetime.now(timezone.utc)
    records: list[dict] = []
    for start in range(0, len(names), _INSPECT_BATCH):
        raw = _docker_lines(["volume", "inspect", *names[start : start + _INSPECT_BATCH]], timeout=60)
        if raw is None:
            return None
        records.extend(json.loads("\n".join(raw)))
    candidates = []
    for record in records:
        name = record.get("Name", "")
        if match and not any(token.lower() in name.lower() for token in match):
            continue
        age = _age_days(record.get("CreatedAt", ""), now)
        if days is not None and (age is None or age < days):
            continue
        labels = record.get("Labels") or {}
        project = labels.get("com.docker.compose.project") or "(bez projektu)"
        protected = bool(_DATA_TOKENS.search(name))
        candidates.append(
            {
                "name": name,
                "description": name,
                "project": project,
                "age_days": age,
                "mountpoint": record.get("Mountpoint", ""),
                "protected": protected,
                "size_bytes": 0,
                "size_known": False,
            }
        )
    sizes = _volume_sizes([c["mountpoint"] for c in candidates if c["mountpoint"]])
    for candidate in candidates:
        if candidate["mountpoint"] in sizes:
            candidate["size_bytes"] = sizes[candidate["mountpoint"]]
            candidate["size_known"] = True
        age = candidate["age_days"]
        size = _format_bytes(candidate["size_bytes"]) if candidate["size_known"] else "rozmiar nieznany"
        candidate["note"] = (
            f"{candidate['project']}, {age:.0f} dni" if age is not None else candidate["project"]
        ) + (" — wygląda na DANE, tylko ręczny wybór" if candidate["protected"] else "")
        candidate["size_label"] = size
    candidates.sort(key=lambda c: (c["size_known"], c["size_bytes"]), reverse=True)
    return candidates


def _cleanup_docker_volumes(
    json_output: bool,
    dry_run: bool,
    list_only: bool,
    yes: bool,
    days: float | None = None,
    match: list[str] | None = None,
) -> None:
    """List unused Docker volumes and remove the selected ones."""
    candidates = _unused_volumes(days, match or [])
    if json_output:
        space._echo_json(
            {
                "error": None if candidates is not None else "docker volume ls failed",
                "candidates": [
                    {k: c[k] for k in ("name", "project", "age_days", "size_bytes", "size_known", "protected")}
                    for c in candidates or []
                ],
            }
        )
        return
    if candidates is None:
        click.echo(click.style("Błąd: nie udało się odczytać wolumenów Dockera.", fg="red"))
        return
    if not candidates:
        click.echo(click.style("Brak nieużywanych wolumenów Dockera dla podanych filtrów.", fg="green"))
        return
    known = sum(c["size_bytes"] for c in candidates if c["size_known"])
    click.echo(
        f"\n{click.style('DOCKER — nieużywane wolumeny (dane!):', fg='magenta', bold=True)} "
        f"{len(candidates)}, znany rozmiar {_format_bytes(known)}"
    )
    for index, item in enumerate(candidates, 1):
        color = "red" if item["protected"] else "yellow"
        click.echo(
            f"  [{index:3d}] {click.style(item['name'], fg=color)}: {item['size_label']} — {item['note']}"
        )
    if list_only:
        return
    if yes:
        selected = [i for i, c in enumerate(candidates) if not c["protected"]]
        skipped = len(candidates) - len(selected)
        if skipped:
            click.echo(f"  --yes pomija {skipped} wolumenów wyglądających na dane; wybierz je ręcznie.")
    else:
        selected = space._choose(candidates, "Numery wolumenów do usunięcia (np. 1,2, all)")
    if not selected:
        click.echo("Pominięto.")
        return
    if dry_run:
        space._show_dry_run_commands([["docker", "volume", "rm", candidates[i]["name"]] for i in selected])
        return
    if not yes and not space._confirm_remove():
        click.echo("Anulowano.")
        return
    freed = 0
    for index in selected:
        name = candidates[index]["name"]
        if not _is_unused(name):
            click.echo(f"  ⏭️ {name}: jest już używany albo nie istnieje — pominięto")
            continue
        try:
            result = space._run_cmd(["docker", "volume", "rm", name], timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            click.echo(click.style(f"  ❌ {name}: {exc}", fg="red"))
            continue
        if result.returncode == 0:
            freed += candidates[index]["size_bytes"]
            click.echo(click.style(f"  ✅ {name}", fg="green"))
        else:
            click.echo(click.style(f"  ❌ {name}: {result.stderr.strip()[:120]}", fg="red"))
    click.echo(f"Usunięto wolumeny o znanym rozmiarze łącznie {_format_bytes(freed)}.")
