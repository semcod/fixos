"""Retention for date-partitioned application state stores.

Collectors and agents often append telemetry under XDG state/data directories
as ``<store>/YYYY/MM/DD/`` without any retention, which can fill a disk at
several GB per day.  This module finds such stores and selects whole day
partitions that are older than a cutoff, both by the partition name and by the
modification time of every file inside it.

Only ``DD`` directories are ever selected.  Files beside the year tree (for
example a collector's ``checkpoint.sqlite3``), symlinks, partitions on another
filesystem and the current day are never touched.  Reclaimable size counts a
hard-linked inode only when every link to it is inside the selection, so
content-addressed snapshot trees are not overestimated.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_STATE_ROOTS = ("~/.local/state", "~/.local/share")
MAX_STORE_DEPTH = 5


@dataclass
class DayPartition:
    path: Path
    day: date
    newest_mtime: float
    apparent_bytes: int
    inodes: dict[tuple[int, int], tuple[int, int, int]] = field(repr=False)


@dataclass
class PartitionedStore:
    path: Path
    old_days: list[DayPartition]
    kept_days: int
    apparent_bytes: int
    reclaimable_bytes: int

    @property
    def oldest(self) -> date:
        return self.old_days[0].day

    @property
    def newest(self) -> date:
        return self.old_days[-1].day


def _numeric_children(path: Path, width: int, low: int, high: int) -> list[tuple[int, Path]]:
    found = []
    try:
        entries = list(os.scandir(path))
    except OSError:
        return found
    for entry in entries:
        name = entry.name
        if (
            len(name) == width
            and name.isdigit()
            and low <= int(name) <= high
            and entry.is_dir(follow_symlinks=False)
        ):
            found.append((int(name), Path(entry.path)))
    return sorted(found)


def _day_partitions(store: Path) -> list[tuple[date, Path]]:
    days = []
    for year, year_path in _numeric_children(store, 4, 2000, 2100):
        for month, month_path in _numeric_children(year_path, 2, 1, 12):
            for day, day_path in _numeric_children(month_path, 2, 1, 31):
                try:
                    days.append((date(year, month, day), day_path))
                except ValueError:
                    continue
    return days


def _measure(day_path: Path, root_dev: int) -> DayPartition | None:
    """Return the partition, or None when it cannot be removed safely."""
    newest = 0.0
    apparent = 0
    inodes: dict[tuple[int, int], tuple[int, int, int]] = {}
    for current, dirs, files in os.walk(day_path, followlinks=False):
        for name in dirs + files:
            try:
                info = os.lstat(os.path.join(current, name))
            except OSError:
                return None
            if info.st_dev != root_dev:
                return None
            newest = max(newest, info.st_mtime)
            if name in files and not os.path.islink(os.path.join(current, name)):
                key = (info.st_dev, info.st_ino)
                size, nlink, links = inodes.get(key, (info.st_size, info.st_nlink, 0))
                if links == 0:
                    apparent += size
                inodes[key] = (size, nlink, links + 1)
    try:
        info = os.lstat(day_path)
    except OSError:
        return None
    return DayPartition(day_path, date.min, max(newest, info.st_mtime), apparent, inodes)


def _reclaimable(partitions: list[DayPartition]) -> int:
    links: dict[tuple[int, int], int] = {}
    sizes: dict[tuple[int, int], tuple[int, int]] = {}
    for partition in partitions:
        for key, (size, nlink, count) in partition.inodes.items():
            links[key] = links.get(key, 0) + count
            sizes[key] = (size, nlink)
    # Space returns only when every directory entry of the inode is removed.
    return sum(size for key, (size, nlink) in sizes.items() if links[key] >= nlink)


def _today() -> date:
    """Local calendar day, the same clock collectors use to name partitions."""
    return datetime.now().astimezone().date()


def find_partitioned_stores(roots: list[Path], max_depth: int = MAX_STORE_DEPTH) -> list[Path]:
    """Directories that contain a ``YYYY/MM/DD`` tree, without descending into them."""
    stores: list[Path] = []
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            continue
        pending = [(root, 0)]
        while pending:
            current, depth = pending.pop()
            if _day_partitions(current):
                stores.append(current)
                continue
            if depth >= max_depth:
                continue
            try:
                entries = list(os.scandir(current))
            except OSError:
                continue
            for entry in entries:
                if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                    pending.append((Path(entry.path), depth + 1))
    return sorted(stores)


def scan_state_retention(
    days: int,
    roots: list[Path] | None = None,
    today: date | None = None,
    now: float | None = None,
) -> list[PartitionedStore]:
    """Stores with day partitions older than ``days`` by name and by file mtime."""
    if days < 1:
        raise ValueError("--days must be at least 1; the current day is never removed")
    roots = roots or [Path(root).expanduser() for root in DEFAULT_STATE_ROOTS]
    today = today or _today()
    now = now if now is not None else time.time()
    cutoff_day = today - timedelta(days=days)
    cutoff_mtime = now - days * 86400
    result = []
    for store in find_partitioned_stores(roots):
        try:
            root_dev = os.lstat(store).st_dev
        except OSError:
            continue
        old: list[DayPartition] = []
        kept = 0
        for day, day_path in _day_partitions(store):
            if day >= cutoff_day:
                kept += 1
                continue
            partition = _measure(day_path, root_dev)
            if partition is None or partition.newest_mtime >= cutoff_mtime:
                kept += 1
                continue
            partition.day = day
            old.append(partition)
        if old:
            result.append(PartitionedStore(
                path=store,
                old_days=old,
                kept_days=kept,
                apparent_bytes=sum(p.apparent_bytes for p in old),
                reclaimable_bytes=_reclaimable(old),
            ))
    return sorted(result, key=lambda store: store.reclaimable_bytes, reverse=True)


def remove_old_partitions(store: PartitionedStore) -> tuple[int, list[str]]:
    """Remove the selected day partitions and the month/year directories they empty."""
    removed = 0
    errors: list[str] = []
    for partition in store.old_days:
        if partition.path.is_symlink():
            errors.append(f"{partition.path}: symlink")
            continue
        try:
            shutil.rmtree(partition.path)
            removed += 1
        except OSError as exc:
            errors.append(f"{partition.path}: {exc}")
            continue
        for parent in (partition.path.parent, partition.path.parent.parent):
            try:
                parent.rmdir()
            except OSError:
                break
    return removed, errors
