"""Disk-space reclaim handlers for large, regenerable targets.

Each handler scans first, lists candidates with sizes, and removes only
explicitly selected entries (or all of them with ``--yes``). User documents
(~/Videos, ~/Downloads, …) are never scanned for deletion.

Handler signature: ``fn(json_output, dry_run, list_only, yes)``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import click

from fixos.cli._cleanup_utils import _format_bytes, _parse_selection
from fixos.constants import (
    DEFAULT_STATE_OLD_DAYS,
    DEFAULT_THUMBNAILS_UNUSED_DAYS,
    DEFAULT_TMP_UNUSED_DAYS,
    DEFAULT_TRASH_UNUSED_DAYS,
    PROJECT_SCAN_DEFAULT_PATH,
    PROJECT_SCAN_MAX_DEPTH,
    PROJECT_SCAN_STALE_DAYS,
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
    "ccache",
    "sccache",
    "ruff",
    "mypy",
    "node",
    "node-gyp",
    "cursor-compile-cache",
    "gstreamer-1.0",
    "mesa_shader_cache_sf",
}


def _run_cmd(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Execute a command; module-level seam so tests can stub it."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


_DU_BATCH = 512


def _dir_sizes(paths: list[Path]) -> dict[str, int]:
    """Sizes in bytes for many directories with one ``du`` per batch.

    ``--count-links`` keeps each directory independent of the others, as a
    separate ``du`` would be; NUL-terminated output survives any file name.
    Paths missing from the result must be measured individually.
    """
    sizes: dict[str, int] = {}
    for start in range(0, len(paths), _DU_BATCH):
        batch = [str(path) for path in paths[start : start + _DU_BATCH]]
        try:
            result = _run_cmd(["du", "-sbl0", "--", *batch], timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            continue
        # du exits 1 when some subtree is unreadable but still prints totals.
        for record in result.stdout.split("\0"):
            size, sep, name = record.partition("\t")
            if sep and size.isdigit():
                sizes[name] = int(size)
    return sizes


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
    path = Path(path)
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
        return True, "usunięto"
    except PermissionError as exc:
        return False, f"PERMISSION_DENIED:{exc}"
    except OSError as exc:
        if exc.errno in (1, 13) or "permission denied" in str(exc).lower():
            return False, f"PERMISSION_DENIED:{exc}"
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
            if not path.exists():
                return True, "usunięto"
            return True, "oczyszczono zawartość"
        return False, str(exc)


_MAX_DISPLAY_CANDIDATES = 50


def _display_candidates(title: str, candidates: list[dict]) -> None:
    click.echo(f"\n{click.style(title, fg='magenta', bold=True)}")
    shown = candidates[:_MAX_DISPLAY_CANDIDATES]
    for index, item in enumerate(shown, 1):
        size = _format_bytes(item.get("size_bytes", 0))
        detail = item.get("note", "")
        suffix = f" — {detail}" if detail else ""
        click.echo(
            f"  [{index:3d}] {click.style(item['description'], fg='yellow')}: "
            f"{size}{suffix}"
        )
    if len(candidates) > _MAX_DISPLAY_CANDIDATES:
        hidden = candidates[_MAX_DISPLAY_CANDIDATES:]
        hidden_bytes = sum(item.get("size_bytes", 0) for item in hidden)
        click.echo(
            f"  ... i {len(hidden)} pozostałych pozycji "
            f"({_format_bytes(hidden_bytes)})"
        )
    total_bytes = sum(item.get("size_bytes", 0) for item in candidates)
    click.echo(
        f"\n  Kandydatów: {len(candidates)} (łącznie {_format_bytes(total_bytes)})"
    )


def _batch_sudo_remove_tmp(items: list[dict], path_key: str = "path") -> tuple[int, int]:
    """Remove root-owned /tmp items in batches using non-interactive sudo if available."""
    if not items or shutil.which("sudo") is None:
        return 0, 0
    safe_items = []
    for item in items:
        p = Path(item[path_key])
        if p.parent == Path("/tmp") and not any(
            p.name.startswith(pref) for pref in _EXCLUDED_TMP_PREFIXES
        ):
            safe_items.append(item)
    if not safe_items:
        return 0, 0
    removed = 0
    freed = 0
    chunk_size = 500
    for start in range(0, len(safe_items), chunk_size):
        chunk = safe_items[start : start + chunk_size]
        cmd = ["sudo", "-n", "rm", "-rf", "--", *[str(it[path_key]) for it in chunk]]
        try:
            res = _run_cmd(cmd, timeout=60)
            if res.returncode == 0:
                removed += len(chunk)
                freed += sum(int(it.get("size_bytes", 0) or 0) for it in chunk)
        except (OSError, subprocess.TimeoutExpired):
            break
    return removed, freed


def _project_artifact_allowed(
    path: Path | str | dict[str, Any],
    project_root: Path | str | None = None,
) -> bool:
    """Strictly validate that path is a safe project artifact directory inside project_root.

    The path must:
    - be an existing directory,
    - not be a symlink (neither the artifact itself nor any ancestor up to project root),
    - resolve strictly inside resolved project root (not equal to project root, not escaping),
    - not be a mount point and contain no nested mounts,
    - have the same filesystem device as project root.
    """
    if isinstance(path, dict):
        if project_root is None:
            project_root = path.get("project")
        path = path.get("path")

    if path is None:
        return False

    try:
        path = Path(path)
        if project_root is None:
            project_root = path.parent
        else:
            project_root = Path(project_root)
    except (TypeError, ValueError, OSError):
        return False

    # Path and project_root must be existing directories and not symlinks
    if path.is_symlink() or project_root.is_symlink():
        return False
    if not path.is_dir() or not project_root.is_dir():
        return False

    # Disallow forbidden critical names
    if path.name in (".git", "", ".", ".."):
        return False

    # Check structural relationship before resolving
    try:
        rel = path.absolute().relative_to(project_root.absolute())
    except ValueError:
        return False

    if rel == Path(".") or not rel.parts:
        return False

    # Ensure no symlinks in path segments from project_root down to path
    curr = project_root.absolute()
    for part in rel.parts:
        curr = curr / part
        if curr.is_symlink():
            return False

    # Check fully resolved paths to prevent symlink traversal or escaping
    try:
        resolved_proj = project_root.resolve()
        resolved_path = path.resolve()
    except (OSError, RuntimeError):
        return False

    if resolved_path.is_symlink() or resolved_proj.is_symlink():
        return False

    try:
        rel_resolved = resolved_path.relative_to(resolved_proj)
    except ValueError:
        return False

    if rel_resolved == Path(".") or not rel_resolved.parts:
        return False

    # Check plain path
    from fixos.diagnostics.venv_cleanup import _plain_path
    if not _plain_path(resolved_path):
        return False

    # Check mount points
    if path.is_mount() or resolved_path.is_mount():
        return False

    # Check filesystem devices
    try:
        dev_art = path.stat().st_dev
        dev_proj = project_root.stat().st_dev
        if dev_art != dev_proj:
            return False
    except OSError:
        pass

    # Check nested mounts inside path
    try:
        device = path.stat().st_dev
        for parent, dirs, _ in os.walk(path, followlinks=False):
            for name in dirs:
                child = Path(parent) / name
                if child.is_symlink():
                    continue
                if child.is_mount():
                    return False
                try:
                    if child.stat().st_dev != device:
                        return False
                except OSError:
                    pass
    except OSError:
        pass

    # Check system mount points via psutil if available
    try:
        import psutil
        mounts = {Path(part.mountpoint).resolve() for part in psutil.disk_partitions(all=True)}
        if any(m == resolved_path or resolved_path in m.parents for m in mounts):
            return False
    except (ImportError, OSError, RuntimeError, ValueError):
        pass

    return True


def _batch_sudo_remove_project_artifacts(
    items: list[dict], path_key: str = "path"
) -> tuple[int, int, list[dict]]:
    """Remove root-owned stale project artifacts in batches using non-interactive sudo if available.

    Only items that pass strict `_project_artifact_allowed` validation are removed.
    Returns (removed_count, freed_bytes, unhandled_items).
    """
    if not items:
        return 0, 0, []

    project_items: list[dict] = []
    for item in items:
        p = Path(item[path_key])
        if p.parent == Path("/tmp"):
            continue
        if "project" in item or (p.parent != Path("/") and p.parent != Path(".")):
            project_items.append(item)

    if not project_items:
        return 0, 0, []

    validated_safe: list[dict] = []
    unhandled: list[dict] = []

    for item in project_items:
        p = Path(item[path_key])
        proj = item.get("project") or p.parent
        if _project_artifact_allowed(p, proj):
            validated_safe.append(item)
        else:
            unhandled.append(item)
            click.echo(
                click.style(
                    f"  Pominięto usuwanie sudo dla {item.get('description', str(p))}: "
                    f"ścieżka nie przeszła weryfikacji bezpieczeństwa (symlink lub punkt montowania)",
                    fg="yellow",
                )
            )

    if not validated_safe:
        return 0, 0, unhandled

    if shutil.which("sudo") is None:
        unhandled.extend(validated_safe)
        return 0, 0, unhandled

    removed = 0
    freed = 0
    chunk_size = 50
    for start in range(0, len(validated_safe), chunk_size):
        chunk = validated_safe[start : start + chunk_size]
        cmd = ["sudo", "-n", "rm", "-rf", "--", *[str(it[path_key]) for it in chunk]]
        try:
            res = _run_cmd(cmd, timeout=60)
            if res.returncode == 0:
                removed += len(chunk)
                freed += sum(int(it.get("size_bytes", 0) or 0) for it in chunk)
            else:
                unhandled.extend(chunk)
        except (OSError, subprocess.TimeoutExpired):
            unhandled.extend(chunk)
            break

    return removed, freed, unhandled


def _remove_selected(
    candidates: list[dict], selected: list[int], path_key: str = "path"
) -> None:
    verbose = len(selected) <= _MAX_DISPLAY_CANDIDATES
    removed_count = 0
    failed_count = 0
    freed_bytes = 0
    perm_denied_items: list[dict] = []
    for index in selected:
        item = candidates[index]
        ok, detail = _remove_path(item[path_key])
        if ok:
            removed_count += 1
            freed_bytes += int(item.get("size_bytes", 0) or 0)
        elif detail.startswith("PERMISSION_DENIED:"):
            perm_denied_items.append(item)
            detail = detail.removeprefix("PERMISSION_DENIED:")
            failed_count += 1
        else:
            failed_count += 1
        if verbose:
            style = "green" if ok else "red"
            click.echo(click.style(f"  {item['description']}: {detail}", fg=style))
    if perm_denied_items:
        sudo_removed, sudo_freed = _batch_sudo_remove_tmp(perm_denied_items, path_key=path_key)
        if sudo_removed > 0:
            removed_count += sudo_removed
            freed_bytes += sudo_freed
            failed_count = max(0, failed_count - sudo_removed)
            if verbose:
                click.echo(
                    click.style(
                        f"  Usunięto przez sudo (/tmp): {sudo_removed} pozycji ({_format_bytes(sudo_freed)})",
                        fg="green",
                    )
                )

        proj_removed, proj_freed, unhandled_proj = _batch_sudo_remove_project_artifacts(
            perm_denied_items, path_key=path_key
        )
        if proj_removed > 0:
            removed_count += proj_removed
            freed_bytes += proj_freed
            failed_count = max(0, failed_count - proj_removed)
            if verbose:
                click.echo(
                    click.style(
                        f"  Usunięto przez sudo (projekty): {proj_removed} pozycji ({_format_bytes(proj_freed)})",
                        fg="green",
                    )
                )
        if unhandled_proj:
            click.echo(
                click.style(
                    f"  Brak uprawnień (PermissionError) dla {len(unhandled_proj)} artefaktów projektów:",
                    fg="yellow",
                )
            )
            for it in unhandled_proj[:_MAX_DISPLAY_CANDIDATES]:
                click.echo(
                    click.style(
                        f"    - {it.get('description', it.get(path_key))}: {it.get(path_key)}",
                        fg="yellow",
                    )
                )
            remediation_paths = [
                str(it[path_key])
                for it in unhandled_proj
                if not Path(it[path_key]).is_symlink() and not Path(it[path_key]).is_mount()
            ]
            if remediation_paths:
                click.echo(
                    click.style(
                        "  Polecenie naprawcze (uruchom ręcznie z sudo):",
                        fg="cyan",
                    )
                )
                paths_arg = " ".join(f"'{p}'" if " " in p else p for p in remediation_paths[:20])
                click.echo(
                    click.style(
                        f"    sudo rm -rf -- {paths_arg}",
                        fg="cyan",
                        bold=True,
                    )
                )
    if not verbose:
        click.echo(
            click.style(
                f"  Usunięto {removed_count}/{len(selected)} pozycji "
                f"(zwolniono {_format_bytes(freed_bytes)})",
                fg="green" if failed_count == 0 else "yellow",
            )
        )
        if failed_count:
            click.echo(
                click.style(f"  Nie udało się usunąć: {failed_count} pozycji", fg="red")
            )


def _show_dry_run_commands(commands: list[list[str]]) -> None:
    click.echo(click.style("[TRYB DRY-RUN] - brak faktycznych zmian", fg="cyan"))
    for command in commands[:_MAX_DISPLAY_CANDIDATES]:
        click.echo(f"  $ {' '.join(command)}")
    if len(commands) > _MAX_DISPLAY_CANDIDATES:
        click.echo(f"  ... i {len(commands) - _MAX_DISPLAY_CANDIDATES} pozostałych komend")


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
        snap_file = Path(f"/var/lib/snapd/snaps/{name}_{rev}.snap")
        try:
            size_bytes = snap_file.stat().st_size if snap_file.is_file() else 0
        except OSError:
            size_bytes = 0
        candidates.append(
            {
                "description": f"{name} (rewizja {rev})",
                "note": f"v{version}",
                "size_bytes": size_bytes,
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
    if root.is_symlink() or not root.is_dir():
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
    from fixos.cli._auto_cleanup import cache_path_allowed

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

    def safe_selection(indices: list[int]) -> list[int]:
        allowed = []
        for index in indices:
            path = candidates[index]["path"]
            if cache_path_allowed(Path.home(), path):
                allowed.append(index)
            else:
                click.echo(f"  {path}: pominięto (niebezpieczna ścieżka lub punkt montowania)")
        return allowed

    selected = safe_selection(selected)
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
    selected = safe_selection(selected)
    if selected:
        _remove_selected(candidates, selected, path_key="path")


# ── JetBrains Toolbox / caches ───────────────────────────────────────────


_JETBRAINS_DATA_DIR = re.compile(r"([A-Za-z]+)(\d{4})\.(\d+)")


def _toolbox_installs(home: Path) -> list[dict] | None:
    """Installs registered in Toolbox state.json; None when any cannot be read."""
    state = home / ".local/share/JetBrains/Toolbox/state.json"
    try:
        tools = json.loads(state.read_text(encoding="utf-8"))["tools"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    installs = []
    for tool in tools:
        location = Path(str(tool.get("installLocation") or ""))
        try:
            info = json.loads((location / "product-info.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        installs.append(
            {
                "tool_id": tool.get("toolId"),
                "build": tool.get("buildNumber"),
                "version": tool.get("displayVersion"),
                "location": location,
                "data_dir": info.get("dataDirectoryName"),
            }
        )
    return installs


def _jetbrains_stale_data_dirs(home: Path, installs: list[dict] | None) -> list[dict]:
    """Version data dirs no install uses and that a newer version superseded."""
    data_root = home / ".local/share/JetBrains"
    if installs is None or not data_root.is_dir():
        return []
    in_use = {install["data_dir"] for install in installs if install["data_dir"]}
    versions: dict[str, list[tuple[tuple[int, int], Path]]] = {}
    for entry in data_root.iterdir():
        match = _JETBRAINS_DATA_DIR.fullmatch(entry.name)
        if match and entry.is_dir() and not entry.is_symlink():
            version = (int(match.group(2)), int(match.group(3)))
            versions.setdefault(match.group(1), []).append((version, entry))
    candidates = []
    for items in versions.values():
        newest = max(version for version, _ in items)
        for version, entry in items:
            if version < newest and entry.name not in in_use:
                candidates.append(
                    {
                        "description": entry.name,
                        "path": entry,
                        "size_bytes": _dir_size(entry),
                        "note": "dane starej wersji IDE, żadna instalacja ich nie używa",
                    }
                )
    return candidates


def _toolbox_duplicate_installs(installs: list[dict] | None) -> list[str]:
    """Same tool and build registered more than once; remove through Toolbox."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for install in installs or []:
        groups.setdefault((str(install["tool_id"]), str(install["build"])), []).append(install)
    return [
        f"{tool} {items[0]['version']} ({build}) zainstalowany {len(items)}×: "
        + ", ".join(str(item["location"]) for item in items)
        + " — usuń zbędny kanał w JetBrains Toolbox"
        for (tool, build), items in sorted(groups.items())
        if len(items) > 1
    ]


def _jetbrains_candidates() -> list[dict]:
    """Stale Toolbox channels and unused version data; preserve system caches."""
    home = Path.home()
    candidates = _jetbrains_stale_data_dirs(home, _toolbox_installs(home))
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
    # IDE system roots mix rebuildable indexes with irreplaceable LocalHistory
    # and recovery/Toolbox state. Never offer a whole root for bulk deletion.
    candidates.sort(key=lambda item: -item["size_bytes"])
    return candidates


def _cleanup_jetbrains(
    json_output: bool, dry_run: bool, list_only: bool, yes: bool
) -> None:
    """Remove stale Toolbox channels and unused version data; retain system caches."""
    candidates = _jetbrains_candidates()
    advisories = _toolbox_duplicate_installs(_toolbox_installs(Path.home()))
    if (Path.home() / ".cache/JetBrains").is_dir():
        advisories.append(
            "Cache systemowy JetBrains jest chroniony: może zawierać "
            "LocalHistory (lokalne wersje plików), dane odzyskiwania i stan Toolbox."
        )
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
                ],
                "advisories": advisories,
            }
        )
        return
    for advisory in advisories:
        click.echo(click.style(f"  Uwaga: {advisory}", fg="yellow"))
    if not candidates:
        click.echo(
            click.style("Brak starych kanałów Toolbox ani nieużywanych danych wersji.", fg="green")
        )
        return
    _display_candidates("JETBRAINS — stare kanały i dane starych wersji:", candidates)
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


def _discover_gitive_rootfs_dirs(root: Path) -> list[Path]:
    """Find workspace `rootfs` directories under `root` without descending into `rootfs`."""
    import os

    found: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(root):
        if "rootfs" in dirnames:
            rootfs_path = Path(dirpath) / "rootfs"
            if rootfs_path.is_dir():
                found.append(rootfs_path)
            dirnames.remove("rootfs")
    found.sort()
    return found


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
        for rootfs in _discover_gitive_rootfs_dirs(root):
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


def _builder_cache_bytes(name: str) -> tuple[int, int | None] | None:
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
    return total, reclaimable


def _container_image_ids() -> set[str] | None:
    """Read image references for running and stopped containers, or unknown."""
    try:
        result = _run_cmd(
            ["docker", "container", "ls", "--all", "--quiet", "--no-trunc"]
        )
        if result.returncode != 0:
            return None
        containers = result.stdout.split()
        if not containers:
            return set()
        if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in containers):
            return None
        result = _run_cmd(
            ["docker", "container", "inspect", "--format", "{{.Image}}", *containers]
        )
        if result.returncode != 0:
            return None
        images = result.stdout.split()
        if len(images) != len(containers) or any(
            not re.fullmatch(r"sha256:[0-9a-f]{64}", item) for item in images
        ):
            return None
        return set(images)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _dangling_images() -> dict | None:
    """Count unreferenced dangling images; their logical sizes can share layers."""
    try:
        result = _run_cmd(
            [
                "docker", "images", "--no-trunc", "-f", "dangling=true",
                "--format", "{{.ID}}\t{{.Size}}",
            ]
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    rows = [line.split("\t") for line in result.stdout.splitlines() if line.strip()]
    if any(
        len(row) != 2 or not re.fullmatch(r"sha256:[0-9a-f]{64}", row[0])
        for row in rows
    ):
        return None
    used = _container_image_ids() if rows else set()
    sizes = [
        _size_to_bytes(size) for image, size in rows
        if used is None or image not in used
    ]
    return {"count": len(sizes), "bytes": sum(sizes), "usage_known": used is not None}


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
                # Shared layers and concurrent container creation prevent a
                # logical image-size sum from predicting actual prune results.
                "reclaimable_bytes": None,
                "usage_known": dangling["usage_known"],
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
        else:
            note = f"{note}, odzyskiwalny rozmiar nieznany".lstrip(", ")
        if target["kind"] == "dangling-images":
            note += "; suma rozmiarów obrazów obejmuje współdzielone warstwy"
            if not target["usage_known"]:
                note += "; użycie przez kontenery nieznane"
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
    directories = []

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
                        is_dir = stat_module.S_ISDIR(stat_val.st_mode)
                        age_days = age_seconds / 86400
                        candidates.append({
                            "description": f"{name} (wiek: {age_days:.1f} dni)",
                            "path": item,
                            "name": name,
                            "size_bytes": 0 if is_dir else stat_val.st_size,
                            "note": f"{age_days:.1f} dni",
                            "age_days": age_days,
                        })
                        if is_dir:
                            directories.append(candidates[-1])
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass

    # One `du` per directory meant thousands of processes on a busy /tmp.
    sizes = _dir_sizes([c["path"] for c in directories])
    for candidate in directories:
        size = sizes.get(str(candidate["path"]))
        candidate["size_bytes"] = size if size is not None else _dir_size(candidate["path"])

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
        "name": "Stare wersje IDE JetBrains",
        "direct": True,
        "default_retention": "stare wersje",
        "default_days": 0.0,
        "risk_level": "safe",
        "default_safe": True,
        "description": "Stare wersje IDE z Toolbox i nieużywane dane starszych wersji",
        "protected": "Dane wersji używanych przez instalacje z Toolbox state.json (także snap), ~/.config/JetBrains, ~/.cache/JetBrains (w tym LocalHistory)",
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
    {
        "id": "state-old",
        "flag": "--state-old",
        "name": "Stare partycje dzienne stanu aplikacji",
        "direct": True,
        "default_retention": f"{DEFAULT_STATE_OLD_DAYS} dni",
        "default_days": float(DEFAULT_STATE_OLD_DAYS),
        "risk_level": "safe",
        "default_safe": True,
        "description": "Katalogi YYYY/MM/DD w ~/.local/state i ~/.local/share starsze niż --days",
        "protected": "Bieżący dzień, pliki poza partycjami (np. checkpoint.sqlite3), dowiązania, inne systemy plików",
        "example": f"fixos cleanup --state-old --days {DEFAULT_STATE_OLD_DAYS} --dry-run",
    },
    {
        "id": "projects-old",
        "flag": "--projects-old",
        "name": "Artefakty projektów nieużywanych od ostatniego tygodnia",
        "direct": True,
        "default_retention": f"{PROJECT_SCAN_STALE_DAYS} dni",
        "default_days": float(PROJECT_SCAN_STALE_DAYS),
        "risk_level": "safe",
        "default_safe": True,
        "description": "Bezpieczne artefakty (venv/.venv, node_modules, target, cache) w projektach bez zmian > --days dni",
        "protected": "Aktywne procesy, projekty z nowszą aktywnością źródeł lub .worktrees, dowiązania, punkty montowania",
        "example": f"fixos cleanup --projects-old --days {PROJECT_SCAN_STALE_DAYS} --dry-run",
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


def _cleanup_build_caches(
    json_output: bool,
    dry_run: bool,
    list_only: bool,
    yes: bool,
    home_dir: Path | None = None,
    *,
    include_build_cache: bool = True,
    clean_state_old: bool = False,
    clean_projects_old: bool = False,
    stale_days: int = PROJECT_SCAN_STALE_DAYS,
) -> None:
    """Clean safe regenerable build/package caches (Cargo target/debug, ~/.npm/_cacache, conda tarballs)."""
    home = home_dir or Path.home()
    dirs_to_size: list[Path] = []
    seen_resolved: set[Path] = set()
    file_candidates: list[dict] = []

    if include_build_cache:
        github_root = home / "github"
        if github_root.is_dir():
            for pat in ("*/*/target/debug", "*/*/packages/*/target/debug"):
                for dbg in sorted(github_root.glob(pat)):
                    if dbg.is_dir() and not dbg.is_symlink():
                        try:
                            real = dbg.resolve()
                        except OSError:
                            real = dbg
                        if real not in seen_resolved:
                            seen_resolved.add(real)
                            dirs_to_size.append(dbg)

        npm_cache = home / ".npm" / "_cacache"
        if npm_cache.is_dir() and not npm_cache.is_symlink():
            dirs_to_size.append(npm_cache)

        conda_pkgs = home / "miniconda3" / "pkgs"
        if conda_pkgs.is_dir():
            for ext in ("*.tar.bz2", "*.conda"):
                for archive in sorted(conda_pkgs.glob(ext)):
                    try:
                        if archive.is_file() and not archive.is_symlink():
                            file_candidates.append(
                                {
                                    "description": f"miniconda3/pkgs/{archive.name}",
                                    "path": archive,
                                    "size_bytes": archive.stat().st_size,
                                    "note": "archiwum pakietu conda",
                                }
                            )
                    except OSError:
                        continue

    sizes = _dir_sizes(dirs_to_size) if dirs_to_size else {}
    candidates: list[dict] = []
    for d in dirs_to_size:
        sz = sizes.get(str(d))
        if sz is None:
            sz = _dir_size(d)
        if sz <= 0:
            continue
        try:
            rel = str(d.relative_to(home))
        except ValueError:
            rel = str(d)
        candidates.append(
            {
                "description": f"~/{rel}",
                "path": d,
                "size_bytes": sz,
                "note": "regenerowalny cache kompilacji/pakietów",
            }
        )
    candidates.extend(file_candidates)
    candidates.sort(key=lambda item: (-item.get("size_bytes", 0), item["description"]))

    if json_output:
        _echo_json(
            {
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
            }
        )
        return

    if include_build_cache:
        if not candidates:
            click.echo(click.style("Brak cache kompilacji/pakietów do wyczyszczenia.", fg="green"))
        else:
            _display_candidates("CACHE KOMPILACJI I PAKIETÓW (target/debug, npm, conda):", candidates)
            if not list_only:
                selected = (
                    list(range(len(candidates)))
                    if yes
                    else _choose(candidates, "Numery pozycji do usunięcia (np. 1,2, all)")
                )
                if not selected:
                    click.echo("Pominięto.")
                elif dry_run:
                    _show_dry_run_commands([["rm", "-rf", str(candidates[i]["path"])] for i in selected])
                elif not yes and not _confirm_remove():
                    click.echo("Anulowano.")
                else:
                    _remove_selected(candidates, selected)

    if clean_state_old:
        click.echo(
            click.style(
                f"\n[+] Przycinanie dziennych partycji stanu aplikacji (> {stale_days} dni)...",
                fg="cyan",
                bold=True,
            )
        )
        _cleanup_state_old(
            json_output=False,
            dry_run=dry_run,
            list_only=list_only,
            yes=yes,
            days=stale_days,
        )

    if clean_projects_old:
        click.echo(
            click.style(
                f"\n[+] Czyszczenie nieużywanych artefaktów projektów (> {stale_days} dni)...",
                fg="cyan",
                bold=True,
            )
        )
        _cleanup_projects_old(
            json_output=False,
            dry_run=dry_run,
            list_only=list_only,
            yes=yes,
            days=stale_days,
            base_dir=(home / "github") if home_dir is not None else None,
        )


# ── date-partitioned state stores ────────────────────────────────────────


def _cleanup_state_old(
    json_output: bool,
    dry_run: bool,
    list_only: bool,
    yes: bool,
    days: int = DEFAULT_STATE_OLD_DAYS,
    roots: list[Path] | None = None,
) -> None:
    """Remove YYYY/MM/DD partitions of application state stores older than `days`."""
    from fixos.diagnostics.state_retention import (
        remove_old_partitions,
        scan_state_retention,
    )

    try:
        stores = scan_state_retention(int(days), roots=roots)
    except ValueError as exc:
        click.echo(click.style(f"Błąd: {exc}", fg="red"))
        return
    candidates = [
        {
            "description": str(store.path),
            "path": store.path,
            "store": store,
            "size_bytes": store.reclaimable_bytes,
            "note": (
                f"{len(store.old_days)} dni {store.oldest}..{store.newest}, "
                f"zostaje {store.kept_days}"
                + (
                    f", pozorny rozmiar {_format_bytes(store.apparent_bytes)} (twarde dowiązania)"
                    if store.apparent_bytes != store.reclaimable_bytes
                    else ""
                )
            ),
        }
        for store in stores
    ]

    if json_output:
        _echo_json({
            "days": days,
            "candidates": [
                {
                    "path": str(c["path"]),
                    "partitions": len(c["store"].old_days),
                    "oldest": str(c["store"].oldest),
                    "newest": str(c["store"].newest),
                    "kept_partitions": c["store"].kept_days,
                    "apparent_bytes": c["store"].apparent_bytes,
                    "reclaimable_bytes": c["size_bytes"],
                }
                for c in candidates
            ],
            "total_bytes": sum(c["size_bytes"] for c in candidates),
        })
        return

    if not candidates:
        click.echo(
            click.style(
                f"Brak partycji dziennych YYYY/MM/DD starszych niż {days} dni.",
                fg="green",
            )
        )
        return

    _display_candidates(
        f"Magazyny stanu z partycjami dziennymi starszymi niż {days} dni:", candidates
    )
    if list_only:
        return

    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery magazynów do przycięcia (np. 1,2, all)")
    )
    if not selected:
        click.echo("Pominięto.")
        return

    if dry_run:
        _show_dry_run_commands(
            [
                ["rm", "-rf", str(p.path)]
                for i in selected
                for p in candidates[i]["store"].old_days
            ]
        )
        return

    if not yes and not _confirm_remove():
        click.echo("Anulowano.")
        return
    freed = 0
    for index in selected:
        store = candidates[index]["store"]
        removed, errors = remove_old_partitions(store)
        if removed == len(store.old_days):
            freed += store.reclaimable_bytes
        style = "green" if not errors else "yellow"
        click.echo(
            click.style(
                f"  {store.path}: usunięto {removed}/{len(store.old_days)} partycji",
                fg=style,
            )
        )
        for error in errors[:5]:
            click.echo(click.style(f"    {error}", fg="red"))
    click.echo(click.style(f"  Zwolniono około {_format_bytes(freed)}", fg="green"))


# ── unused developer project artifacts (> 7 days) ────────────────────────


def _project_source_has_recent_activity(
    project: Path,
    exclude: set[str],
    cutoff: float,
) -> bool:
    """Return True if any non-excluded file/dir in `project` has mtime >= cutoff."""
    import os

    for git_rel in (".git/index", ".git/HEAD", ".git/FETCH_HEAD"):
        try:
            if (project / git_rel).lstat().st_mtime >= cutoff:
                return True
        except OSError:
            pass

    stack = [project]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if entry.name in exclude or entry.name.endswith(".egg-info"):
                        continue
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:
                        return True
                    if st.st_mtime >= cutoff:
                        return True
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
        except OSError:
            return True
    return False


def _scan_unused_projects(
    days: int = PROJECT_SCAN_STALE_DAYS,
    base_dir: Path | str | None = None,
    *,
    now: float | None = None,
) -> list[dict]:
    """Scan developer projects under `base_dir` for safe regenerable artifacts unused for >= `days` days."""
    import os
    import time

    import psutil

    from fixos.diagnostics.project_scanner import (
        REMOVABLE_ARTIFACTS,
        _is_removable_artifact,
        discover_project_roots,
    )
    from fixos.diagnostics.venv_cleanup import (
        PROJECT_SOURCE_EXCLUDE,
        _plain_path,
        _within,
        active_paths,
    )

    if days < 1:
        raise ValueError("Okres nieaktywności projektów musi wynosić co najmniej 1 dzień")

    base = (
        Path(base_dir).expanduser().absolute()
        if base_dir is not None
        else Path(PROJECT_SCAN_DEFAULT_PATH).expanduser().absolute()
    )
    if not base.is_dir() or not _plain_path(base):
        return []

    now_ts = time.time() if now is None else float(now)
    cutoff = now_ts - float(days) * 86400.0
    paths, _ = active_paths()
    try:
        mounts = {Path(part.mountpoint) for part in psutil.disk_partitions(all=True)}
    except OSError:
        mounts = None
    if mounts is None:
        return []

    exclude_set = set(PROJECT_SOURCE_EXCLUDE)
    raw_items: list[dict] = []
    for project in discover_project_roots(base, max_depth=PROJECT_SCAN_MAX_DEPTH):
        if not _plain_path(project) or any(_within(p, project) for p in paths):
            continue
        try:
            entries = sorted(os.listdir(project))
        except OSError:
            continue
        project_artifacts: list[tuple[str, Path, str, str, float]] = []
        for name in entries:
            if not _is_removable_artifact(project, name):
                continue
            description, ecosystem, risk_level = REMOVABLE_ARTIFACTS[name]
            if risk_level != "safe":
                continue
            art_path = project / name
            if (
                not art_path.is_dir()
                or art_path.is_symlink()
                or not _plain_path(art_path)
                or any(_within(mount, art_path) for mount in mounts)
            ):
                continue
            try:
                st = art_path.lstat()
            except OSError:
                continue
            if st.st_mtime >= cutoff:
                continue
            project_artifacts.append((name, art_path, description, ecosystem, st.st_mtime))

        if not project_artifacts:
            continue
        if _project_source_has_recent_activity(project, exclude_set, cutoff):
            continue

        for name, art_path, description, ecosystem, art_mtime in project_artifacts:
            age_days = max(0.0, (now_ts - art_mtime) / 86400.0)
            try:
                rel = str(art_path.relative_to(base))
            except ValueError:
                rel = str(art_path)
            raw_items.append(
                {
                    "description": f"{rel} ({ecosystem})",
                    "path": art_path,
                    "project": project,
                    "artifact_name": name,
                    "ecosystem": ecosystem,
                    "age_days": round(age_days, 1),
                    "note": f"{description}, nieużywany {age_days:.0f} dni",
                }
            )

    if not raw_items:
        return []

    sizes = _dir_sizes([item["path"] for item in raw_items])
    candidates: list[dict] = []
    for item in raw_items:
        sz = sizes.get(str(item["path"]))
        if sz is None:
            sz = _dir_size(item["path"])
        if sz <= 0:
            continue
        item["size_bytes"] = sz
        candidates.append(item)

    candidates.sort(key=lambda item: (-item["size_bytes"], item["description"]))
    return candidates


def _cleanup_projects_old(
    json_output: bool,
    dry_run: bool,
    list_only: bool,
    yes: bool,
    days: int = PROJECT_SCAN_STALE_DAYS,
    base_dir: Path | str | None = None,
) -> None:
    """Remove safe regenerable artifacts in developer projects unused for >= `days` days."""
    from fixos.diagnostics.venv_cleanup import _plain_path, _within, active_paths

    try:
        candidates = _scan_unused_projects(days=int(days), base_dir=base_dir)
    except ValueError as exc:
        click.echo(click.style(f"Błąd: {exc}", fg="red"))
        return

    if json_output:
        _echo_json(
            {
                "days": int(days),
                "candidates": [
                    {
                        "description": c["description"],
                        "path": str(c["path"]),
                        "project": str(c["project"]),
                        "artifact_name": c["artifact_name"],
                        "ecosystem": c["ecosystem"],
                        "age_days": c["age_days"],
                        "size_bytes": c["size_bytes"],
                        "note": c["note"],
                    }
                    for c in candidates
                ],
                "total_bytes": sum(c["size_bytes"] for c in candidates),
            }
        )
        return

    if not candidates:
        click.echo(
            click.style(
                f"Brak nieużywanych artefaktów projektów starszych niż {int(days)} dni.",
                fg="green",
            )
        )
        return

    _display_candidates(
        f"Projekty nieużywane od > {int(days)} dni — bezpieczne artefakty do usunięcia:",
        candidates,
    )
    if list_only:
        return

    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery artefaktów do usunięcia (np. 1,2, all)")
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

    paths, _ = active_paths()
    safe_selected: list[int] = []
    for i in selected:
        item = candidates[i]
        art_path = item["path"]
        proj_path = item["project"]
        if (
            not _plain_path(art_path)
            or not art_path.is_dir()
            or any(_within(p, proj_path) for p in paths)
        ):
            click.echo(
                click.style(
                    f"  {item['description']}: pominięto (projekt aktywny lub zmieniona ścieżka)",
                    fg="yellow",
                )
            )
            continue
        safe_selected.append(i)

    if safe_selected:
        _remove_selected(candidates, safe_selected, path_key="path")

