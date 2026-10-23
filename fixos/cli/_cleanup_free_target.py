"""Target-driven cleanup ladder: reclaim disk until a free-space goal is met.

The NoLimits LIM-STORAGE-001 runbook wants "cleanup until N GB free".
``--threshold-gb`` cannot express that (it filters which *services* are
reported), so this module provides the goal-oriented pieces:

- :func:`free_bytes` — statvfs-based free space of a filesystem.
- :func:`find_stale_release_caches` — compatibility inventory of old persistent
  releases/snapshots. Every entry is protected, regardless of write bits.
- :func:`remove_release_caches` — compatibility guard that never deletes
  persistent deployment/rollback data or counts it as reclaimable space.
- :func:`docker_call` — batched ``docker`` subprocess with a hard timeout so a
  busy daemon skips a tier instead of hanging the whole command.
- :func:`run_free_target_ladder` — generic runner that measures free space
  before and after each tier and stops as soon as the goal is reached.

Nothing here deletes user documents, models, editor data, Docker volumes, or
anything that needs elevated privileges.
"""

from __future__ import annotations

import os
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


def find_stale_release_caches(
    share_root: Path | str | None = None,
    min_days: float = DEFAULT_RELEASE_CACHE_MIN_DAYS,
    *,
    now: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return ``([], protected)`` old persistent release/snapshot entries.

    An entry is a directory directly below
    ``<share_root>/<owner>/releases|release|snapshots/`` whose own mtime is
    older than ``min_days`` days. Neither age nor writable mode bits prove that
    immutable deployed releases or rollback snapshots are disposable caches.
    Preserve all of them: partial systemd/process reference discovery cannot
    establish that an unreferenced entry is safe to delete either. The owning
    deployment lifecycle must retire these trees. Do not traverse their payloads
    merely to report protected entries; size_bytes=0 means unmeasured here.
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
                    "size_bytes": 0,
                    "size_measured": False,
                    "reason": "persistent deployment/rollback data",
                }
                protected.append(entry)
    return removable, protected


def remove_release_caches(entries: Iterable[dict], *, dry_run: bool = False) -> int:
    """Preserve persistent releases/snapshots; always return zero bytes.

    Retained for compatibility with callers holding a precomputed cleanup plan.
    Reject every candidate, including stale or forged writable entries, without
    inspecting or deleting its path. Dry-run must not promise this space either.
    """
    return 0


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
