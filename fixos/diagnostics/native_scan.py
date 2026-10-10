"""Read-only filesystem measurements, optionally accelerated by fixos-native.

Install the separate Rust CLI on PATH (or set FIXOS_NATIVE_BIN to its absolute
path). The versioned JSON protocol is optional; failures use the Python scanner.
Neither implementation follows links or reads file contents.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

PROTOCOL = "fixos-scan/v1"


def find_native_binary() -> Path | None:
    """Locate the fixos-native Rust executable if available."""
    if os.environ.get("FIXOS_NATIVE", "auto") == "off":
        return None
    raw = os.environ.get("FIXOS_NATIVE_BIN") or shutil.which("fixos-native")
    if raw:
        p = Path(raw)
        if p.is_absolute():
            return p
        which_path = shutil.which(raw)
        if which_path:
            return Path(which_path)
    defaults = [
        Path.home() / ".local" / "bin" / "fixos-native",
        Path.home() / "github" / "semcod" / "fixos-native" / "target" / "release" / "fixos-native",
    ]
    for d in defaults:
        if d.is_file() and os.access(d, os.X_OK):
            return d
    return None


def measure_tree(
    path: Path, exclude: tuple[str, ...] = (), *, native: bool = True
) -> dict:
    if native:
        executable = find_native_binary()
        if executable and executable.is_absolute():
            try:
                result = subprocess.run(
                    [str(executable), "measure", str(path), *exclude],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=True,
                )
                data = json.loads(result.stdout)
                fields = ("bytes", "entries", "mtime_ns", "atime_ns")
                if (
                    isinstance(data, dict)
                    and data.get("protocol") == PROTOCOL
                    and data.get("path") == str(path)
                    and all(type(data.get(k)) is int and data[k] >= 0 for k in fields)
                    and isinstance(data.get("errors"), list)
                ):
                    return data
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
    return measure_python(path, exclude)


def measure_batch(
    paths: list[Path], exclude: tuple[str, ...] = (), *, native: bool = True
) -> dict[str, dict]:
    """Measure multiple paths, accelerating with Rust batch measurement if available."""
    if not paths:
        return {}
    if native:
        executable = find_native_binary()
        if executable and executable.is_absolute():
            abs_paths = [str(p.resolve()) for p in paths if p.is_absolute() or p.exists()]
            if abs_paths:
                try:
                    result = subprocess.run(
                        [str(executable), "batch-measure", *abs_paths],
                        capture_output=True,
                        text=True,
                        timeout=120,
                        check=True,
                    )
                    data = json.loads(result.stdout)
                    if (
                        isinstance(data, dict)
                        and data.get("protocol") == PROTOCOL
                        and isinstance(data.get("measurements"), dict)
                    ):
                        measurements = data["measurements"]
                        res = {}
                        for p_str, m in measurements.items():
                            fields = ("bytes", "entries", "mtime_ns", "atime_ns")
                            if all(type(m.get(k)) is int and m[k] >= 0 for k in fields):
                                res[p_str] = m
                        if res:
                            return res
                except (OSError, ValueError, subprocess.SubprocessError):
                    pass
    return {str(p.resolve()): measure_python(p, exclude) for p in paths}


def scan_dir_native(
    base: Path, min_bytes: int = 0, exclude: tuple[str, ...] = ()
) -> list[dict] | None:
    """Scan subdirectories of base in Rust, returning sorted list of directory measurements."""
    if not base.is_absolute() or not base.is_dir():
        return None
    executable = find_native_binary()
    if not executable or not executable.is_absolute():
        return None
    try:
        cmd = [str(executable), "scan-dir", str(base.resolve()), str(min_bytes)]
        if exclude:
            cmd.append(",".join(sorted(exclude)))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        data = json.loads(result.stdout)
        if (
            isinstance(data, dict)
            and data.get("protocol") == PROTOCOL
            and isinstance(data.get("entries"), list)
        ):
            return data["entries"]
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None



def measure_python(path: Path, exclude: tuple[str, ...] = ()) -> dict:
    result = {
        "protocol": PROTOCOL,
        "path": str(path),
        "bytes": 0,
        "entries": 0,
        "mtime_ns": 0,
        "atime_ns": 0,
        "errors": [],
    }
    stack = [path]
    seen = set()
    device = None
    while stack:
        current = stack.pop()
        try:
            info = current.lstat()
            if device is None:
                device = info.st_dev
            if info.st_dev != device:
                raise OSError("filesystem boundary")
            result["entries"] += 1
            result["mtime_ns"] = max(result["mtime_ns"], info.st_mtime_ns)
            if not stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
                result["atime_ns"] = max(result["atime_ns"], info.st_atime_ns)
            identity = (info.st_dev, info.st_ino)
            if identity not in seen:
                seen.add(identity)
                result["bytes"] += (
                    getattr(info, "st_blocks", (info.st_size + 511) // 512) * 512
                )
            if stat.S_ISDIR(info.st_mode):
                with os.scandir(current) as entries:
                    stack.extend(Path(e.path) for e in entries if e.name not in exclude)
        except OSError as exc:
            result["errors"].append(f"{current}: {exc}")
    return result


def discover_native(
    base: Path, max_depth: int, markers: tuple[str, ...], prune: frozenset[str]
) -> list[Path] | None:
    # Process/validation overhead dominates small root searches; opt in only
    # after benchmarking the workspace. Heavy tree measurement remains automatic.
    if (
        not base.is_absolute()
        or os.environ.get("FIXOS_NATIVE_DISCOVERY") != "1"
        or os.environ.get("FIXOS_NATIVE", "auto") == "off"
        or not 0 <= max_depth <= 64
    ):
        return None
    executable = find_native_binary()
    if not executable or not executable.is_absolute():
        return None
    try:
        result = subprocess.run(
            [
                str(executable),
                "discover",
                str(base.absolute()),
                str(max_depth),
                ",".join(markers),
                ",".join(sorted(prune)),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
        data = json.loads(result.stdout)
        if (
            not isinstance(data, dict)
            or data.get("protocol") != PROTOCOL
            or data.get("path") != str(base.absolute())
            or data.get("errors") != []
            or not isinstance(data.get("roots"), list)
        ):
            return None
        roots = []
        checked = set()
        for value in data["roots"]:
            if not isinstance(value, str):
                return None
            root = Path(value)
            if not root.is_absolute() or not root.is_relative_to(base.absolute()):
                return None
            relative = root.relative_to(base.absolute())
            if ".." in relative.parts or len(relative.parts) > max_depth:
                return None
            for part in (root, *root.parents):
                if part not in checked:
                    if part.is_symlink():
                        return None
                    checked.add(part)
            roots.append(root)
        return sorted(set(roots))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
