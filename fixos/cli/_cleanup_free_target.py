"""Target-driven cleanup ladder: reclaim disk until a free-space goal is met.

The NoLimits LIM-STORAGE-001 runbook wants "cleanup until N GB free".
``--threshold-gb`` cannot express that (it filters which *services* are
reported), so this module provides the goal-oriented pieces:

- :func:`free_bytes` — statvfs-based free space of a filesystem.
- :func:`find_stale_release_caches` — agent/release cache directories under
  ``~/.local/share/*/releases|release|snapshots`` untouched for a minimum
  number of days. Read-only (protected) trees are reported separately so the
  caller never tries to delete them.
- :func:`remove_release_caches` — best-effort removal that skips protected
  paths and returns the bytes actually reclaimed.
- :func:`docker_call` — batched ``docker`` subprocess with a hard timeout so a
  busy daemon skips a tier instead of hanging the whole command.
- :func:`run_free_target_ladder` — generic runner that measures free space
  before and after each tier and stops as soon as the goal is reached.

Nothing here deletes user documents, models, editor data, Docker volumes, or
anything that needs elevated privileges.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_FREE_TARGET_GB = 10.0
DEFAULT_RELEASE_CACHE_MIN_DAYS = 7.0
DEFAULT_DOCKER_IMAGE_MIN_DAYS = 14.0
DOCKER_CALL_TIMEOUT_SECONDS = 30
_RELEASE_PARENT_NAMES = frozenset({"releases", "release", "snapshots"})


@dataclass
class TierResult:
    """Outcome of one ladder tier."""

    name: str
    attempted: bool = True
    skipped_reason: str | None = None
    bytes_freed: int = 0
    note: str = ""


@dataclass
class LadderReport:
    """Aggregated ladder outcome."""

    goal_bytes: int
    started_free_bytes: int
    ended_free_bytes: int = 0
    tiers: list[TierResult] = field(default_factory=list)

    @property
    def goal_reached(self) -> bool:
        return self.ended_free_bytes >= self.goal_bytes


def free_bytes(path: str | Path = "/") -> int:
    """Return free bytes on the filesystem containing ``path`` (0 on error)."""
    try:
        stat = os.statvfs(str(path))
    except OSError:
        return 0
    return stat.f_bavail * stat.f_frsize


def _dir_size(path: Path) -> int:
    """Best-effort recursive size (0 on error, like du with ignored errors)."""
    total = 0
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        total += _dir_size(Path(entry.path))
                    else:
                        total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    continue
        return total
    except OSError:
        return total


def _write_allowed(path: Path) -> bool:
    """True when a deployment has not cleared the owner-write bit.

    ``os.access(W_OK)`` alone is useless under root (root can write
    everywhere), and exactly the protected deployment trees are marked by
    clearing the write bits.
    """
    try:
        stat = path.stat(follow_symlinks=False)
    except OSError:
        return False
    if not stat.st_mode & 0o200:
        return False
    return os.access(path, os.W_OK)


def find_stale_release_caches(
    share_root: Path | str | None = None,
    min_days: float = DEFAULT_RELEASE_CACHE_MIN_DAYS,
    *,
    now: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return ``(removable, protected)`` stale release-cache entries.

    An entry is a directory directly below
    ``<share_root>/<owner>/releases|release|snapshots/`` whose own mtime is
    older than ``min_days`` days. Protection is detected from the write bits:
    entries inside a read-only (deployment-protected) parent are returned as
    ``protected`` and never selected for removal — also when running as root,
    where ``os.access`` alone would claim write access everywhere.
    """
    root = Path(share_root) if share_root is not None else Path.home() / ".local/share"
    now = time.time() if now is None else now
    cutoff = now - min_days * 86400.0
    removable: list[dict] = []
    protected: list[dict] = []
    try:
        owners = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError:
        return removable, protected
    for owner in owners:
        for parent_name in sorted(_RELEASE_PARENT_NAMES):
            parent = owner / parent_name
            if not parent.is_dir():
                continue
            try:
                children = sorted(parent.iterdir())
            except OSError:
                continue
            for child in children:
                try:
                    stat = child.stat(follow_symlinks=False)
                except OSError:
                    continue
                if not os.path.isdir(child) or child.is_symlink():
                    continue
                if stat.st_mtime > cutoff:
                    continue
                entry = {
                    "path": child,
                    "owner": owner.name,
                    "mtime": stat.st_mtime,
                    "size_bytes": _dir_size(child),
                }
                if _write_allowed(parent) and _write_allowed(child):
                    removable.append(entry)
                else:
                    protected.append(entry)
    return removable, protected


def remove_release_caches(entries: Iterable[dict], *, dry_run: bool = False) -> int:
    """Remove stale release-cache entries; return bytes reclaimed."""
    reclaimed = 0
    for entry in entries:
        path = Path(entry["path"])
        size = int(entry.get("size_bytes") or 0)
        if dry_run:
            reclaimed += size
            continue
        try:
            shutil.rmtree(path)
        except OSError:
            # Newly protected or busy: skip without counting.
            continue
        reclaimed += size
    return reclaimed


def docker_call(
    args: list[str], timeout: int = DOCKER_CALL_TIMEOUT_SECONDS
) -> tuple[bool, str]:
    """Run ``docker <args>`` with a hard timeout.

    Returns ``(ok, output)``. A missing binary, a timeout or a non-zero exit
    is a skipped tier, never a crash of the whole ladder.
    """
    try:
        completed = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return False, "docker not available"
    except subprocess.TimeoutExpired:
        return False, f"docker {args[0]} timed out after {timeout}s (busy daemon)"
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode == 0, output.strip()


def _docker_used_image_refs(timeout: int) -> tuple[set[str], set[str]] | None:
    """Return ``(used_ids, used_names)`` from one cheap ``ps -a`` call.

    Container→image resolution via ``docker inspect`` races with the daemon
    on busy hosts (containers vanish mid-chunk); ``ps --format {{.Image}}``
    already carries the reference (``repo:tag`` or ``sha256:…``).
    """
    ok, out = docker_call(["ps", "-a", "--format", "{{.Image}}"], timeout)
    if not ok:
        return None
    used_ids: set[str] = set()
    used_names: set[str] = set()
    for line in out.splitlines():
        ref = line.strip()
        if not ref:
            continue
        if ref.startswith("sha256:"):
            used_ids.add(ref.split(":", 1)[1])
        else:
            used_names.add(ref)
    return used_ids, used_names


def docker_prune_dangling(timeout: int = DOCKER_CALL_TIMEOUT_SECONDS) -> TierResult:
    """Prune dangling images and old build cache (no volumes, no tagged data)."""
    ok, out = docker_call(["image", "prune", "-f"], timeout)
    if not ok:
        return TierResult("docker-dangling", attempted=False, skipped_reason=out)
    ok_cache, out_cache = docker_call(
        ["builder", "prune", "-f", "--filter", "until=168h"], timeout
    )
    note = out_cache if not ok_cache else ""
    return TierResult("docker-dangling", note=note)


def _parse_docker_created(value: str) -> float:
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(value.strip(), fmt))
        except ValueError:
            continue
    return 0.0


def docker_remove_unused_old_images(
    min_days: float = DEFAULT_DOCKER_IMAGE_MIN_DAYS,
    timeout: int = DOCKER_CALL_TIMEOUT_SECONDS,
) -> TierResult:
    """Remove images referenced by no container and older than ``min_days``."""
    used = _docker_used_image_refs(timeout)
    if used is None:
        return TierResult(
            "docker-unused-images", attempted=False, skipped_reason="docker unavailable"
        )
    used_ids, used_names = used
    ok, out = docker_call(
        ["images", "--format", "{{.ID}}\t{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}"],
        timeout,
    )
    if not ok:
        return TierResult("docker-unused-images", attempted=False, skipped_reason=out)
    cutoff = time.time() - min_days * 86400.0
    candidates: list[str] = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) != 3:
            continue
        image_id, name, created = parts
        if image_id in used_ids or name in used_names or name.startswith("<none>:"):
            continue
        if (
            _parse_docker_created(created) == 0.0
            or _parse_docker_created(created) > cutoff
        ):
            continue
        candidates.append(image_id)
    if not candidates:
        return TierResult("docker-unused-images")
    # Batched rmi: conflicting (multi-repo) images are skipped by the daemon.
    ok, out = docker_call(["rmi", *candidates], timeout)
    if not ok:
        return TierResult(
            "docker-unused-images", attempted=False, skipped_reason=out[:200]
        )
    return TierResult("docker-unused-images")


def run_free_target_ladder(
    goal_gb: float,
    *,
    tiers: list[Callable[[], TierResult]],
    free_fn: Callable[[], int] = lambda: free_bytes("/"),
    echo: Callable[[str], None] = print,
    dry_run: bool = False,
) -> LadderReport:
    """Run tiers in order, stopping once free space reaches ``goal_gb``.

    Tiers are callables returning :class:`TierResult`; the free-space delta
    measured around each tier is authoritative (tier-reported byte counts are
    advisory only).
    """
    report = LadderReport(
        goal_bytes=int(goal_gb * 1024**3),
        started_free_bytes=free_fn(),
    )
    report.ended_free_bytes = report.started_free_bytes
    if report.started_free_bytes >= report.goal_bytes:
        echo(
            f"Cel już osiągnięty: {report.started_free_bytes / 1024**3:.1f} GB wolnego "
            f"(cel {goal_gb:.1f} GB)."
        )
        return report
    for tier in tiers:
        before = free_fn()
        result = tier()
        after = free_fn()
        result.bytes_freed = max(0, after - before)
        report.tiers.append(result)
        report.ended_free_bytes = after
        if result.attempted:
            echo(
                f"  • {result.name}: zwolniono {result.bytes_freed / 1024**3:.2f} GB"
                + (f" ({result.skipped_reason})" if result.skipped_reason else "")
            )
        else:
            echo(f"  • {result.name}: pominięto ({result.skipped_reason})")
        if dry_run:
            continue
        if after >= report.goal_bytes:
            break
    return report


def print_privileged_hints(goal_gb: float, report: LadderReport) -> None:
    """Print exact next steps needing privileges when the goal is unmet."""
    if report.goal_reached:
        return
    gap_gb = (report.goal_bytes - report.ended_free_bytes) / 1024**3
    print()
    print(
        f"Brakuje ~{gap_gb:.1f} GB do celu {goal_gb:.1f} GB. "
        "Kolejne pule wymagają uprawnień — wykonaj ręcznie:"
    )
    print("  sudo snap set system refresh.retain=2   # ogranicz przyszłe rewizje")
    print(
        "  snap list --all | awk '/disabled/{print $1, $3}' | "
        'while read n r; do sudo snap remove "$n" --revision="$r"; done'
    )
    print("  sudo journalctl --vacuum-size=500M      # przycięcie dziennika")
    print("  sudo rm /var/log/syslog.[0-9].gz        # stare rotacje sysloga")
