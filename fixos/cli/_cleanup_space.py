"""Disk-space reclaim handlers for large, regenerable targets.

Each handler scans first, lists candidates with sizes, and removes only
explicitly selected entries (or all of them with ``--yes``). User documents
(~/Videos, ~/Downloads, …) are never scanned for deletion.

Handler signature: ``fn(json_output, dry_run, list_only, yes)``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import click

from fixos.cli._cleanup_utils import _format_bytes, _parse_selection
from fixos.constants import (
    DEFAULT_THUMBNAILS_UNUSED_DAYS,
    DEFAULT_TMP_UNUSED_DAYS,
    DEFAULT_TRASH_UNUSED_DAYS,
)

_JOURNAL_DEFAULT_SIZE = "500M"
_IMAGE_SUFFIXES = {".qcow2", ".img", ".iso", ".raw"}
_LIBVIRT_URIS = ("qemu:///system", "qemu:///session")
# Well-known tool caches that are always safe to drop — every entry is
# regenerated on demand and never holds user-authored data.
_USER_CACHE_SAFE = {
    "pip",
    "uv",
    "npm",
    "yarn",
    "pnpm",
    "composer",
    "go-build",
    "fontconfig",
    "mesa_shader_cache",
    "mesa_shader_cache_db",
    "thumbnails",
    "pre-commit",
    "vcpkg",
}


def _run_cmd(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Execute a command; module-level seam so tests can stub it."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def _dir_size(path: Path) -> int:
    """Return directory size in bytes (du -sb with a Python fallback)."""
    try:
        result = _run_cmd(["du", "-sb", str(path)], timeout=300)
        if result.returncode == 0:
            return int(result.stdout.split()[0])
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        pass
    total = 0
    try:
        for entry in path.rglob("*"):
            try:
                if entry.is_file() and not entry.is_symlink():
                    total += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0
    return total


def _size_to_bytes(value: str) -> int:
    """Parse sizes like '7.9GB' / '512M' / '1.5GiB' to bytes."""
    match = re.match(r"([0-9.]+)\s*([KMGT]?I?B|[KMGT])(?=$|[^A-Za-z])", value.strip().upper())
    if not match:
        return 0
    number, unit = match.groups()
    multipliers = {
        "B": 1,
        "K": 1024,
        "KB": 1000,
        "KIB": 1024,
        "M": 1024**2,
        "MB": 1000**2,
        "MIB": 1024**2,
        "G": 1024**3,
        "GB": 1000**3,
        "GIB": 1024**3,
        "T": 1024**4,
        "TB": 1000**4,
        "TIB": 1024**4,
    }
    return int(float(number) * multipliers.get(unit, 1))


def _echo_json(payload: object) -> None:
    click.echo(json.dumps(payload, indent=2, default=str))


def _choose(candidates: list[dict], prompt: str) -> list[int]:
    raw = click.prompt(prompt, default="", show_default=False)
    if not raw.strip():
        return []
    return _parse_selection(raw, len(candidates))


def _confirm_remove() -> bool:
    return click.confirm("  Wykonać usunięcie wybranych pozycji?", default=False)


def _remove_path(path: Path) -> tuple[bool, str]:
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
        return True, "usunięto"
    except OSError as exc:
        return False, str(exc)


def _display_candidates(title: str, candidates: list[dict]) -> None:
    click.echo(f"\n{click.style(title, fg='magenta', bold=True)}")
    for index, item in enumerate(candidates, 1):
        size = _format_bytes(item.get("size_bytes", 0))
        detail = item.get("note", "")
        suffix = f" — {detail}" if detail else ""
        click.echo(
            f"  [{index:3d}] {click.style(item['description'], fg='yellow')}: "
            f"{size}{suffix}"
        )
    click.echo(f"\n  Kandydatów: {len(candidates)}")


def _remove_selected(
    candidates: list[dict], selected: list[int], path_key: str = "path"
) -> None:
    for index in selected:
        item = candidates[index]
        ok, detail = _remove_path(item[path_key])
        style = "green" if ok else "red"
        click.echo(click.style(f"  {item['description']}: {detail}", fg=style))


def _show_dry_run_commands(commands: list[list[str]]) -> None:
    click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))
    for command in commands:
        click.echo(f"  $ {' '.join(command)}")


# ── snap revisions ───────────────────────────────────────────────────────


def _snap_disabled_revisions() -> list[dict] | None:
    """Parse `snap list --all` rows marked as disabled."""
    try:
        result = _run_cmd(["snap", "list", "--all"])
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    candidates = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 3 or "disabled" not in line.lower():
            continue
        name, version, rev = parts[0], parts[1], parts[2]
        candidates.append(
            {
                "description": f"{name} (rewizja {rev})",
                "note": f"v{version}",
                "size_bytes": 0,
                "command": ["sudo", "snap", "remove", name, "--revision", rev],
            }
        )
    return candidates


def _cleanup_snap_old(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Remove disabled snap revisions selected by the user."""
    candidates = _snap_disabled_revisions()
    if json_output:
        _echo_json({"candidates": candidates or []})
        return
    if candidates is None:
        click.echo(click.style("Błąd: `snap list --all` niedostępny.", fg="red"))
        return
    if not candidates:
        click.echo(click.style("Brak wyłączonych rewizji snap.", fg="green"))
        return
    _display_candidates("WYŁĄCZONE REWIZJE SNAP:", candidates)
    if list_only:
        return
    if dry_run:
        _show_dry_run_commands([item["command"] for item in candidates])
        return
    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery rewizji do usunięcia (np. 1,3-5, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return
    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return
    for index in selected:
        item = candidates[index]
        try:
            result = _run_cmd(item["command"], timeout=300)
            ok = result.returncode == 0
            detail = (result.stderr or result.stdout or "").strip()[:200]
        except (OSError, subprocess.TimeoutExpired) as exc:
            ok, detail = False, str(exc)
        style = "green" if ok else "red"
        click.echo(
            click.style(
                f"  {item['description']}: {'usunięto' if ok else detail}",
                fg=style,
            )
        )


# ── systemd journal ──────────────────────────────────────────────────────


def _cleanup_journal(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Vacuum the systemd journal down to a chosen size."""
    try:
        usage = _run_cmd(["journalctl", "--disk-usage"])
    except (OSError, subprocess.TimeoutExpired):
        usage = None
    if json_output:
        _echo_json({"usage": usage.stdout.strip() if usage else None})
        return
    if usage is None or usage.returncode != 0:
        click.echo(
            click.style("Błąd: `journalctl --disk-usage` niedostępny.", fg="red")
        )
        return
    click.echo(f"Aktualne zużycie journald: {usage.stdout.strip()}")
    if list_only:
        return
    if dry_run:
        _show_dry_run_commands(
            [["sudo", "journalctl", f"--vacuum-size={_JOURNAL_DEFAULT_SIZE}"]]
        )
        return
    if yes:
        size = _JOURNAL_DEFAULT_SIZE
    else:
        size = (
            click.prompt(
                "Docelowy rozmiar journal (np. 200M, 500M, 1G; puste = pomiń)",
                default="",
                show_default=False,
            )
            .strip()
            .upper()
        )
        if not size:
            click.echo("Pominięto.")
            return
        if not re.match(r"^[0-9]+[KMG]$", size):
            click.echo(click.style(f"Nieprawidłowy rozmiar: {size}", fg="red"))
            return
        if not _confirm_remove():
            click.echo("Anulowano.")
            return
    try:
        result = _run_cmd(
            ["sudo", "journalctl", f"--vacuum-size={size}"], timeout=300
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        click.echo(click.style(f"Błąd journalctl: {exc}", fg="red"))
        return
    if result.returncode == 0:
        tail = (result.stdout or "").strip().splitlines()
        click.echo(
            click.style(f"Vacuum do {size}: {tail[-1] if tail else 'done'}", fg="green")
        )
    else:
        detail = (result.stderr or "błąd").strip()[:200]
        click.echo(click.style(f"Błąd journalctl: {detail}", fg="red"))


# ── ~/.cache ─────────────────────────────────────────────────────────────


def _user_cache_candidates() -> list[dict]:
    """Top-level ~/.cache entries; safe ones are regenerable tool caches."""
    root = Path.home() / ".cache"
    if not root.is_dir():
        return []
    candidates = []
    for entry in sorted(root.iterdir()):
        if entry.is_symlink():
            continue
        candidates.append(
            {
                "description": entry.name,
                "path": entry,
                "size_bytes": _dir_size(entry),
                "safe": entry.name in _USER_CACHE_SAFE,
                "note": "regenerowalny cache" if entry.name in _USER_CACHE_SAFE else "",
            }
        )
    candidates.sort(key=lambda item: -item["size_bytes"])
    return candidates


def _cleanup_user_cache(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Remove selected ~/.cache entries; --yes touches only known-safe caches."""
    candidates = _user_cache_candidates()
    if json_output:
        _echo_json(
            {
                "candidates": [
                    {
                        "description": c["description"],
                        "size_bytes": c["size_bytes"],
                        "path": str(c["path"]),
                        "safe": c["safe"],
                    }
                    for c in candidates
                ]
            }
        )
        return
    if not candidates:
        click.echo(click.style("Brak katalogów w ~/.cache.", fg="green"))
        return
    _display_candidates("~/.cache — katalogi:", candidates)
    if list_only:
        return
    if yes:
        selected = [i for i, item in enumerate(candidates) if item["safe"]]
        skipped = len(candidates) - len(selected)
        if skipped:
            click.echo(
                click.style(
                    f"Tryb --yes pomija {skipped} pozycji spoza listy bezpiecznych; "
                    "wybierz je ręcznie bez --yes.",
                    fg="yellow",
                )
            )
    else:
        selected = _choose(candidates, "Numery katalogów do usunięcia (np. 1,2, all)")
    if not selected:
        click.echo("Pominięto.")
        return
    if dry_run:
        _show_dry_run_commands(
            [["rm", "-rf", str(candidates[i]["path"])] for i in selected]
        )
        return
    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return
    _remove_selected(candidates, selected)


# ── JetBrains Toolbox / caches ───────────────────────────────────────────


def _jetbrains_candidates() -> list[dict]:
    """Stale Toolbox channels (all but newest per app) + IDE caches."""
    home = Path.home()
    candidates = []
    apps_dir = home / ".local/share/JetBrains/Toolbox/apps"
    if apps_dir.is_dir():
        for app_dir in sorted(apps_dir.iterdir()):
            if not app_dir.is_dir():
                continue
            channels = sorted(
                (
                    (int(match.group(1)), child)
                    for child in app_dir.iterdir()
                    if (match := re.fullmatch(r"ch-(\d+)", child.name))
                ),
                reverse=True,
            )
            for number, path in channels[1:]:
                candidates.append(
                    {
                        "description": f"{app_dir.name} ch-{number}",
                        "path": path,
                        "size_bytes": _dir_size(path),
                        "note": "stary kanał Toolbox",
                    }
                )
    cache_dir = home / ".cache/JetBrains"
    if cache_dir.is_dir():
        for entry in sorted(cache_dir.iterdir()):
            if entry.is_symlink():
                continue
            candidates.append(
                {
                    "description": entry.name,
                    "path": entry,
                    "size_bytes": _dir_size(entry),
                    "note": "cache IDE",
                }
            )
    candidates.sort(key=lambda item: -item["size_bytes"])
    return candidates


def _cleanup_jetbrains(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Remove stale JetBrains Toolbox channels and IDE caches."""
    candidates = _jetbrains_candidates()
    if json_output:
        _echo_json(
            {
                "candidates": [
                    {
                        "description": c["description"],
                        "size_bytes": c["size_bytes"],
                        "path": str(c["path"]),
                    }
                    for c in candidates
                ]
            }
        )
        return
    if not candidates:
        click.echo(
            click.style("Brak starych kanałów Toolbox ani cache IDE.", fg="green")
        )
        return
    _display_candidates("JETBRAINS — stare kanały i cache:", candidates)
    if list_only:
        return
    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery pozycji do usunięcia (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return
    if dry_run:
        _show_dry_run_commands(
            [["rm", "-rf", str(candidates[i]["path"])] for i in selected]
        )
        return
    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return
    _remove_selected(candidates, selected)


# ── libvirt images ───────────────────────────────────────────────────────


def _virsh_domains(uri: str) -> list[str] | None:
    try:
        result = _run_cmd(["virsh", "-c", uri, "list", "--all", "--name"])
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return [name for name in result.stdout.split() if name]


def _libvirt_attached_images() -> set[str] | None:
    """Disk image paths attached to defined domains on any accessible URI."""
    attached: set[str] = set()
    seen = False
    for uri in _LIBVIRT_URIS:
        domains = _virsh_domains(uri)
        if domains is None:
            continue
        seen = True
        for domain in domains:
            result = _run_cmd(
                ["virsh", "-c", uri, "domblklist", domain], timeout=60
            )
            if result.returncode != 0:
                continue
            for line in result.stdout.splitlines()[2:]:
                parts = line.split()
                if len(parts) >= 4 and parts[0] == "file" and parts[3] != "-":
                    attached.add(parts[3])
    return attached if seen else None


def _cleanup_libvirt(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Remove ~/.local/share/libvirt images not attached to any domain."""
    attached = _libvirt_attached_images()
    images_dir = Path.home() / ".local/share/libvirt/images"
    candidates = []
    error = None
    if attached is None:
        error = "Nie udało się zweryfikować podpięcia obrazów (virsh niedostępny)"
    elif images_dir.is_dir():
        for entry in sorted(images_dir.iterdir()):
            if not entry.is_file() or entry.suffix.lower() not in _IMAGE_SUFFIXES:
                continue
            if str(entry) in attached:
                continue
            candidates.append(
                {
                    "description": entry.name,
                    "path": entry,
                    "size_bytes": entry.stat().st_size,
                    "note": "niepodpięty do żadnej domeny",
                }
            )
    if json_output:
        _echo_json(
            {
                "error": error,
                "candidates": [
                    {
                        "description": c["description"],
                        "size_bytes": c["size_bytes"],
                        "path": str(c["path"]),
                    }
                    for c in candidates
                ],
            }
        )
        return
    if error:
        click.echo(click.style(f"Błąd: {error}", fg="red"))
        return
    if not candidates:
        click.echo(click.style("Brak niepodpiętych obrazów libvirt.", fg="green"))
        return
    _display_candidates("LIBVIRT — obrazy bez domeny:", candidates)
    if list_only:
        return
    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery obrazów do usunięcia (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return
    if dry_run:
        _show_dry_run_commands(
            [["rm", str(candidates[i]["path"])] for i in selected]
        )
        return
    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return
    _remove_selected(candidates, selected)


# ── gitive-isolated workspaces ───────────────────────────────────────────


def _gitive_container_names() -> set[str] | None:
    """Names of all containers (running or stopped); None when docker is down."""
    try:
        result = _run_cmd(["docker", "ps", "-a", "--format", "{{.Names}}"])
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return {name for name in result.stdout.split() if name}


def _cleanup_gitive(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Remove gitive-isolated workspaces not referenced by any container."""
    names = _gitive_container_names()
    root = Path.home() / ".local/share/gitive-isolated"
    candidates = []
    error = None
    if names is None:
        error = "Nie udało się zweryfikować powiązania z kontenerami (docker niedostępny)"
    elif root.is_dir():
        for rootfs in sorted(root.rglob("rootfs")):
            workspace = rootfs.parent
            if not rootfs.is_dir() or workspace.is_symlink():
                continue
            if any(workspace.name in name for name in names):
                continue
            candidates.append(
                {
                    "description": str(workspace.relative_to(root)),
                    "path": workspace,
                    "size_bytes": _dir_size(workspace),
                    "note": "brak kontenera z tym workspace",
                }
            )
    if json_output:
        _echo_json(
            {
                "error": error,
                "candidates": [
                    {
                        "description": c["description"],
                        "size_bytes": c["size_bytes"],
                        "path": str(c["path"]),
                    }
                    for c in candidates
                ],
            }
        )
        return
    if error:
        click.echo(click.style(f"Błąd: {error}", fg="red"))
        return
    if not candidates:
        click.echo(
            click.style("Brak osieroconych workspace gitive-isolated.", fg="green")
        )
        return
    _display_candidates("GITIVE — nieużywane workspace:", candidates)
    if list_only:
        return
    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery workspace do usunięcia (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return
    if dry_run:
        _show_dry_run_commands(
            [["rm", "-rf", str(candidates[i]["path"])] for i in selected]
        )
        return
    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return
    _remove_selected(candidates, selected)


# ── docker buildx caches + dangling images ───────────────────────────────


def _docker_buildx_builders() -> list[dict] | None:
    """Return buildx builders (name, driver, current) or None if unavailable."""
    try:
        result = _run_cmd(["docker", "buildx", "ls"], timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    builders = []
    for line in result.stdout.splitlines()[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("\\_"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        name = parts[0]
        builders.append(
            {
                "name": name.rstrip("*"),
                "driver": parts[1],
                "current": name.endswith("*"),
            }
        )
    return builders


def _builder_cache_bytes(name: str) -> tuple[int, int] | None:
    """Return (total, reclaimable) bytes of a builder's cache or None."""
    try:
        result = _run_cmd(
            ["docker", "buildx", "du", "--builder", name], timeout=300
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    total = reclaimable = None
    for line in result.stdout.splitlines():
        match = re.match(r"(Total|Reclaimable):\s*(\S+)", line.strip())
        if not match:
            continue
        if match.group(1) == "Total":
            total = _size_to_bytes(match.group(2))
        else:
            reclaimable = _size_to_bytes(match.group(2))
    if total is None:
        return None
    return total, reclaimable if reclaimable is not None else total


def _dangling_images() -> dict | None:
    """Return count and approx bytes of dangling (<none>) images."""
    try:
        result = _run_cmd(
            ["docker", "images", "-f", "dangling=true", "--format", "{{.Size}}"]
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    sizes = [
        _size_to_bytes(line) for line in result.stdout.splitlines() if line.strip()
    ]
    return {"count": len(sizes), "bytes": sum(sizes)}


def _docker_buildcache_scan() -> dict:
    """Collect prune candidates: every buildx builder cache + dangling images."""
    targets: list[dict] = []
    builders = _docker_buildx_builders()
    if builders is None:
        return {"error": "docker buildx niedostępny", "targets": []}
    for builder in builders:
        usage = _builder_cache_bytes(builder["name"])
        targets.append(
            {
                "kind": "builder",
                "name": builder["name"],
                "driver": builder["driver"],
                "current": builder["current"],
                "total_bytes": usage[0] if usage else None,
                "reclaimable_bytes": usage[1] if usage else None,
                "command": [
                    "docker",
                    "buildx",
                    "prune",
                    "--builder",
                    builder["name"],
                    "--all",
                    "--force",
                ],
            }
        )
    dangling = _dangling_images()
    if dangling and dangling["count"]:
        targets.append(
            {
                "kind": "dangling-images",
                "name": "obrazy <none>",
                "driver": "docker",
                "current": False,
                "total_bytes": dangling["bytes"],
                "reclaimable_bytes": dangling["bytes"],
                "count": dangling["count"],
                "command": ["docker", "image", "prune", "--force"],
            }
        )
    return {"error": None, "targets": targets}


def _cleanup_docker_buildcache(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Prune every buildx builder's cache (incl. docker-container) + dangling images.

    ``docker builder prune`` covers only the currently selected builder, which
    is why fixos cleanup --docker-all leaves docker-container buildkit
    instances (e.g. ``arm64-builder``) untouched — this action iterates
    ``docker buildx ls`` and prunes each builder explicitly.
    """
    scan = _docker_buildcache_scan()
    if json_output:
        _echo_json(scan)
        return
    if scan["error"]:
        click.echo(click.style(f"Błąd: {scan['error']}", fg="red"))
        return
    targets = scan["targets"]
    if not targets:
        click.echo(
            click.style("Brak cache builderów i wiszących obrazów.", fg="green")
        )
        return

    candidates = []
    for target in targets:
        if target["kind"] == "dangling-images":
            label = f"{target['name']} ({target['count']} szt.)"
        else:
            label = f"builder {target['name']} ({target['driver']})"
        note = "bieżący builder" if target.get("current") else ""
        reclaimable = target.get("reclaimable_bytes")
        if reclaimable is not None:
            note = (
                f"{note}, reclaimable ~{_format_bytes(reclaimable)}"
                if note
                else f"reclaimable ~{_format_bytes(reclaimable)}"
            )
        candidates.append(
            {
                "description": label,
                "size_bytes": target["total_bytes"] or 0,
                "note": note,
            }
        )
    _display_candidates("DOCKER — cache builderów i wiszące obrazy:", candidates)
    if list_only:
        return
    if dry_run:
        _show_dry_run_commands([target["command"] for target in targets])
        return

    selected = (
        list(range(len(targets)))
        if yes
        else _choose(candidates, "Numery pozycji do wyczyszczenia (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return
    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return
    for index in selected:
        target = targets[index]
        label = candidates[index]["description"]
        try:
            result = _run_cmd(target["command"], timeout=3600)
            ok = result.returncode == 0
            output = (result.stdout or result.stderr or "").strip()
        except (OSError, subprocess.TimeoutExpired) as exc:
            ok, output = False, str(exc)
        if ok:
            tail = output.splitlines()
            click.echo(
                click.style(f"  {label}: {tail[-1] if tail else 'done'}", fg="green")
            )
        else:
            click.echo(click.style(f"  {label}: błąd — {output[:200]}", fg="red"))


# ── /tmp stale files and directories ─────────────────────────────────────

_EXCLUDED_TMP_PREFIXES = (
    ".X11-unix",
    ".ICE-unix",
    ".XIM-unix",
    ".font-unix",
    ".X",
    ".tmux-",
    "ssh-",
    "systemd-private-",
    "snap.",
    "snap-",
)


def _scan_tmp(
    days: float = DEFAULT_TMP_UNUSED_DAYS,
    tmp_dir: Path | str | None = None,
) -> list[dict]:
    """Scan and return files/directories in /tmp older than `days` (default 1 day).

    System sockets, FIFOs, and protected directories (.X11-unix, .ICE-unix, .X*-lock,
    .tmux-*, ssh-*, systemd-private-*, etc.) are excluded.
    """
    import stat as stat_module
    import time

    now = time.time()
    cutoff_seconds = days * 86400
    tmp_path = Path(tmp_dir) if tmp_dir is not None else Path("/tmp")
    candidates = []

    if tmp_path.is_dir():
        try:
            for item in sorted(tmp_path.iterdir()):
                name = item.name
                if any(name.startswith(p) for p in _EXCLUDED_TMP_PREFIXES):
                    continue
                try:
                    stat_val = item.lstat()
                    # Skip unix domain sockets and named pipes (FIFOs)
                    if stat_module.S_ISSOCK(stat_val.st_mode) or stat_module.S_ISFIFO(
                        stat_val.st_mode
                    ):
                        continue
                    mtime = stat_val.st_mtime
                    age_seconds = now - mtime
                    if age_seconds >= cutoff_seconds:
                        size = (
                            stat_val.st_size if not item.is_dir() else _dir_size(item)
                        )
                        age_days = age_seconds / 86400
                        candidates.append({
                            "description": f"{name} (wiek: {age_days:.1f} dni)",
                            "path": item,
                            "name": name,
                            "size_bytes": size,
                            "note": f"{age_days:.1f} dni",
                            "age_days": age_days,
                        })
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass

    return candidates


def _cleanup_tmp(
    json_output: bool,
    dry_run: bool,
    list_only: bool,
    yes: bool,
    days: float = DEFAULT_TMP_UNUSED_DAYS,
    tmp_dir: Path | str | None = None,
) -> None:
    """Scan and remove files/directories in /tmp older than `days` (default 1 day).

    System sockets and locks like .X11-unix, .ICE-unix, .X*-lock are excluded.
    """
    candidates = _scan_tmp(days=days, tmp_dir=tmp_dir)

    if json_output:
        _echo_json({
            "days": days,
            "candidates": [
                {
                    "description": c["description"],
                    "path": str(c["path"]),
                    "size_bytes": c["size_bytes"],
                    "note": c["note"],
                }
                for c in candidates
            ],
            "total_bytes": sum(c["size_bytes"] for c in candidates),
        })
        return

    if not candidates:
        click.echo(
            click.style(f"Brak plików w /tmp starszych niż {days:.1f} dni.", fg="green")
        )
        return

    _display_candidates(f"/tmp — pliki i katalogi starsze niż {days:.1f} dni:", candidates)
    if list_only:
        return

    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery pozycji do usunięcia (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return

    if dry_run:
        _show_dry_run_commands(
            [["rm", "-rf", str(candidates[i]["path"])] for i in selected]
        )
        return

    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return

    _remove_selected(candidates, selected)


# ── Retention duration parser ────────────────────────────────────────────


def parse_retention_days(
    retention: str | float | None,
    default_days: float = 1.0,
) -> float:
    """Parse a human retention string into float days.

    Supports formats like:
      - '24h', '12h', '1.5h' (hours -> days / 24)
      - '1d', '7d', '30d', '0.5d' (days)
      - '2w' (weeks -> days * 7)
      - '30m' (minutes -> days / 1440)
      - Plain number: treated as days
    """
    if retention is None:
        return default_days
    if isinstance(retention, (int, float)):
        return max(0.0, float(retention))
    text = str(retention).strip().lower()
    if not text:
        return default_days

    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([a-z]*)$", text)
    if not match:
        try:
            return max(0.0, float(text))
        except ValueError:
            raise ValueError(
                f"Nieprawidłowy format retencji: {retention!r} (oczekiwano np. 24h, 7d, 30d)"
            )

    val = float(match.group(1))
    unit = match.group(2)
    if not unit or unit in ("d", "day", "days", "dni", "doba", "doby"):
        return max(0.0, val)
    if unit in ("h", "hr", "hrs", "hour", "hours", "godz", "godzina", "godziny"):
        return max(0.0, val / 24.0)
    if unit in ("m", "min", "mins", "minute", "minutes", "minut", "minuta", "minuty"):
        return max(0.0, val / 1440.0)
    if unit in ("w", "wk", "wks", "week", "weeks", "tydz", "tygodni", "tygodnie"):
        return max(0.0, val * 7.0)
    if unit in ("s", "sec", "secs", "second", "seconds", "sekund", "sekunda", "sekundy"):
        return max(0.0, val / 86400.0)

    raise ValueError(
        f"Nieznana jednostka retencji: {unit!r} w {retention!r} (dozwolone: h, d, w, m)"
    )


# ── Trash (~/.local/share/Trash) ──────────────────────────────────────────


def _scan_trash(
    days: float = DEFAULT_TRASH_UNUSED_DAYS,
    trash_dir: Path | str | None = None,
) -> list[dict]:
    """Scan and return items in Trash older than `days`.

    Inspects ~/.local/share/Trash/files and matching info files.
    """
    import time

    now = time.time()
    cutoff_seconds = days * 86400.0
    trash_path = (
        Path(trash_dir).expanduser()
        if trash_dir is not None
        else Path("~/.local/share/Trash").expanduser()
    )
    candidates = []

    files_dir = trash_path / "files"
    info_dir = trash_path / "info"

    scan_dirs = [files_dir] if files_dir.is_dir() else ([trash_path] if trash_path.is_dir() else [])

    for target_dir in scan_dirs:
        try:
            for item in sorted(target_dir.iterdir()):
                try:
                    stat_val = item.lstat()
                    mtime = stat_val.st_mtime
                    age_seconds = now - mtime
                    if age_seconds >= cutoff_seconds or days <= 0:
                        size = (
                            stat_val.st_size if not item.is_dir() else _dir_size(item)
                        )
                        age_days = age_seconds / 86400.0
                        info_file = info_dir / f"{item.name}.trashinfo"
                        candidates.append({
                            "description": f"{item.name} (wiek: {age_days:.1f} dni)",
                            "path": item,
                            "info_path": info_file if info_file.exists() else None,
                            "name": item.name,
                            "size_bytes": size,
                            "note": f"{age_days:.1f} dni",
                            "age_days": age_days,
                        })
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass

    return candidates


def _cleanup_trash(
    json_output: bool,
    dry_run: bool,
    list_only: bool,
    yes: bool,
    days: float = DEFAULT_TRASH_UNUSED_DAYS,
    trash_dir: Path | str | None = None,
) -> None:
    """Scan and remove files/directories in Trash older than `days`."""
    candidates = _scan_trash(days=days, trash_dir=trash_dir)

    if json_output:
        _echo_json({
            "days": days,
            "candidates": [
                {
                    "description": c["description"],
                    "path": str(c["path"]),
                    "size_bytes": c["size_bytes"],
                    "note": c["note"],
                }
                for c in candidates
            ],
            "total_bytes": sum(c["size_bytes"] for c in candidates),
        })
        return

    if not candidates:
        click.echo(
            click.style(f"Brak plików w koszu starszych niż {days:.1f} dni.", fg="green")
        )
        return

    _display_candidates(f"Kosz użytkownika — pliki starsze niż {days:.1f} dni:", candidates)
    if list_only:
        return

    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery pozycji do usunięcia z kosza (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return

    if dry_run:
        _show_dry_run_commands(
            [["rm", "-rf", str(candidates[i]["path"])] for i in selected]
        )
        return

    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return

    for index in selected:
        item = candidates[index]
        ok, detail = _remove_path(item["path"])
        info_path = item.get("info_path")
        if info_path and isinstance(info_path, Path) and info_path.exists():
            _remove_path(info_path)
        style = "green" if ok else "red"
        click.echo(click.style(f"  {item['description']}: {detail}", fg=style))


# ── Thumbnails (~/.cache/thumbnails) ──────────────────────────────────────


def _scan_thumbnails(
    days: float = DEFAULT_THUMBNAILS_UNUSED_DAYS,
    thumbnails_dir: Path | str | None = None,
) -> list[dict]:
    """Scan and return thumbnail cache candidates in ~/.cache/thumbnails older than `days`."""
    import time

    now = time.time()
    cutoff_seconds = days * 86400.0
    thumb_path = (
        Path(thumbnails_dir).expanduser()
        if thumbnails_dir is not None
        else Path("~/.cache/thumbnails").expanduser()
    )
    candidates = []

    if not thumb_path.is_dir():
        return candidates

    subdirs = ["normal", "large", "x-large", "xx-large", "fail"]
    found_subdirs = [thumb_path / s for s in subdirs if (thumb_path / s).is_dir()]
    if not found_subdirs:
        found_subdirs = [thumb_path]

    for sdir in found_subdirs:
        try:
            old_files = []
            total_size = 0
            for item in sdir.iterdir():
                try:
                    if item.is_file():
                        stat_val = item.lstat()
                        mtime = stat_val.st_mtime
                        age_seconds = now - mtime
                        if age_seconds >= cutoff_seconds or days <= 0:
                            old_files.append(item)
                            total_size += stat_val.st_size
                except (OSError, PermissionError):
                    continue
            if old_files:
                sub_name = sdir.name
                candidates.append({
                    "description": f"{sub_name} ({len(old_files)} plików)",
                    "name": sub_name,
                    "path": sdir,
                    "paths": old_files,
                    "items_count": len(old_files),
                    "size_bytes": total_size,
                    "note": f"{len(old_files)} plików, starsze niż {days:.1f} dni",
                    "age_days": days,
                })
        except (OSError, PermissionError):
            continue

    return candidates


def _cleanup_thumbnails(
    json_output: bool,
    dry_run: bool,
    list_only: bool,
    yes: bool,
    days: float = DEFAULT_THUMBNAILS_UNUSED_DAYS,
    thumbnails_dir: Path | str | None = None,
) -> None:
    """Scan and remove cached thumbnails older than `days`."""
    candidates = _scan_thumbnails(days=days, thumbnails_dir=thumbnails_dir)

    if json_output:
        _echo_json({
            "days": days,
            "candidates": [
                {
                    "description": c["description"],
                    "path": str(c["path"]),
                    "items_count": c.get("items_count", 0),
                    "size_bytes": c["size_bytes"],
                    "note": c["note"],
                }
                for c in candidates
            ],
            "total_bytes": sum(c["size_bytes"] for c in candidates),
        })
        return

    if not candidates:
        click.echo(
            click.style(
                f"Brak miniaturek w ~/.cache/thumbnails starszych niż {days:.1f} dni.",
                fg="green",
            )
        )
        return

    _display_candidates(
        f"Miniaturki ~/.cache/thumbnails starsze niż {days:.1f} dni:", candidates
    )
    if list_only:
        return

    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery kategorii miniaturek do usunięcia (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return

    if dry_run:
        _show_dry_run_commands(
            [
                ["rm", "-f", f"{len(candidates[i].get('paths', []))} plików w {candidates[i]['path']}"]
                for i in selected
            ]
        )
        return

    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return

    for index in selected:
        item = candidates[index]
        paths = item.get("paths", [])
        removed_count = 0
        for p in paths:
            ok, _ = _remove_path(p)
            if ok:
                removed_count += 1
        click.echo(
            click.style(
                f"  {item['description']}: usunięto {removed_count}/{len(paths)} plików",
                fg="green",
            )
        )


# ── Policy & Retention Transparency Matrix ───────────────────────────────


CLEANUP_POLICIES: list[dict[str, Any]] = [
    {
        "id": "tmp",
        "flag": "--tmp",
        "name": "Pliki tymczasowe (/tmp)",
        "direct": True,
        "default_retention": "24h (1.0 d)",
        "default_days": 1.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Przedawnione pliki i katalogi w /tmp",
        "protected": "Gniazda unix (is_socket), potoki FIFO (is_fifo), prefiksy systemowe (.X11-unix, .ICE-unix, .tmux-*, ssh-*, systemd-private-*, snap.*), pliki < retencja",
        "example": "fixos cleanup --tmp --retention 24h",
    },
    {
        "id": "trash",
        "flag": "--trash",
        "name": "Kosz użytkownika (~/.local/share/Trash)",
        "direct": True,
        "default_retention": "14d",
        "default_days": 14.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Pliki w koszu starsze niż zadana retencja",
        "protected": "Pliki w koszu nowsze niż retencja",
        "example": "fixos cleanup --trash --retention 7d",
    },
    {
        "id": "thumbnails",
        "flag": "--thumbnails",
        "name": "Cache miniaturek (~/.cache/thumbnails)",
        "direct": True,
        "default_retention": "30d",
        "default_days": 30.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Wygenerowane miniaturki obrazów i wideo w ~/.cache/thumbnails",
        "protected": "Miniaturki nowsze niż retencja; pamięć regenerowalna na żądanie",
        "example": "fixos cleanup --thumbnails --retention 30d",
    },
    {
        "id": "docker-buildcache",
        "flag": "--docker-buildcache",
        "name": "Docker buildx builder cache",
        "direct": True,
        "default_retention": "7d",
        "default_days": 7.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Cache builderów buildx (w tym docker-container) oraz wiszące obrazy <none>",
        "protected": "Nazwane obrazy, aktywne kontenery, wolumeny danych",
        "example": "fixos cleanup --docker-buildcache",
    },
    {
        "id": "docker-old",
        "flag": "--docker-old",
        "name": "Stare obrazy i cache Docker",
        "direct": True,
        "default_retention": "30d",
        "default_days": 30.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Nieużywane obrazy Docker i build cache starsze niż retencja",
        "protected": "Aktywne kontenery, powiązane obrazy, wolumeny danych",
        "example": "fixos cleanup --docker-old --retention 30d",
    },
    {
        "id": "docker-networks",
        "flag": "--docker-networks",
        "name": "Osierocone sieci Docker",
        "direct": True,
        "default_retention": "0d (wszystkie nieużywane)",
        "default_days": 0.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Niestandardowe sieci bez aktywnych endpointów",
        "protected": "Sieci domyślne (bridge, host, none) oraz sieci przypięte do kontenerów",
        "example": "fixos cleanup --docker-networks",
    },
    {
        "id": "docker-stale-services",
        "flag": "--docker-stale-services",
        "name": "Usługi z nieaktywnych repozytoriów Git",
        "direct": True,
        "default_retention": "3d",
        "default_days": 3.0,
        "risk_level": "review",
        "default_safe": False,
        "description": "Usługi z czystych repozytoriów Git nieaktywnych od zadanego czasu",
        "protected": "Brudne repozytoria, aktywne commity; zatrzymanie wymaga potwierdzenia",
        "example": "fixos cleanup --docker-stale-services --retention 7d",
    },
    {
        "id": "orphaned-projects",
        "flag": "--orphaned-projects",
        "name": "Osierocone kontenery Compose i procesy IDE",
        "direct": True,
        "default_retention": "3d / 12h",
        "default_days": 3.0,
        "risk_level": "review",
        "default_safe": False,
        "description": "Kontenery z brakującym katalogiem projektu i stare drzewa agentów IDE",
        "protected": "Przypięte projekty (--pin-orphan-project), bieżące IDE i procesy robocze",
        "example": "fixos cleanup --orphaned-projects --retention 3d",
    },
    {
        "id": "venvs-old",
        "flag": "--venvs-old",
        "name": "Stare środowiska venv w nieaktywnych projektach",
        "direct": True,
        "default_retention": "30d",
        "default_days": 30.0,
        "risk_level": "review",
        "default_safe": False,
        "description": "Katalogi venv/.venv w projektach bez aktywności przez zadany czas",
        "protected": "Aktywne procesy, otwarte pliki, bind-mounts, świeże commity",
        "example": "fixos cleanup --venvs-old --retention 30d",
    },
    {
        "id": "ollama-old",
        "flag": "--ollama-old",
        "name": "Nieużywane modele Ollama",
        "direct": True,
        "default_retention": "90d",
        "default_days": 90.0,
        "risk_level": "review",
        "default_safe": False,
        "description": "Modele LLM niezmieniane od 90 dni",
        "protected": "Aktualnie załadowane modele w pamięci",
        "example": "fixos cleanup --ollama-old --retention 60d",
    },
    {
        "id": "journal",
        "flag": "--journal",
        "name": "Dziennik systemowy systemd",
        "direct": True,
        "default_retention": "500M (rozmiar)",
        "default_days": 0.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Przycięcie journalctl do ustalonego rozmiaru",
        "protected": "Ostatnie wpisy dziennika systemowego",
        "example": "fixos cleanup --journal",
    },
    {
        "id": "snap-old",
        "flag": "--snap-old",
        "name": "Wyłączone rewizje pakietów snap",
        "direct": True,
        "default_retention": "wyłączone (od ręki)",
        "default_days": 0.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Stare, wyłączone rewizje pakietów snap",
        "protected": "Aktywne rewizje pakietów snap",
        "example": "fixos cleanup --snap-old",
    },
    {
        "id": "user-cache",
        "flag": "--user-cache",
        "name": "Pamięć podręczna użytkownika (~/.cache)",
        "direct": True,
        "default_retention": "regenerowalna (od ręki)",
        "default_days": 0.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Katalogi cache narzędzi (pip, uv, npm, yarn, pnpm, go-build, itp.)",
        "protected": "~/Videos, ~/Downloads, pliki autorskie użytkownika",
        "example": "fixos cleanup --user-cache",
    },
    {
        "id": "jetbrains",
        "flag": "--jetbrains",
        "name": "Stare IDE JetBrains i cache Toolbox",
        "direct": True,
        "default_retention": "stare wersje",
        "default_days": 0.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Stare wersje IDE z Toolbox oraz ~/.cache/JetBrains",
        "protected": "Ustawienia i konfiguracja w ~/.local/share/JetBrains",
        "example": "fixos cleanup --jetbrains",
    },
    {
        "id": "libvirt",
        "flag": "--libvirt",
        "name": "Nieprzypisane obrazy maszyn wirtualnych",
        "direct": True,
        "default_retention": "niepodpięte (od ręki)",
        "default_days": 0.0,
        "risk_level": "review",
        "default_safe": False,
        "description": "Obrazy w ~/.local/share/libvirt/images niepodpięte pod żadną domenę",
        "protected": "Obrazy podpięte pod zdefiniowane domeny libvirt",
        "example": "fixos cleanup --libvirt",
    },
    {
        "id": "gitive",
        "flag": "--gitive",
        "name": "Izolowane przestrzenie robocze gitive",
        "direct": True,
        "default_retention": "osierocone (od ręki)",
        "default_days": 0.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Stare katalogi w ~/.local/share/gitive-isolated",
        "protected": "Workspace'y powiązane z działającymi kontenerami",
        "example": "fixos cleanup --gitive",
    },
]


def _display_cleanup_policies(json_output: bool = False) -> None:
    """Display the transparency policy matrix of cleanable targets, retention and risk levels."""
    if json_output:
        _echo_json({"policies": CLEANUP_POLICIES})
        return

    header = (
        f"{'Flaga':<20} {'Bezpośrednio':<13} {'Domyślna retencja':<22} "
        f"{'Ryzyko':<11} {'Auto (-y)':<10} {'Zasób'}"
    )
    divider = "=" * 100

    click.echo(
        click.style(
            "\nPOLITYKA RETENCJI I BEZPOŚREDNIEGO CZYSZCZENIA (fixOS)",
            fg="cyan",
            bold=True,
        )
    )
    click.echo(divider)
    click.echo(click.style(header, bold=True))
    click.echo("-" * 100)

    for p in CLEANUP_POLICIES:
        direct_str = "TAK" if p["direct"] else "NIE"
        auto_str = "TAK" if p["default_safe"] else "NIE"
        risk_color = (
            "green"
            if p["risk_level"] == "safe"
            else ("yellow" if p["risk_level"] == "review" else "red")
        )
        risk_styled = click.style(f"{p['risk_level']:<11}", fg=risk_color)
        click.echo(
            f"{click.style(p['flag'], fg='cyan'):<29} "
            f"{direct_str:<13} "
            f"{p['default_retention']:<22} "
            f"{risk_styled} "
            f"{auto_str:<10} "
            f"{p['name']}"
        )

    click.echo(divider)
    click.echo(
        click.style(
            "\nPrzykłady użycia z retencją czasową (h=godziny, d=dni, w=tygodnie):",
            fg="magenta",
            bold=True,
        )
    )
    click.echo("  fixos cleanup --tmp --retention 24h         # czyści pliki w /tmp starsze niż 24 godziny")
    click.echo("  fixos cleanup --trash --retention 7d        # czyści kosz starszy niż 7 dni")
    click.echo("  fixos cleanup --thumbnails --retention 30d  # czyści miniaturki starsze niż 30 dni")
    click.echo("  fixos cleanup --docker-old --retention 14d  # czyści nieużywane obrazy Dockera starsze niż 14 dni")
    click.echo("  fixos cleanup --policy                      # wyświetla tę tabelę polityk i retencji\n")


