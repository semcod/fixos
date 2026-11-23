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

import json
import os
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

VERDICT_ALLOW = "ALLOW"
VERDICT_HOLD_PROTECTED = "HOLD_PROTECTED"

VETO_ACTIVE_PROCESS = "VETO_ACTIVE_PROCESS"
VETO_ACTIVE_LEASE = "VETO_ACTIVE_LEASE"
VETO_OPEN_PR_OR_UNMERGED = "VETO_OPEN_PR_OR_UNMERGED"
VETO_DIRTY_OR_STASH = "VETO_DIRTY_OR_STASH"
VETO_UNPUSHED_REFS = "VETO_UNPUSHED_REFS"
VETO_WORKTREE_OR_IDE_OWNERSHIP = "VETO_WORKTREE_OR_IDE_OWNERSHIP"

ACTIVE_LEASE_PHASES: frozenset[str] = frozenset(
    {"claimed", "editing", "validating", "publication_frozen"}
)
_DEFAULT_BRANCH_REFS: tuple[str, ...] = (
    "origin/main",
    "origin/master",
    "main",
    "master",
)
_IDE_OWNERSHIP_MARKERS: tuple[str, ...] = (
    ".idea/.lock",
    ".idea/workspace.xml",
    ".vscode/.lock",
)

# A directory is a "project root" worth inspecting if it has one of these.
PROJECT_MARKERS: tuple[str, ...] = (
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
REMOVABLE_ARTIFACTS: dict[str, tuple[str, str, str]] = {
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
    "dist": (
        "Build output — may hold something you meant to publish",
        "generic",
        "review",
    ),
    "build": (
        "Build output — may hold something you meant to publish",
        "generic",
        "review",
    ),
}

# Names too generic/ambiguous to trust by name alone — verified by content
# before being reported (see _looks_like_venv).
_VENV_NAMES = frozenset({"venv", ".venv", ".venv_test", "virtualenv"})

# Some artifact names are common across ecosystems (target, dist, build) or
# only meaningful for a specific one (node_modules); only report them when
# the project actually has the matching ecosystem marker, to avoid false
# positives on a coincidentally-named directory.
_REQUIRES_PROJECT_MARKER: dict[str, str] = {
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


@dataclass(frozen=True)
class CleanupVetoReport:
    """Result of evaluating the 6 canonical wellmanifest/git-lifecycle hard vetos."""

    target: str
    verdict: str
    veto_codes: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    @property
    def protected(self) -> bool:
        return self.verdict == VERDICT_HOLD_PROTECTED


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
    days_since_modified: int | None
    stale: bool
    cleanup_command: str
    project_has_recent_activity: bool = False
    verdict: str = VERDICT_ALLOW
    veto_codes: tuple[str, ...] = ()


def _get_dir_size_mb(path: str) -> float:
    """Size of a directory in MB, via native Rust scan with du fallback."""
    p = Path(path)
    if not p.is_dir():
        return 0.0

    try:
        from fixos.diagnostics.native_scan import measure_tree

        m = measure_tree(p, native=True)
        if isinstance(m, dict) and "bytes" in m and m["bytes"] > 0:
            return m["bytes"] / (1024 * 1024)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        pass

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


def _days_since_modified(path: str) -> int | None:
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
    return not (required_marker and not (project_root / required_marker).exists())


def discover_project_roots(
    base: Path, max_depth: int = 4, *, errors: list[str] | None = None
) -> list[Path]:
    """Find developer project roots under `base` (dirs carrying a known
    marker like .git/pyproject.toml/package.json), without descending into
    dependency trees, artifact directories, or nested projects.
    """
    base = base.expanduser()
    if not base.is_dir():
        return []

    from fixos.diagnostics.native_scan import discover_native

    accelerated = discover_native(base, max_depth, PROJECT_MARKERS, _PRUNE_DIR_NAMES)
    if accelerated is not None:
        return accelerated

    def onerror(exc):
        if errors is not None:
            errors.append(str(exc))

    roots: list[Path] = []
    base_depth = len(base.parts)

    for dirpath, dirnames, _filenames in os.walk(base, onerror=onerror):
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
            d
            for d in dirnames
            if d not in _PRUNE_DIR_NAMES
            and not d.startswith(".")
            and not (current / d).is_symlink()
        ]

    return roots


_PROJECT_SOURCE_EXCLUDE: set[str] = set(REMOVABLE_ARTIFACTS) | set(_PRUNE_DIR_NAMES) | {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "CLAUDE.md",
    "GEMINI.md",
    "AGENTS.md",
}


def _project_source_has_recent_activity(
    project: Path,
    exclude: set[str] | None = None,
    cutoff: float | None = None,
    max_depth: int = 4,
    max_files: int = 500,
) -> bool:
    """Return True if any non-excluded file in `project` has mtime >= cutoff."""
    if cutoff is None:
        return False

    exclude_set = _PROJECT_SOURCE_EXCLUDE if exclude is None else exclude

    for git_rel in (".git/index", ".git/HEAD", ".git/FETCH_HEAD"):
        try:
            if (project / git_rel).lstat().st_mtime >= cutoff:
                return True
        except OSError:
            pass

    stack: list[tuple[Path, int]] = [(project, 0)]
    files_checked = 0

    while stack and files_checked < max_files:
        current, depth = stack.pop()
        try:
            with os.scandir(current) as scandir_entries:
                for entry in scandir_entries:
                    if entry.name in exclude_set or entry.name.endswith(".egg-info"):
                        continue
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        if depth < max_depth:
                            stack.append((Path(entry.path), depth + 1))
                    else:
                        files_checked += 1
                        if st.st_mtime >= cutoff:
                            return True
        except OSError:
            continue
    return False


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _is_real_git_worktree(target: Path) -> bool:
    proc = _run_git(target, "rev-parse", "--is-inside-work-tree")
    return proc is not None and proc.returncode == 0 and proc.stdout.strip() == "true"


def _path_is_within(candidate: str, root: str) -> bool:
    return candidate == root or candidate.startswith(root + os.sep)


def _check_active_process_veto(target: Path, *, check_lsof: bool = False) -> str | None:
    """Hard veto 1: active process has cwd or open fd inside target."""
    try:
        resolved = str(target.resolve())
    except OSError:
        resolved = str(target)

    skip_pids = {str(os.getpid()), str(os.getppid())}
    proc_root = Path("/proc")
    if proc_root.is_dir():
        try:
            proc_entries = os.listdir(proc_root)
        except OSError:
            proc_entries = []
        for pid in proc_entries:
            if not pid.isdigit() or pid in skip_pids:
                continue
            pid_dir = proc_root / pid
            try:
                cwd = os.readlink(pid_dir / "cwd")
                if _path_is_within(cwd, resolved):
                    return f"Active process PID {pid} has cwd inside {resolved}"
            except OSError:
                pass
            fd_dir = pid_dir / "fd"
            try:
                fds = os.listdir(fd_dir)
            except OSError:
                continue
            for fd in fds:
                try:
                    link = os.readlink(fd_dir / fd)
                except OSError:
                    continue
                if _path_is_within(link, resolved):
                    return f"Active process PID {pid} holds open fd inside {resolved}"

    if check_lsof:
        try:
            proc = subprocess.run(
                ["lsof", "+D", resolved],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.stdout.strip():
                return f"lsof reports open file handles under {resolved}"
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def _lease_dirs_for_target(target: Path, repo_root: Path | None) -> list[Path]:
    candidates: list[Path] = []
    for base in (repo_root, target):
        if base is not None:
            ld = base / ".subactor" / "leases"
            if ld.is_dir() and ld not in candidates:
                candidates.append(ld)
    if target.parent.name == ".worktrees":
        primary_ld = target.parent.parent / ".subactor" / "leases"
        if primary_ld.is_dir() and primary_ld not in candidates:
            candidates.append(primary_ld)
    return candidates


def _check_active_lease_veto(
    target: Path, *, repo_root: Path | None = None
) -> str | None:
    """Hard veto 2: active or unreadable/foreign lease in .subactor/leases/*.json."""
    wt_name = target.name if target.parent.name == ".worktrees" else None
    for lease_dir in _lease_dirs_for_target(target, repo_root):
        try:
            lease_files = sorted(lease_dir.glob("*.json"))
        except OSError:
            continue
        for lf in lease_files:
            if lf.is_symlink():
                return f"Symlinked lease file {lf.name} requires HOLD_PROTECTED"
            if wt_name is not None and lf.stem != wt_name:
                continue
            try:
                data = json.loads(lf.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return f"Unreadable/foreign lease file {lf.name}"
            if not isinstance(data, dict):
                return f"Malformed lease file {lf.name}"
            phase = data.get("phase")
            if phase in ACTIVE_LEASE_PHASES:
                owner = data.get("ownerActor") or data.get("owner") or "unknown"
                return f"Active lease {lf.name} (phase={phase}, owner={owner})"
    return None


def _check_open_pr_or_unmerged_veto(
    target: Path,
    *,
    repo_root: Path | None = None,
    is_git: bool = False,
    open_pr_checker: Callable[[Path], bool] | None = None,
) -> str | None:
    """Hard veto 3: open PRs or unmerged commits against default branch."""
    if open_pr_checker is not None:
        try:
            if open_pr_checker(target):
                return "Target branch has an open pull request"
        except Exception:
            return "Open PR check failed (fail-closed HOLD_PROTECTED)"

    for lease_dir in _lease_dirs_for_target(target, repo_root):
        try:
            lease_files = sorted(lease_dir.glob("*.json"))
        except OSError:
            continue
        for lf in lease_files:
            try:
                data = json.loads(lf.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            pr = data.get("pullRequest")
            if isinstance(pr, dict):
                pr_state = str(pr.get("state", "open")).lower()
                if pr_state not in {"merged", "closed"}:
                    return f"Open PR recorded in lease {lf.name}"
            elif isinstance(pr, (int, str)) and pr:
                return f"PR reference recorded in lease {lf.name}"

    if is_git:
        default_ref = None
        for ref in _DEFAULT_BRANCH_REFS:
            chk = _run_git(target, "rev-parse", "--verify", "--quiet", ref)
            if chk is not None and chk.returncode == 0:
                default_ref = ref
                break
        if default_ref is not None:
            cnt = _run_git(target, "rev-list", "--count", f"{default_ref}..HEAD")
            if cnt is not None and cnt.returncode == 0:
                try:
                    ahead = int(cnt.stdout.strip() or "0")
                except ValueError:
                    ahead = 0
                if ahead > 0:
                    return f"Branch has {ahead} unmerged commit(s) ahead of {default_ref}"
    return None


def _check_dirty_or_stash_veto(target: Path, *, is_git: bool = False) -> str | None:
    """Hard veto 4: dirty working tree or stashes."""
    if not is_git:
        return None
    status = _run_git(target, "status", "--porcelain")
    if status is not None and status.returncode == 0 and status.stdout.strip():
        return "Dirty working tree (uncommitted changes or untracked files)"
    stash = _run_git(target, "stash", "list")
    if stash is not None and stash.returncode == 0 and stash.stdout.strip():
        return "Repository has unapplied Git stashes"
    return None


def _check_unpushed_refs_veto(target: Path, *, is_git: bool = False) -> str | None:
    """Hard veto 5: unpushed refs or branches ahead of upstream."""
    if not is_git:
        return None
    ahead_proc = _run_git(target, "rev-list", "--count", "@{u}..HEAD")
    if ahead_proc is not None and ahead_proc.returncode == 0:
        try:
            ahead = int(ahead_proc.stdout.strip() or "0")
        except ValueError:
            ahead = 0
        if ahead > 0:
            return f"Branch has {ahead} unpushed commit(s) ahead of upstream"
        return None

    remotes = _run_git(target, "remote")
    if remotes is not None and remotes.returncode == 0 and remotes.stdout.strip():
        head_cnt = _run_git(target, "rev-list", "--count", "HEAD")
        if head_cnt is not None and head_cnt.returncode == 0:
            try:
                commits = int(head_cnt.stdout.strip() or "0")
            except ValueError:
                commits = 0
            if commits > 0:
                return "Branch has commits with no configured upstream tracking ref"
    return None


def _check_worktree_or_ide_veto(
    target: Path, *, is_git: bool = False, is_directory_cleanup: bool = False
) -> str | None:
    """Hard veto 6: active linked worktree, primary checkout, or IDE ownership."""
    for marker in _IDE_OWNERSHIP_MARKERS:
        if (target / marker).exists():
            return f"IDE ownership marker present ({marker})"

    git_entry = target / ".git"
    if git_entry.is_file():
        return "Target is an active linked Git worktree"

    if is_git:
        wt_list = _run_git(target, "worktree", "list", "--porcelain")
        if wt_list is not None and wt_list.returncode == 0:
            wt_count = sum(
                1 for line in wt_list.stdout.splitlines() if line.startswith("worktree ")
            )
            if wt_count > 1:
                return f"Primary checkout owns {wt_count - 1} active linked worktree(s)"
        if is_directory_cleanup and git_entry.is_dir():
            return "Target is a primary Git checkout"
    return None


def evaluate_cleanup_vetos(
    target: Path,
    *,
    repo_root: Path | None = None,
    is_directory_cleanup: bool = False,
    check_lsof: bool = False,
    open_pr_checker: Callable[[Path], bool] | None = None,
) -> CleanupVetoReport:
    """Evaluate all 6 canonical wellmanifest/git-lifecycle hard vetos for ``target``.

    Any triggered veto forces ``HOLD_PROTECTED`` so callers never propose unsafe
    directory or worktree deletion.
    """
    is_git = _is_real_git_worktree(target)
    checks: tuple[tuple[str, str | None], ...] = (
        (VETO_ACTIVE_PROCESS, _check_active_process_veto(target, check_lsof=check_lsof)),
        (VETO_ACTIVE_LEASE, _check_active_lease_veto(target, repo_root=repo_root)),
        (
            VETO_OPEN_PR_OR_UNMERGED,
            _check_open_pr_or_unmerged_veto(
                target,
                repo_root=repo_root,
                is_git=is_git,
                open_pr_checker=open_pr_checker,
            ),
        ),
        (VETO_DIRTY_OR_STASH, _check_dirty_or_stash_veto(target, is_git=is_git)),
        (VETO_UNPUSHED_REFS, _check_unpushed_refs_veto(target, is_git=is_git)),
        (
            VETO_WORKTREE_OR_IDE_OWNERSHIP,
            _check_worktree_or_ide_veto(
                target, is_git=is_git, is_directory_cleanup=is_directory_cleanup
            ),
        ),
    )

    codes: list[str] = []
    reasons: list[str] = []
    for code, reason in checks:
        if reason is not None:
            codes.append(code)
            reasons.append(reason)

    verdict = VERDICT_HOLD_PROTECTED if codes else VERDICT_ALLOW
    return CleanupVetoReport(
        target=str(target),
        verdict=verdict,
        veto_codes=tuple(codes),
        reasons=tuple(reasons),
    )


def scan_project_artifacts(
    project_root: Path,
    threshold_mb: float = 50,
    stale_days: int = 7,
    *,
    enforce_vetos: bool = True,
    include_protected: bool = False,
    open_pr_checker: Callable[[Path], bool] | None = None,
) -> list[ProjectArtifact]:
    """Find removable artifacts directly under a single project root."""
    veto_report: CleanupVetoReport | None = None
    if enforce_vetos:
        veto_report = evaluate_cleanup_vetos(
            project_root, open_pr_checker=open_pr_checker
        )
        if veto_report.protected and not include_protected:
            return []

    artifacts: list[ProjectArtifact] = []
    try:
        entries = os.listdir(project_root)
    except OSError:
        return artifacts

    has_recent_activity: bool | None = None

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

        if days is not None and days >= stale_days:
            if has_recent_activity is None:
                now_ts = datetime.now(timezone.utc).timestamp()
                cutoff = now_ts - float(stale_days) * 86400.0
                has_recent_activity = _project_source_has_recent_activity(
                    project_root, cutoff=cutoff
                )
            is_stale = not has_recent_activity
        else:
            is_stale = False

        if veto_report is not None and veto_report.protected:
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
                    risk_level="protected",
                    days_since_modified=days,
                    stale=False,
                    cleanup_command="",
                    project_has_recent_activity=bool(has_recent_activity),
                    verdict=VERDICT_HOLD_PROTECTED,
                    veto_codes=veto_report.veto_codes,
                )
            )
            continue

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
                stale=is_stale,
                cleanup_command=f"rm -rf {shlex.quote(str(artifact_path))}",
                project_has_recent_activity=bool(has_recent_activity),
            )
        )

    return artifacts


def scan_all(
    base: Path,
    threshold_mb: float = 50,
    stale_days: int = 7,
    max_depth: int = 4,
) -> list[ProjectArtifact]:
    """Scan every project under `base` for removable artifacts, largest first."""
    results: list[ProjectArtifact] = []
    for project_root in discover_project_roots(base, max_depth=max_depth):
        results.extend(scan_project_artifacts(project_root, threshold_mb, stale_days))
    results.sort(key=lambda a: a.size_mb, reverse=True)
    return results


def find_duplicate_venvs(artifacts: list[ProjectArtifact]) -> list[str]:
    """Project paths that carry more than one virtualenv-type artifact at
    once (e.g. both 'venv' and '.venv') — redundant, safe to consolidate."""
    by_project: dict[str, list[str]] = {}
    for a in artifacts:
        if a.artifact_name in _VENV_NAMES:
            by_project.setdefault(a.project_path, []).append(a.artifact_name)
    return [path for path, names in by_project.items() if len(names) > 1]


def summarize(artifacts: list[ProjectArtifact]) -> dict:
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
