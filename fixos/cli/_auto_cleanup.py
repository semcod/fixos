"""Additional regenerable leaf caches; never scan personal directories."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import click

# Keep installations, local repositories, model weights and application state out.
_CACHE_PATHS = (
    ".npm/_npx",
    ".npm/_logs",
    ".ccache",
    ".nv/ComputeCache",
    ".cargo/registry/cache",
    ".cache/pypoetry/cache",
    ".cache/pypoetry/artifacts",
    ".cache/Google/Chrome/Default/Cache",
)
_BROWSERS = ("google-chrome", "chromium", "BraveSoftware/Brave-Browser")
_BROWSER_LEAVES = ("Cache", "Code Cache", "GPUCache", "DawnCache", "ShaderCache")


def cache_path_allowed(home: Path, path: Path) -> bool:
    """Reject symlinked ancestors, nested mounts and paths outside this home.

    Symlinks *inside* a cache are unlinked by rmtree, never followed. A mount
    inside a cache must instead protect the entire candidate.
    """
    try:
        relative = path.relative_to(home)
        current = home
        for part in relative.parts:
            current = current / part
            if current.is_symlink() or current.is_mount():
                return False
        if not path.is_dir():
            return False
        device = path.stat().st_dev
        for parent, dirs, _ in os.walk(
            path, followlinks=False, onerror=_raise_os_error
        ):
            for name in dirs:
                child = Path(parent) / name
                if not child.is_symlink() and (
                    child.is_mount() or child.stat().st_dev != device
                ):
                    return False
        return True
    except (OSError, ValueError):
        return False


def _raise_os_error(error: OSError) -> None:
    raise error


def additional_cache_candidates(home: Path | None = None) -> list[dict]:
    from fixos.cli._cleanup_space import _dir_sizes

    home = home or Path.home()
    paths = [home / relative for relative in _CACHE_PATHS]
    for browser in _BROWSERS:
        root = home / ".cache" / browser
        # Only cache roots, never ~/.config or browser profile databases.
        if root.is_symlink():
            continue
        try:
            profiles = [
                p
                for p in root.iterdir()
                if p.name == "Default" or p.name.startswith("Profile ")
            ]
        except OSError:
            profiles = []
        for profile in [root, *profiles]:
            paths.extend(profile / leaf for leaf in _BROWSER_LEAVES)
    paths = sorted({p for p in paths if cache_path_allowed(home, p)})
    sizes = _dir_sizes(paths)
    return [
        {
            "path": p,
            "description": f"~/{p.relative_to(home)}",
            "size_bytes": sizes.get(str(p), 0),
            "note": "regenerowalny cache",
        }
        for p in paths
        if sizes.get(str(p), 0) > 0
    ]


def cleanup_additional_caches(*, dry_run: bool, yes: bool) -> None:
    from fixos.cli._cleanup_space import (
        _choose,
        _confirm_remove,
        _display_candidates,
        _show_dry_run_commands,
    )

    home = Path.home()
    candidates = additional_cache_candidates(home)
    if not candidates:
        return
    _display_candidates("DODATKOWE CACHE (bez danych użytkownika):", candidates)
    selected = (
        list(range(len(candidates)))
        if yes
        else _choose(candidates, "Numery cache do usunięcia")
    )
    if dry_run:
        _show_dry_run_commands(
            [["rm", "-rf", str(candidates[i]["path"])] for i in selected]
        )
        return
    if not selected or (not yes and not _confirm_remove()):
        return
    for index in selected:
        path = candidates[index]["path"]
        # Revalidate immediately before deletion, including all ancestors.
        if not cache_path_allowed(home, path):
            click.echo(f"  {path}: pominięto (zmiana ścieżki lub punkt montowania)")
            continue
        try:
            shutil.rmtree(path)
            click.echo(f"  {path}: usunięto")
        except OSError as error:
            click.echo(f"  {path}: pominięto ({error})")


def cleanup_docker_builder(*, dry_run: bool, yes: bool) -> None:
    """Prune only unused build cache older than seven days, with a hard timeout."""
    import shlex

    if not shutil.which("docker"):
        return
    command = [
        "docker",
        "builder",
        "prune",
        "--all",
        "--force",
        "--filter",
        "until=168h",
    ]
    if dry_run:
        click.echo(f"[DRY-RUN] {shlex.join(command)}")
        return
    if not yes and not click.confirm(
        "Usunąć nieużywany cache budowania Dockera starszy niż 7 dni?"
    ):
        return
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        click.echo(
            "Docker build cache: pominięto (niedostępny daemon lub timeout 30 s)."
        )
        return
    if result.returncode:
        click.echo("Docker build cache: pominięto (daemon odmówił wykonania).")
    else:
        click.echo(result.stdout.strip() or "Docker build cache: zakończono.")
