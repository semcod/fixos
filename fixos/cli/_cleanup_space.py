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

import click

from fixos.cli._cleanup_utils import _format_bytes, _parse_selection

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
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


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
