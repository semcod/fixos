"""Reference-aware reclamation of content-addressed stores and build caches.

Content-addressed stores (``<root>/sha256/<digest>/<file>``) look disposable but
are frequently referenced *implicitly*: a manifest such as
``inputs/runtime/<sha>/guestfs.json`` embeds an absolute path to
``inputs/sha256/<digest>/builder-kernel`` without naming the digest inline.
Deleting such an entry silently breaks the build ("Guestfs kernel/modules
missing"), so every candidate is cross-referenced against surrounding manifests,
symlinks and the Git index before it can be offered for removal.

Private user data is never a candidate: protected home directories
(``Downloads``, ``Documents``, ``Pictures``, ``.ssh`` …) and credential stores
are excluded by name anywhere in the path, before any size is measured.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import Iterable, Sequence
from pathlib import Path

DIGEST_DIR = "sha256"
DIGEST_RE = re.compile(r"[a-f0-9]{64}")
DIGEST_IN_TEXT_RE = re.compile(r"sha256/([a-f0-9]{64})")
ABS_PATH_RE = re.compile(r"(?<![\w/])(/[^\s\"'`,;:)\]}]+)")

PROTECTED_HOME_DIRS = frozenset(
    {
        "downloads",
        "documents",
        "desktop",
        "pictures",
        "music",
        "videos",
        "public",
        "templates",
        "books",
        "mail",
        "maildir",
        "thunderbird",
        ".ssh",
        ".gnupg",
        ".password-store",
        ".mozilla",
        ".thunderbird",
        ".aws",
        ".kube",
        ".docker",
    }
)

MANIFEST_SUFFIXES = (
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
    ".lock",
    ".txt",
    ".md",
    ".py",
    ".sh",
    ".mjs",
    ".js",
    ".env",
)

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "venv",
        ".venv",
    }
)

BUILD_CACHE_DIRS = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "node_modules",
    "dist",
    "build",
)

MAX_MANIFEST_BYTES = 2 * 1024 * 1024


def is_protected_path(path: Path, *, home: Path | None = None) -> list[str]:
    """Return protection reasons for a path that must never be reclaimed."""

    reasons: list[str] = []
    home = home or Path.home()
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError):
        resolved = path
    try:
        relative = resolved.relative_to(home)
    except (ValueError, OSError):
        relative = None
    if relative is not None:
        for part in relative.parts:
            if part.lower() in PROTECTED_HOME_DIRS:
                reasons.append(f"private-home-data:{part}")
                break
    for part in (item.lower() for item in resolved.parts):
        if part in {".ssh", ".gnupg", ".password-store"}:
            reasons.append(f"credential-store:{part}")
            break
    if path.is_symlink():
        reasons.append("symlink")
    return reasons


def measure_tree(path: Path) -> int:
    """Measured on-disk size of a file or directory tree in bytes."""

    try:
        if path.is_symlink() or path.is_file():
            return path.lstat().st_size
        total = 0
        for entry in path.rglob("*"):
            try:
                if entry.is_file() and not entry.is_symlink():
                    total += entry.lstat().st_size
            except OSError:
                continue
        return total
    except OSError:
        return 0


def newest_mtime(path: Path) -> float:
    """Newest modification time anywhere in the tree."""

    try:
        newest = path.lstat().st_mtime
        if path.is_dir() and not path.is_symlink():
            for entry in path.rglob("*"):
                try:
                    newest = max(newest, entry.lstat().st_mtime)
                except OSError:
                    continue
        return newest
    except OSError:
        return 0.0


def git_tracked_paths(repo_root: Path) -> set[str]:
    """Tracked paths of a Git work tree, or an empty set when unavailable."""

    if shutil.which("git") is None:
        return set()
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z"],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0:
        return set()
    return {
        item.decode("utf-8", "surrogateescape")
        for item in proc.stdout.split(b"\0")
        if item
    }


def _manifest_texts(
    roots: Sequence[tuple[Path, int]], *, limit: int = 20000
) -> Iterable[tuple[Path, str]]:
    seen = 0
    for root, depth in roots:
        for current_path, filenames in _walk_bounded(root, depth):
            for name in filenames:
                if not name.lower().endswith(MANIFEST_SUFFIXES):
                    continue
                candidate = current_path / name
                try:
                    if candidate.is_symlink() or candidate.stat().st_size > MAX_MANIFEST_BYTES:
                        continue
                    text = candidate.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                seen += 1
                if seen > limit:
                    return
                yield candidate, text


def _walk_bounded(root: Path, depth: int) -> Iterable[tuple[Path, list[str]]]:
    """Walk ``root`` without following links, descending at most ``depth`` levels."""

    if not root.exists():
        return
    base = len(root.parts)
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        level = len(current_path.parts) - base
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        if level >= depth:
            dirnames[:] = []
        yield current_path, filenames


def _iter_symlinks(roots: Sequence[tuple[Path, int]], *, limit: int = 20000) -> Iterable[Path]:
    """Symlinks found under the given roots, without following links."""

    seen = 0
    for root, depth in roots:
        for current_path, filenames in _walk_bounded(root, depth):
            for name in filenames:
                candidate = current_path / name
                try:
                    if not candidate.is_symlink():
                        continue
                except OSError:
                    continue
                seen += 1
                if seen > limit:
                    return
                yield candidate


def collect_references(
    store_root: Path, scope_roots: Sequence[tuple[Path, int]]
) -> dict[str, set[str]]:
    """Map digest -> referencing evidence, including implicit absolute paths."""

    references: dict[str, set[str]] = {}
    digest_dir = (store_root / DIGEST_DIR).resolve()
    for path, text in _manifest_texts(scope_roots):
        for digest in DIGEST_IN_TEXT_RE.findall(text):
            references.setdefault(digest, set()).add(f"digest-in-text:{path}")
        for token in ABS_PATH_RE.findall(text):
            try:
                resolved = Path(token).resolve()
            except (OSError, RuntimeError):
                continue
            try:
                parts = resolved.relative_to(digest_dir).parts
            except ValueError:
                continue
            if parts and DIGEST_RE.fullmatch(parts[0]):
                references.setdefault(parts[0], set()).add(
                    f"absolute-path-in-text:{path}"
                )
    for link in _iter_symlinks([(store_root, 6), *scope_roots]):
        try:
            target = link.resolve()
        except (OSError, RuntimeError):
            continue
        try:
            parts = target.relative_to(digest_dir).parts
        except ValueError:
            continue
        if parts and DIGEST_RE.fullmatch(parts[0]):
            references.setdefault(parts[0], set()).add(f"symlink:{link}")
    return references


def scan_artifact_stores(
    roots: Sequence[Path | str],
    *,
    min_age_days: int = 1,
    receipt_dirs: Sequence[Path | str] = (),
    scope_roots: Sequence[Path | str] | None = None,
) -> dict:
    """Inventory content-addressed digests with safety verdicts."""

    if min_age_days < 0:
        raise ValueError("min_age_days must be >= 0")
    now = time.time()
    scope = [Path(root).expanduser().resolve() for root in roots]
    receipts = [Path(item).expanduser().resolve() for item in receipt_dirs]
    receipt_text: list[tuple[Path, str]] = []
    for receipt in receipts:
        try:
            if receipt.is_file():
                receipt_text.append((receipt, receipt.read_text(errors="ignore")))
            elif receipt.is_dir():
                for file in receipt.glob("*.json"):
                    receipt_text.append((file, file.read_text(errors="ignore")))
        except OSError:
            continue
    report: dict = {
        "roots": [str(item) for item in scope],
        "min_age_days": min_age_days,
        "found": 0,
        "eligible": 0,
        "bytes": 0,
        "total_bytes": 0,
        "items": [],
    }
    seen: set[Path] = set()
    manifest_scope = (
        [(Path(item).expanduser().resolve(), 4) for item in scope_roots]
        if scope_roots is not None
        else list(dict.fromkeys([*((item, 4) for item in scope), *((item.parent, 1) for item in scope)]))
    )
    for store_root in scope:
        digest_dir = store_root / DIGEST_DIR
        if not digest_dir.is_dir():
            continue
        references = collect_references(store_root, manifest_scope)
        tracked = git_tracked_paths(store_root)
        for entry in sorted(digest_dir.iterdir()):
            if not entry.is_dir() or not DIGEST_RE.fullmatch(entry.name):
                continue
            if entry in seen:
                continue
            seen.add(entry)
            reasons = is_protected_path(entry)
            evidence = sorted(references.get(entry.name, ()))
            if evidence:
                reasons.append(f"referenced:{evidence[0]}")
            if entry.relative_to(store_root).as_posix() in tracked:
                reasons.append("git-tracked")
            for receipt, text in receipt_text:
                if entry.name in text:
                    reasons.append(f"recorded-in-receipt:{receipt.name}")
                    break
            age_days = (now - newest_mtime(entry)) / 86400
            if age_days < min_age_days:
                reasons.append(f"too-recent:{age_days:.2f}d")
            size = measure_tree(entry)
            eligible = not reasons
            report["found"] += 1
            report["total_bytes"] += size
            if eligible:
                report["eligible"] += 1
                report["bytes"] += size
            report["items"].append(
                {
                    "path": str(entry),
                    "kind": "content-addressed",
                    "digest": entry.name,
                    "bytes": size,
                    "age_days": round(age_days, 2),
                    "references": evidence,
                    "eligible": eligible,
                    "reasons": reasons,
                }
            )
    return report


def scan_build_caches(
    roots: Sequence[Path | str],
    *,
    min_age_days: int = 7,
) -> dict:
    """Inventory disposable build caches (``__pycache__``, ``node_modules`` …)."""

    now = time.time()
    scope = [Path(root).expanduser().resolve() for root in roots]
    report: dict = {
        "roots": [str(item) for item in scope],
        "min_age_days": min_age_days,
        "found": 0,
        "eligible": 0,
        "bytes": 0,
        "total_bytes": 0,
        "items": [],
    }
    for root in scope:
        if not root.exists():
            continue
        tracked_cache: dict[Path, set[str]] = {}
        for current, dirnames, _ in os.walk(root, followlinks=False):
            current_path = Path(current)
            keep: list[str] = []
            for name in list(dirnames):
                candidate = current_path / name
                if name == ".git":
                    continue
                if name not in BUILD_CACHE_DIRS:
                    keep.append(name)
                    continue
                repo = current_path
                while repo != repo.parent and not (repo / ".git").exists():
                    repo = repo.parent
                if repo not in tracked_cache:
                    tracked_cache[repo] = git_tracked_paths(repo)
                reasons = is_protected_path(candidate)
                if repo in candidate.parents:
                    relative = candidate.relative_to(repo).as_posix()
                    if relative in tracked_cache[repo]:
                        reasons.append("git-tracked")
                age_days = (now - newest_mtime(candidate)) / 86400
                if age_days < min_age_days:
                    reasons.append(f"too-recent:{age_days:.2f}d")
                size = measure_tree(candidate)
                eligible = not reasons
                report["found"] += 1
                report["total_bytes"] += size
                if eligible:
                    report["eligible"] += 1
                    report["bytes"] += size
                report["items"].append(
                    {
                        "path": str(candidate),
                        "kind": "build-cache",
                        "bytes": size,
                        "age_days": round(age_days, 2),
                        "eligible": eligible,
                        "reasons": reasons,
                    }
                )
            dirnames[:] = keep
    return report


def remove_artifacts(
    items: Sequence[dict],
    *,
    receipt_dir: Path | str | None = None,
) -> dict:
    """Delete explicitly selected eligible items and write a receipt."""

    removed: list[dict] = []
    skipped: list[dict] = []
    for item in items:
        path = Path(item["path"]).expanduser()
        reasons = list(item.get("reasons") or ())
        if reasons or not item.get("eligible", False):
            skipped.append({"path": str(path), "reasons": reasons or ["not-eligible"]})
            continue
        if not path.exists() or path.is_symlink():
            skipped.append({"path": str(path), "reasons": ["missing-or-symlink"]})
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            skipped.append({"path": str(path), "reasons": [f"error:{exc}"]})
            continue
        removed.append({"path": str(path), "bytes": int(item.get("bytes") or 0)})
    receipt: dict = {
        "schema": "fixos.artifact-reclaim/v1",
        "removed": removed,
        "skipped": skipped,
        "freed_bytes": sum(entry["bytes"] for entry in removed),
    }
    if receipt_dir is not None:
        target_dir = Path(receipt_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        target = target_dir / f"artifact-reclaim-{stamp}.json"
        target.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
        receipt["receipt"] = str(target)
    return receipt


#: Known-safe reclaimable locations. ``pattern=None`` means "whole directory".
#: Every entry is allowlisted: nothing outside these roots can ever be removed by
#: the system-wide scan, so private user data stays untouched by construction.
SYSTEM_TARGETS: tuple[dict, ...] = (
    {
        "name": "apt-archives",
        "path": "/var/cache/apt/archives",
        "pattern": ".deb",
        "kind": "package-cache",
    },
    {"name": "crash-dumps", "path": "/var/crash", "pattern": None, "kind": "crash", "contents": True},
    {
        "name": "coredumps",
        "path": "/var/lib/systemd/coredump",
        "pattern": None,
        "kind": "crash",
        "contents": True,
    },
    {"name": "rotated-logs", "path": "/var/log", "pattern": "rotated", "kind": "logs"},
    {"name": "tmp", "path": "/tmp", "pattern": None, "kind": "tmp", "contents": True},
    {"name": "var-tmp", "path": "/var/tmp", "pattern": None, "kind": "tmp", "contents": True},
    {"name": "pip-cache", "path": "~/.cache/pip", "pattern": None, "kind": "user-cache"},
    {"name": "uv-cache", "path": "~/.cache/uv", "pattern": None, "kind": "user-cache"},
    {
        "name": "npm-cache",
        "path": "~/.npm/_cacache",
        "pattern": None,
        "kind": "user-cache",
    },
    {
        "name": "thumbnails",
        "path": "~/.cache/thumbnails",
        "pattern": None,
        "kind": "user-cache",
    },
    {
        "name": "trash",
        "path": "~/.local/share/Trash/files",
        "pattern": None,
        "kind": "user-cache",
    },
    {
        "name": "journal",
        "path": "/var/log/journal",
        "pattern": None,
        "kind": "logs",
    },
)

ROTATED_LOG_SUFFIXES = (".gz", ".xz", ".bz2", ".zst", ".old", ".1", ".2")


def _matches_pattern(path: Path, pattern: str | None) -> bool:
    if pattern is None:
        return True
    if pattern == "rotated":
        return path.is_file() and path.name.endswith(ROTATED_LOG_SUFFIXES)
    return path.name.endswith(pattern)


def scan_system_targets(
    *,
    min_age_days: int = 1,
    home: Path | None = None,
    overrides: dict[str, Path | str] | None = None,
    targets: Sequence[dict] | None = None,
) -> dict:
    """Inventory allowlisted system caches with per-entry safety verdicts.

    ``overrides`` maps a target name to an alternative path; it exists so tests
    and operators can point a target at a fixture without touching ``/var``.
    """

    if min_age_days < 0:
        raise ValueError("min_age_days must be >= 0")
    home = (home or Path.home()).expanduser()
    overrides = overrides or {}
    now = time.time()
    report: dict = {
        "min_age_days": min_age_days,
        "home": str(home),
        "found": 0,
        "eligible": 0,
        "bytes": 0,
        "total_bytes": 0,
        "items": [],
    }
    for target in targets or SYSTEM_TARGETS:
        raw = overrides.get(target["name"], target["path"])
        base = (
            Path(str(home) + str(raw)[1:])
            if str(raw).startswith("~")
            else Path(raw)
        )
        if not base.exists():
            continue
        pattern = target.get("pattern")
        contents_only = bool(target.get("contents"))
        entries = (
            sorted(base.glob("*"))
            if pattern is not None or contents_only
            else [base]
        )
        for entry in entries:
            if not _matches_pattern(entry, pattern):
                continue
            reasons = is_protected_path(entry, home=home)
            if os.path.ismount(entry):
                reasons.append("mount-point")
            if not str(entry).startswith(str(home)) and hasattr(os, "geteuid"):
                try:
                    if entry.lstat().st_uid != 0:
                        reasons.append("unexpected-owner")
                except OSError:
                    reasons.append("unreadable")
            age_days = max(0.0, (now - newest_mtime(entry)) / 86400)
            if age_days < min_age_days:
                reasons.append(f"too-recent:{age_days:.2f}d")
            size = measure_tree(entry)
            eligible = not reasons
            report["found"] += 1
            report["total_bytes"] += size
            if eligible:
                report["eligible"] += 1
                report["bytes"] += size
            report["items"].append(
                {
                    "path": str(entry),
                    "kind": target["kind"],
                    "target": target["name"],
                    "bytes": size,
                    "age_days": round(age_days, 2),
                    "eligible": eligible,
                    "reasons": reasons,
                }
            )
    return report




