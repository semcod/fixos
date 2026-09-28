"""Conservative virtualenv inventory and explicitly selected deletion."""

from __future__ import annotations

import os
import shutil
import stat
import sys
import time
from pathlib import Path

import psutil

from fixos.diagnostics.native_scan import measure_tree
from fixos.diagnostics.project_scanner import (
    REMOVABLE_ARTIFACTS,
    discover_project_roots,
)

VENV_NAMES = ("venv", ".venv")


def _plain_path(path: Path) -> bool:
    return path.is_absolute() and all(not p.is_symlink() for p in (path, *path.parents))


def active_paths() -> tuple[set[Path], list[str]]:
    """Collect visible process paths without discarding other readable fields."""
    paths = {Path(sys.prefix).absolute(), Path.cwd()}
    errors = []
    if os.environ.get("VIRTUAL_ENV"):
        paths.add(Path(os.environ["VIRTUAL_ENV"]).absolute())
    user = psutil.Process().username()
    for process in psutil.process_iter():
        process_pid = process.pid

        def observe(field, callback, pid=process_pid):
            try:
                return callback()
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                raise
            except (psutil.AccessDenied, OSError) as exc:
                errors.append(f"PID {pid} {field}: {type(exc).__name__}")
                return None

        try:
            owner = observe("username", process.username)
            if owner is None:
                uids = observe("uids", process.uids)
                if uids is None or uids.real != os.getuid():
                    continue
            elif owner != user:
                continue

            values = []
            for field, callback in (
                ("cwd", process.cwd),
                ("exe", process.exe),
                ("cmdline", process.cmdline),
                ("open_files", process.open_files),
                ("environ", process.environ),
            ):
                value = observe(field, callback)
                if field == "cmdline" and value is not None:
                    values.extend(value)
                elif field == "open_files" and value is not None:
                    values.extend(item.path for item in value)
                elif field == "environ" and value is not None:
                    values.append(value.get("VIRTUAL_ENV", ""))
                elif field != "cmdline" and field != "open_files" and field != "environ":
                    values.append(value or "")
            for value in values:
                if value and os.path.isabs(value):
                    paths.add(Path(os.path.normpath(value)))
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
    return paths, errors


def _within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def inspect_project(
    project: Path,
    days: int,
    paths: set[Path],
    *,
    now_ns: int | None = None,
) -> list[dict]:
    cutoff = (now_ns if now_ns is not None else time.time_ns()) - days * 86400 * 10**9
    source = measure_tree(project, tuple(REMOVABLE_ARTIFACTS))
    project_active = any(_within(p, project) for p in paths)
    items = []
    parent_info = project.stat(follow_symlinks=False)
    parent_identity = [parent_info.st_dev, parent_info.st_ino]
    try:
        mounts = {Path(part.mountpoint) for part in psutil.disk_partitions(all=True)}
    except OSError:
        mounts = None
    for name in VENV_NAMES:
        env = project / name
        if not env.exists() and not env.is_symlink():
            continue
        reasons = []
        if not _plain_path(env) or not env.is_dir():
            reasons.append("ścieżka jest dowiązaniem lub nie jest katalogiem")
        if mounts is None or any(_within(mount, env) for mount in mounts):
            reasons.append(
                "punkt montowania w środowisku lub niepełna obserwacja montowań"
            )
        cfg = env / "pyvenv.cfg"
        if not cfg.is_file() or cfg.is_symlink():
            reasons.append("brak zwykłego pliku pyvenv.cfg")
        if not _plain_path(project):
            reasons.append("projekt zawiera dowiązanie w ścieżce")
        measurement = measure_tree(env) if not reasons else None
        if source["errors"] or (measurement and measurement["errors"]):
            reasons.append("niepełna obserwacja plików lub procesów")
        if max(source["mtime_ns"], source["atime_ns"]) >= cutoff:
            reasons.append("projekt ma nowszą aktywność")
        if (
            measurement
            and max(measurement["mtime_ns"], measurement["atime_ns"]) >= cutoff
        ):
            reasons.append("środowisko ma nowszą aktywność")
        if project_active:
            reasons.append("projekt lub środowisko używane przez proces")
        try:
            info = env.lstat()
            identity = [info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns]
        except OSError:
            identity = None
            reasons.append("nie można odczytać katalogu")
        items.append(
            {
                "path": str(env),
                "project": str(project),
                "eligible": not reasons,
                "reasons": reasons,
                "bytes": measurement["bytes"]
                if measurement and not measurement["errors"]
                else None,
                "identity": identity,
                "project_identity": parent_identity,
                "measurement": measurement,
                "source": source,
            }
        )
    return items


def scan_venvs(base: Path, days: int = 30) -> dict:
    if days < 1:
        raise ValueError("Okres musi być dodatnią liczbą dni")
    base = base.expanduser().absolute()
    if not _plain_path(base) or not base.is_dir():
        raise ValueError("Katalog projektów musi istnieć i nie może zawierać dowiązań")
    paths, process_errors = active_paths()
    items = []
    discovery_errors = []
    projects = discover_project_roots(base, errors=discovery_errors)
    for project in projects:
        items.extend(inspect_project(project, days, paths))
    eligible = [item for item in items if item["eligible"]]
    return {
        "base": str(base),
        "days": days,
        "found": len(items),
        "total_bytes": sum(item["bytes"] or 0 for item in items),
        "unknown_sizes": sum(item["bytes"] is None for item in items),
        "eligible": len(eligible),
        "bytes": sum(item["bytes"] for item in eligible),
        "items": items,
        "errors": process_errors + discovery_errors,
    }


def _identity(info):
    return [info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns]


def remove_venvs(items: list[dict], days: int):
    """Revalidate one selected project batch, then delete through pinned fds.

    Sibling environments are one batch: our first removal changes the project's
    directory timestamp, which must not falsely classify its sibling as active.
    Each environment identity, contents and process usage are checked again
    before its deletion. A failure stops the remainder of this project batch.
    """
    if not items or days < 1:
        raise ValueError("Nieprawidłowy wybór lub okres")
    project = Path(items[0]["project"])
    for item in items:
        env = Path(item["path"])
        if (
            not item["eligible"]
            or env.parent != project
            or item["project"] != str(project)
            or env.name not in VENV_NAMES
            or not _plain_path(env)
        ):
            raise ValueError("Nieprawidłowy cel usuwania")
    if (
        not getattr(shutil.rmtree, "avoids_symlink_attacks", False)
        or os.name != "posix"
        or (sys.version_info < (3, 11) and not Path("/proc/self/fd").is_dir())
    ):
        raise ValueError(
            "Platforma nie obsługuje bezpiecznego usuwania przez deskryptor"
        )
    paths, _errors = active_paths()
    fresh = {v["path"]: v for v in inspect_project(project, days, paths)}
    for item in items:
        current = fresh.get(item["path"])
        if (
            not current
            or not current["eligible"]
            or any(
                current[k] != item[k]
                for k in ("identity", "project_identity", "measurement", "source")
            )
        ):
            raise ValueError(
                "Stan projektu lub środowiska zmienił się; wykonaj nowy skan"
            )
    fd = os.open(project, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parent = os.fstat(fd)
        if [parent.st_dev, parent.st_ino] != items[0]["project_identity"]:
            raise ValueError("Projekt zmienił się po skanowaniu")
        for item in items:
            env = Path(item["path"])
            paths, _errors = active_paths()
            if any(_within(p, project) for p in paths):
                raise ValueError(
                    "Projekt stał się aktywny"
                )
            if not _plain_path(env) or measure_tree(env) != item["measurement"]:
                raise ValueError("Środowisko zmieniło się po skanowaniu")
            env_fd = os.open(
                env.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
            )
            try:
                if _identity(os.fstat(env_fd)) != item["identity"]:
                    raise ValueError("Ścieżka zmieniła się po skanowaniu")
                # The root fd pins the selected inode even if its name is replaced.
                # rmtree's own fd implementation protects nested symbolic links.
                with os.scandir(env_fd) as entries:
                    names = [entry.name for entry in entries]
                for name in names:
                    info = os.stat(name, dir_fd=env_fd, follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        if sys.version_info >= (3, 11):
                            shutil.rmtree(name, dir_fd=env_fd)
                        else:
                            shutil.rmtree(f"/proc/self/fd/{env_fd}/{name}")
                    else:
                        os.unlink(name, dir_fd=env_fd)
                current = os.stat(env.name, dir_fd=fd, follow_symlinks=False)
                if [current.st_dev, current.st_ino] != item["identity"][:2]:
                    raise ValueError("Nazwa środowiska zmieniła się podczas usuwania")
                os.rmdir(env.name, dir_fd=fd)
            finally:
                os.close(env_fd)
            yield item
    finally:
        os.close(fd)


def remove_venv(item: dict, days: int) -> None:
    list(remove_venvs([item], days))
