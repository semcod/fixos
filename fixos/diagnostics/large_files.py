"""Bounded, read-only large-file triage with deterministic decision evidence."""

from __future__ import annotations

import heapq
import math
import os
import re
import shutil
import stat
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fixos.diagnostics.storage_rules import RULESET_VERSION, decide_file, file_kind

DEFAULT_MIN_BYTES = 500_000_000
_PSEUDO = {Path("/proc"), Path("/sys"), Path("/dev"), Path("/run")}


def _unescape_proc(value: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), value)


def _swap_evidence() -> dict:
    paths, identities = set(), set()
    try:
        with open("/proc/swaps", encoding="utf-8") as source:
            for line in source:
                fields = line.split()
                if not fields or fields[0] == "Filename":
                    continue
                path = _unescape_proc(fields[0])
                paths.add(path)
                try:
                    info = os.stat(path)
                    identities.add((info.st_dev, info.st_ino))
                except OSError:
                    pass
    except OSError:
        return {"status": "unavailable", "paths": paths, "identities": identities}
    return {"status": "observed", "paths": paths, "identities": identities}


def _open_evidence(identities: set, deadline: float, max_entries: int = 20_000) -> dict:
    opened = defaultdict(set)
    deleted = {}
    examined = errors = 0
    status = "complete"
    try:
        with os.scandir("/proc") as processes:
            for process in processes:
                if not process.name.isdigit():
                    continue
                if time.monotonic() >= deadline or examined >= max_entries:
                    status = "budget-exhausted"
                    break
                try:
                    with os.scandir(Path(process.path) / "fd") as descriptors:
                        for descriptor in descriptors:
                            if time.monotonic() >= deadline or examined >= max_entries:
                                status = "budget-exhausted"
                                break
                            examined += 1
                            try:
                                info = descriptor.stat(follow_symlinks=True)
                                key = (info.st_dev, info.st_ino)
                                if key in identities:
                                    opened[key].add(int(process.name))
                                if stat.S_ISREG(info.st_mode) and info.st_nlink == 0:
                                    deleted[key] = getattr(info, "st_blocks", 0) * 512
                            except OSError:
                                errors += 1
                    # mmap can keep a model/image active after its fd is closed.
                    with open(
                        Path(process.path) / "maps", encoding="utf-8", errors="replace"
                    ) as mappings:
                        for line in mappings:
                            if time.monotonic() >= deadline or examined >= max_entries:
                                status = "budget-exhausted"
                                break
                            examined += 1
                            fields = line.split(None, 5)
                            if (
                                len(fields) >= 5
                                and fields[4].isdigit()
                                and ":" in fields[3]
                            ):
                                major, minor = fields[3].split(":", 1)
                                key = (
                                    os.makedev(int(major, 16), int(minor, 16)),
                                    int(fields[4]),
                                )
                                if key in identities:
                                    opened[key].add(int(process.name))
                except OSError:
                    errors += 1
    except OSError:
        status = "unavailable"
    if errors and status == "complete":
        status = "partial"
    return {
        "status": status,
        "opened": opened,
        "examined": examined,
        "errors": errors,
        "open_deleted_allocated_bytes": sum(deleted.values()),
        "open_deleted_files": len(deleted),
    }


def _root(path: str | Path) -> Path:
    result = Path(os.path.abspath(os.path.expanduser(path)))
    for component in (result, *result.parents):
        if component.is_symlink():
            raise ValueError(f"Symlink w ścieżce wejściowej: {component}")
    if not result.is_dir():
        raise ValueError(f"Katalog wejściowy niedostępny: {result}")
    return result


def _inventory(
    roots: list[Path], min_bytes: int, limit: int, deadline: float, max_entries: int
) -> dict:
    heap, unique_large, directories = [], {}, set()
    stats = {
        "entries_scanned": 0,
        "large_paths": 0,
        "unique_large_files": 0,
        "hardlink_paths_deduplicated": 0,
        "symlinks_skipped": 0,
        "mounts_skipped": 0,
        "pseudo_filesystems_skipped": 0,
        "errors": 0,
        "error_samples": [],
        "budget_exhausted": False,
    }
    for root in roots:
        pending = [root]
        device = root.stat().st_dev
        while pending:
            if time.monotonic() >= deadline or stats["entries_scanned"] >= max_entries:
                stats["budget_exhausted"] = True
                break
            directory = pending.pop()
            try:
                if directory in _PSEUDO:
                    stats["pseudo_filesystems_skipped"] += 1
                    continue
                info = directory.lstat()
                if not stat.S_ISDIR(info.st_mode):
                    stats["symlinks_skipped"] += int(stat.S_ISLNK(info.st_mode))
                    continue
                identity = (info.st_dev, info.st_ino)
                if info.st_dev != device:
                    stats["mounts_skipped"] += 1
                    continue
                if identity in directories:
                    continue
                directories.add(identity)
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if (
                            time.monotonic() >= deadline
                            or stats["entries_scanned"] >= max_entries
                        ):
                            stats["budget_exhausted"] = True
                            break
                        stats["entries_scanned"] += 1
                        try:
                            info = entry.stat(follow_symlinks=False)
                            if stat.S_ISLNK(info.st_mode):
                                stats["symlinks_skipped"] += 1
                            elif info.st_dev != device:
                                stats["mounts_skipped"] += 1
                            elif stat.S_ISDIR(info.st_mode):
                                pending.append(Path(entry.path))
                            elif (
                                stat.S_ISREG(info.st_mode) and info.st_size > min_bytes
                            ):
                                stats["large_paths"] += 1
                                key = (info.st_dev, info.st_ino)
                                if key in unique_large:
                                    stats["hardlink_paths_deduplicated"] += 1
                                    if len(unique_large[key]) < 20:
                                        unique_large[key].append(entry.path)
                                    continue
                                unique_large[key] = [entry.path]
                                stats["unique_large_files"] += 1
                                candidate = (info.st_size, entry.path, info)
                                if len(heap) < limit:
                                    heapq.heappush(heap, candidate)
                                elif candidate[:2] > heap[0][:2]:
                                    heapq.heapreplace(heap, candidate)
                        except OSError as error:
                            _record_error(stats, Path(entry.path), error)
            except OSError as error:
                _record_error(stats, directory, error)
        if stats["budget_exhausted"]:
            break
    stats["status"] = (
        "partial" if stats["budget_exhausted"] or stats["errors"] else "complete"
    )
    return dict(
        files=sorted(heap, key=lambda row: (-row[0], row[1])),
        aliases=unique_large,
        **stats,
    )


def _record_error(stats: dict, path: Path, error: OSError) -> None:
    stats["errors"] += 1
    if len(stats["error_samples"]) < 20:
        stats["error_samples"].append({"path": str(path), "errno": error.errno})


def _repository(path: Path, cache: dict) -> str | None:
    for parent in path.parents:
        if parent in cache:
            return cache[parent]
        if (parent / ".git").exists():
            cache[path.parent] = str(parent)
            return str(parent)
    cache[path.parent] = None
    return None


def _header(path: Path, expected: os.stat_result) -> tuple[bytes, str]:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        )
        with os.fdopen(descriptor, "rb") as source:
            actual = os.fstat(source.fileno())
            if not stat.S_ISREG(actual.st_mode) or (
                actual.st_dev,
                actual.st_ino,
                actual.st_size,
                actual.st_mtime_ns,
            ) != (
                expected.st_dev,
                expected.st_ino,
                expected.st_size,
                expected.st_mtime_ns,
            ):
                return b"", "changed-during-scan"
            return source.read(32), "sampled-32-bytes"
    except OSError:
        return b"", "unavailable"


def _owner(uid: int) -> str:
    try:
        import pwd

        return pwd.getpwuid(uid).pw_name
    except (ImportError, KeyError):
        return str(uid)


def analyze_large_files(
    roots: list[str | Path],
    *,
    min_bytes: int = DEFAULT_MIN_BYTES,
    limit: int = 50,
    max_seconds: float = 30,
    max_entries: int = 200_000,
) -> dict:
    """Find largest files in the observed scope, never claim unseen paths were scanned."""
    if (
        not roots
        or min_bytes < 0
        or limit < 1
        or not math.isfinite(max_seconds)
        or max_seconds <= 0
        or max_entries < 1
    ):
        raise ValueError("Nieprawidłowy zakres lub budżet skanu.")
    roots = list(dict.fromkeys(_root(path) for path in roots))
    started = time.monotonic()
    deadline = started + max_seconds
    swap = _swap_evidence()
    # A large tree must not consume the entire budget before active-use checks.
    scan_deadline = deadline - min(2, max_seconds * 0.2)
    inventory = _inventory(roots, min_bytes, limit, scan_deadline, max_entries)
    selected = inventory.pop("files")
    aliases = inventory.pop("aliases")
    identities = {(info.st_dev, info.st_ino) for _, _, info in selected}
    processes = _open_evidence(identities, min(deadline, time.monotonic() + 2))
    now = time.time()
    files, repository_cache = [], {}
    for size, name, info in selected:
        path = Path(name)
        header, signature_status = _header(path, info)
        signature_kind = file_kind(Path(""), header)
        extension_kind = file_kind(path)
        kind = file_kind(path, header)
        allocated = info.st_blocks * 512 if hasattr(info, "st_blocks") else None
        identity = (info.st_dev, info.st_ino)
        repository = _repository(path, repository_cache)
        row = {
            "path": name,
            "name": path.name,
            "directory": str(path.parent),
            "repository": repository,
            "kind": kind,
            "type_evidence": "signature"
            if signature_kind != "other" and signature_kind == kind
            else "extension"
            if extension_kind != "other"
            else "unknown",
            "signature_status": signature_status,
            "logical_bytes": size,
            "allocated_bytes": allocated,
            "sparse": allocated is not None and allocated < size,
            "link_count": info.st_nlink,
            "device": info.st_dev,
            "inode": info.st_ino,
            "observed_paths": aliases[identity],
            "observed_paths_may_be_incomplete": len(aliases[identity]) < info.st_nlink,
            "uid": info.st_uid,
            "owner": _owner(info.st_uid),
            "modified_at": datetime.fromtimestamp(
                info.st_mtime, timezone.utc
            ).isoformat(),
            "age_days": max(0, round((now - info.st_mtime) / 86400, 1)),
            "active_swap": identity in swap["identities"] or name in swap["paths"],
            "open_pids": sorted(processes["opened"].get(identity, set())),
            "process_visibility": processes["status"],
        }
        row.update(decide_file(row))
        if signature_status == "changed-during-scan":
            row.update(
                decision="protected",
                rule_id="CHANGED_DURING_SCAN",
                reclaim_upper_bound_bytes=0,
            )
            row["reasons"].insert(
                0, "Plik zmienił się podczas skanu; wymagany ponowny odczyt."
            )
        files.append(row)
    groups = defaultdict(list)
    for row in files:
        groups[
            (
                row["decision"],
                row["kind"],
                row["repository"] or row["directory"],
                row["owner"],
            )
        ].append(row)
    grouped = [
        {
            "decision": key[0],
            "kind": key[1],
            "location": key[2],
            "owner": key[3],
            "files": len(rows),
            "logical_bytes": sum(r["logical_bytes"] for r in rows),
            "allocated_bytes": sum(r["allocated_bytes"] for r in rows)
            if all(r["allocated_bytes"] is not None for r in rows)
            else None,
            "reclaim_upper_bound_bytes": sum(
                r["reclaim_upper_bound_bytes"] for r in rows
            )
            if all(r["reclaim_upper_bound_bytes"] is not None for r in rows)
            else None,
            "paths": [r["path"] for r in rows],
        }
        for key, rows in sorted(groups.items())
    ]
    filesystems = []
    for root in roots:
        usage = shutil.disk_usage(root)
        filesystems.append(
            {
                "path": str(root),
                "device": root.stat().st_dev,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "available_bytes": usage.free,
                "unavailable_or_reserved_bytes": max(
                    0, usage.total - usage.used - usage.free
                ),
            }
        )
    return {
        "schema": "fixos.storage-triage/v1",
        "ruleset_version": RULESET_VERSION,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "roots": [str(r) for r in roots],
        "min_bytes_exclusive": min_bytes,
        "units": {"MB": 10**6, "GB": 10**9, "MiB": 2**20, "GiB": 2**30},
        "limits": {
            "max_seconds": max_seconds,
            "max_entries": max_entries,
            "result_limit": limit,
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "scan": inventory,
        "results_truncated": inventory["unique_large_files"] > len(files),
        "swap_probe": {"status": swap["status"], "active_paths": sorted(swap["paths"])},
        "process_probe": {k: v for k, v in processes.items() if k != "opened"},
        "filesystems": filesystems,
        "files": files,
        "groups": grouped,
        "llm_used": False,
        "data_mutations": 0,
        "notes": [
            "Wyniki dotyczą tylko podanego zakresu i zaobserwowanych wpisów; największe pliki są wybierane w tym zakresie.",
            "st_blocks to przydzielone bloki, nie gwarancja odzysku; reflinki, snapshoty i równoległe zapisy mogą zmienić wynik.",
            "Hardlinki odjęto według device/inode. Wiek to mtime, nie dowód ostatniego użycia ani zbędności.",
            "Zależności niepotwierdzone wymagają przeglądu. Żadna reguła nie zezwala na automatyczne usunięcie.",
        ],
    }
