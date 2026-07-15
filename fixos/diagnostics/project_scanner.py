"""
Developer Project Scanner for fixOS.

Recursively finds removable build/environment artifacts across a workspace
tree of developer projects (e.g. ``~/github/*/*``) — virtualenvs,
node_modules, compiler/lint caches, build output — and flags the ones that
haven't been touched in a long time. Distinct from ``service_scanner.py``,
which only looks at a fixed list of well-known global cache paths
(``~/.cache/...``); this walks an arbitrary workspace tree to find project
roots first, then inspects each one.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# A directory is a "project root" worth inspecting if it has one of these.
PROJECT_MARKERS: Tuple[str, ...] = (
    ".git",
    "pyproject.toml",
    "setup.py",
    "package.json",
    "Cargo.toml",
    "go.mod",
)

# artifact dir name -> (description, ecosystem, risk_level)
# risk_level is "safe" (rebuildable via install/build, fine to bulk-select)
# or "review" (might hold something you actually want, e.g. release output).
REMOVABLE_ARTIFACTS: Dict[str, Tuple[str, str, str]] = {
    "venv": ("Python virtualenv", "python", "safe"),
    ".venv": ("Python virtualenv", "python", "safe"),
    ".venv_test": ("Python test virtualenv", "python", "safe"),
    "virtualenv": ("Python virtualenv", "python", "safe"),
    "__pycache__": ("Python bytecode cache", "python", "safe"),
    ".pytest_cache": ("Pytest cache", "python", "safe"),
    ".mypy_cache": ("Mypy type-check cache", "python", "safe"),
    ".ruff_cache": ("Ruff lint cache", "python", "safe"),
    ".tox": ("Tox test environments", "python", "safe"),
    ".nox": ("Nox test environments", "python", "safe"),
    ".eggs": ("Python egg build cache", "python", "safe"),
    "node_modules": ("Node.js dependencies (npm/yarn/pnpm install)", "node", "safe"),
    ".next": ("Next.js build cache", "node", "safe"),
    ".nuxt": ("Nuxt build cache", "node", "safe"),
    ".turbo": ("Turborepo cache", "node", "safe"),
    ".parcel-cache": ("Parcel bundler cache", "node", "safe"),
    "target": ("Rust build artifacts (cargo build)", "rust", "safe"),
    "dist": ("Build output — may hold something you meant to publish", "generic", "review"),
    "build": ("Build output — may hold something you meant to publish", "generic", "review"),
}

# Names too generic/ambiguous to trust by name alone — verified by content
# before being reported (see _looks_like_venv).
_VENV_NAMES = frozenset({"venv", ".venv", ".venv_test", "virtualenv"})

# Some artifact names are common across ecosystems (target, dist, build) or
# only meaningful for a specific one (node_modules); only report them when
# the project actually has the matching ecosystem marker, to avoid false
# positives on a coincidentally-named directory.
_REQUIRES_PROJECT_MARKER: Dict[str, str] = {
    "target": "Cargo.toml",
    "node_modules": "package.json",
    ".next": "package.json",
    ".nuxt": "package.json",
    ".turbo": "package.json",
    ".parcel-cache": "package.json",
}

# Never descend into these while searching for project roots: they're huge
# dependency/artifact trees, and nested markers inside them (e.g. a
# package.json inside node_modules/some-lib) aren't standalone projects.
_PRUNE_DIR_NAMES = frozenset({".git"} | set(REMOVABLE_ARTIFACTS))


@dataclass
class ProjectArtifact:
    """A single removable artifact directory found inside a project."""

    project_name: str
    project_path: str
    artifact_name: str
    artifact_path: str
    size_mb: float
    size_gb: float
    description: str
    ecosystem: str
    risk_level: str
    days_since_modified: Optional[int]
    stale: bool
    cleanup_command: str


def _get_dir_size_mb(path: str) -> float:
    """Size of a directory in MB, via `du` (fast, sparse-file aware)."""
    try:
        result = subprocess.run(
            ["du", "-sk", "--", path],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            kb = int(result.stdout.strip().splitlines()[-1].split()[0])
            return kb / 1024
    except (OSError, ValueError, subprocess.TimeoutExpired, IndexError):
        pass
    return 0.0


def _days_since_modified(path: str) -> Optional[int]:
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    return int((datetime.now(timezone.utc).timestamp() - mtime) // 86400)


def _looks_like_venv(path: Path) -> bool:
    """Confirm a venv-ish-named directory is actually a virtualenv (has a
    pyvenv.cfg) rather than some unrelated directory that just happens to be
    named 'venv'."""
    return (path / "pyvenv.cfg").exists()


def _is_removable_artifact(project_root: Path, name: str) -> bool:
    if name not in REMOVABLE_ARTIFACTS:
        return False
    if name in _VENV_NAMES and not _looks_like_venv(project_root / name):
        return False
    required_marker = _REQUIRES_PROJECT_MARKER.get(name)
    if required_marker and not (project_root / required_marker).exists():
        return False
    return True


def discover_project_roots(base: Path, max_depth: int = 4) -> List[Path]:
    """Find developer project roots under `base` (dirs carrying a known
    marker like .git/pyproject.toml/package.json), without descending into
    dependency trees, artifact directories, or nested projects.
    """
    base = base.expanduser()
    if not base.is_dir():
        return []

    roots: List[Path] = []
    base_depth = len(base.parts)

    for dirpath, dirnames, _filenames in os.walk(base):
        current = Path(dirpath)
        depth = len(current.parts) - base_depth
        if depth > max_depth:
            dirnames[:] = []
            continue

        if any((current / marker).exists() for marker in PROJECT_MARKERS):
            roots.append(current)
            dirnames[:] = []  # don't look for nested "sub-projects" inside one
            continue

        dirnames[:] = [
            d for d in dirnames if d not in _PRUNE_DIR_NAMES and not d.startswith(".")
        ]

    return roots


def scan_project_artifacts(
    project_root: Path,
    threshold_mb: float = 50,
    stale_days: int = 60,
) -> List[ProjectArtifact]:
    """Find removable artifacts directly under a single project root."""
    artifacts: List[ProjectArtifact] = []
    try:
        entries = os.listdir(project_root)
    except OSError:
        return artifacts

    for entry in entries:
        if not _is_removable_artifact(project_root, entry):
            continue

        artifact_path = project_root / entry
        if not artifact_path.is_dir():
            continue

        size_mb = _get_dir_size_mb(str(artifact_path))
        if size_mb < threshold_mb:
            continue

        description, ecosystem, risk_level = REMOVABLE_ARTIFACTS[entry]
        days = _days_since_modified(str(artifact_path))

        artifacts.append(
            ProjectArtifact(
                project_name=project_root.name,
                project_path=str(project_root),
                artifact_name=entry,
                artifact_path=str(artifact_path),
                size_mb=round(size_mb, 2),
                size_gb=round(size_mb / 1024, 3),
                description=description,
                ecosystem=ecosystem,
                risk_level=risk_level,
                days_since_modified=days,
                stale=days is not None and days >= stale_days,
                cleanup_command=f"rm -rf {shlex.quote(str(artifact_path))}",
            )
        )

    return artifacts


def scan_all(
    base: Path,
    threshold_mb: float = 50,
    stale_days: int = 60,
    max_depth: int = 4,
) -> List[ProjectArtifact]:
    """Scan every project under `base` for removable artifacts, largest first."""
    results: List[ProjectArtifact] = []
    for project_root in discover_project_roots(base, max_depth=max_depth):
        results.extend(scan_project_artifacts(project_root, threshold_mb, stale_days))
    results.sort(key=lambda a: a.size_mb, reverse=True)
    return results


def find_duplicate_venvs(artifacts: List[ProjectArtifact]) -> List[str]:
    """Project paths that carry more than one virtualenv-type artifact at
    once (e.g. both 'venv' and '.venv') — redundant, safe to consolidate."""
    by_project: Dict[str, List[str]] = {}
    for a in artifacts:
        if a.artifact_name in _VENV_NAMES:
            by_project.setdefault(a.project_path, []).append(a.artifact_name)
    return [path for path, names in by_project.items() if len(names) > 1]


def summarize(artifacts: List[ProjectArtifact]) -> dict:
    """Aggregate stats used for the CLI summary header."""
    total_mb = sum(a.size_mb for a in artifacts)
    stale_mb = sum(a.size_mb for a in artifacts if a.stale)
    safe_mb = sum(a.size_mb for a in artifacts if a.risk_level == "safe")
    review_mb = sum(a.size_mb for a in artifacts if a.risk_level == "review")
    return {
        "total_gb": round(total_mb / 1024, 2),
        "stale_gb": round(stale_mb / 1024, 2),
        "safe_gb": round(safe_mb / 1024, 2),
        "review_gb": round(review_mb / 1024, 2),
        "projects_count": len({a.project_path for a in artifacts}),
        "duplicate_venv_projects": find_duplicate_venvs(artifacts),
    }
