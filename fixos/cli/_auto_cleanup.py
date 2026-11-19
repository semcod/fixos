"""Additional regenerable leaf caches; never scan personal directories."""

from __future__ import annotations

import os
import re
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
    ".cache/uv",
    ".cache/pip",
    ".cache/pre-commit",
    ".cache/yarn",
    ".cache/pnpm",
    ".cache/pypoetry/cache",
    ".cache/pypoetry/artifacts",
    ".cache/Google/Chrome/Default/Cache",
    ".cache/go-build",
    ".cache/ruff",
    ".cache/mypy",
    ".cache/Flake8",
    ".cache/black",
    ".cache/subactor-search",
    ".cache/virt-builder",
    ".cache/tree-sitter-language-pack",
)
_BROWSERS = ("google-chrome", "chromium", "BraveSoftware/Brave-Browser")
_BROWSER_LEAVES = ("Cache", "Code Cache", "GPUCache", "DawnCache", "ShaderCache")
_PROTECTED_DOCKER_TOKENS = frozenset(
    {
        "approved",
        "parent",
        "sandbox",
        "base",
        "latest",
        "stable",
        "release",
        "runtime",
        "pinned",
    }
)
_TOKEN_SPLIT_RE = re.compile(r"[/:\-_.]+")


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


def is_ephemeral_docker_image_tag(ref: str) -> bool:
    """Return True only for strictly disposable CI/qualification/cache image tags.

    Images carrying protected tokens (approved, parent, sandbox, base, latest,
    stable, release, runtime, pinned) or lacking a repo:tag separator are always
    rejected fail-closed.
    """
    if not ref or ":" not in ref or ref.startswith("<none>:"):
        return False
    repo, _, tag = ref.rpartition(":")
    if not repo or not tag or tag == "<none>":
        return False
    lower_ref = ref.lower()
    lower_repo = repo.lower()
    lower_tag = tag.lower()
    tokens = {tok for tok in _TOKEN_SPLIT_RE.split(lower_ref) if tok}
    if tokens & _PROTECTED_DOCKER_TOKENS:
        return False
    if "unpinned-counterexample" in lower_ref:
        return True
    if lower_repo == "onedev-progress-staged":
        return True
    if lower_repo.endswith("-qualification"):
        return True
    if lower_tag.startswith(("qualify-", "qualification-", "qualified-")):
        return True
    return bool(lower_repo.endswith("-cache") and lower_tag.startswith("continue-"))


def _collect_ephemeral_docker_candidates(timeout: int = 30) -> list[str]:
    """Identify 0-reference ephemeral Docker image tags fail-closed."""
    ps_res = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Image}}"],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if ps_res.returncode != 0:
        return []
    raw_refs = [line.strip() for line in (ps_res.stdout or "").splitlines() if line.strip()]
    used_names: set[str] = set()
    used_ids: set[str] = set()
    to_inspect: list[str] = []
    for ref in raw_refs:
        if ref.startswith("sha256:"):
            digest = ref.split(":", 1)[1]
            used_ids.add(ref)
            used_ids.add(digest)
            used_ids.add(digest[:12])
        else:
            used_names.add(ref)
            if ":" not in ref:
                used_names.add(f"{ref}:latest")
            if re.fullmatch(r"[0-9a-f]{12,64}", ref):
                used_ids.add(ref)
                used_ids.add(ref[:12])
            to_inspect.append(ref)
    if to_inspect:
        unique_refs = sorted(set(to_inspect))
        insp = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", *unique_refs],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if insp.returncode != 0:
            return []
        for line in (insp.stdout or "").splitlines():
            iid = line.strip()
            if not iid:
                continue
            used_ids.add(iid)
            bare = iid.split(":", 1)[1] if iid.startswith("sha256:") else iid
            used_ids.add(bare)
            used_ids.add(bare[:12])

    img_res = subprocess.run(
        [
            "docker",
            "images",
            "--no-trunc",
            "--format",
            "{{.ID}}\t{{.Repository}}:{{.Tag}}",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if img_res.returncode != 0:
        return []
    candidates: list[str] = []
    seen: set[str] = set()
    for line in (img_res.stdout or "").splitlines():
        if "\t" not in line:
            continue
        image_id, repo_tag = (part.strip() for part in line.split("\t", 1))
        bare_id = image_id.split(":", 1)[1] if image_id.startswith("sha256:") else image_id
        if (
            image_id in used_ids
            or bare_id in used_ids
            or bare_id[:12] in used_ids
            or repo_tag in used_names
        ):
            continue
        if repo_tag not in seen and is_ephemeral_docker_image_tag(repo_tag):
            seen.add(repo_tag)
            candidates.append(repo_tag)
    return candidates


def cleanup_ephemeral_docker_images(
    *, dry_run: bool, yes: bool, timeout: int = 30
) -> list[str]:
    """Remove unused, strictly ephemeral Docker image tags (never volumes or active images)."""
    import shlex

    if not shutil.which("docker") or dry_run:
        return []
    try:
        candidates = _collect_ephemeral_docker_candidates(timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if not candidates:
        return []
    if not yes and not click.confirm(
        f"Usunąć {len(candidates)} tymczasowych nieużywanych obrazów Dockera?"
    ):
        return []
    command = ["docker", "rmi", *candidates]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired):
        click.echo(
            f"Docker ephemeral images: pominięto (timeout lub błąd: {shlex.join(command[:3])})."
        )
        return []
    if result.returncode == 0:
        click.echo(
            f"Docker ephemeral images: usunięto {len(candidates)} nieużywanych obrazów tymczasowych."
        )
        return candidates
    return []


def cleanup_docker_builder(*, dry_run: bool, yes: bool) -> None:
    """Prune dangling Docker images, ephemeral 0-ref tags, and unused build cache."""
    import shlex

    if not shutil.which("docker"):
        return
    dangling_images_cmd = ["docker", "image", "prune", "--force"]
    dangling_builder_cmd = ["docker", "builder", "prune", "--force"]
    retained_builder_cmd = [
        "docker",
        "builder",
        "prune",
        "--all",
        "--force",
        "--filter",
        "until=168h",
    ]
    if dry_run:
        click.echo(f"[DRY-RUN] {shlex.join(dangling_images_cmd)}")
        click.echo(f"[DRY-RUN] {shlex.join(dangling_builder_cmd)}")
        click.echo(f"[DRY-RUN] {shlex.join(retained_builder_cmd)}")
        return
    if not yes and not click.confirm(
        "Usunąć osierocone obrazy Dockera oraz nieużywany cache budowania?"
    ):
        return
    try:
        img_res = subprocess.run(
            dangling_images_cmd, capture_output=True, text=True, check=False, timeout=30
        )
        if img_res.returncode == 0 and (img_res.stdout or "").strip():
            click.echo(img_res.stdout.strip().splitlines()[-1])
        cleanup_ephemeral_docker_images(dry_run=False, yes=True, timeout=30)
        subprocess.run(
            dangling_builder_cmd, capture_output=True, text=True, check=False, timeout=30
        )
        result = subprocess.run(
            retained_builder_cmd, capture_output=True, text=True, check=False, timeout=30
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
