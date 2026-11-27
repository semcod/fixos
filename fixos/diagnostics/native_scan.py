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
_NON_NEGATIVE_INT_FIELDS = ("bytes", "entries", "mtime_ns", "atime_ns")


def _is_non_negative_int(value: object) -> bool:
    """Accept only genuine non-negative int values (never bool)."""
    return type(value) is int and value >= 0


def _valid_error_list(value: object) -> list[str] | None:
    """Return a copied list of string errors, or None when malformed."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def _valid_timeout(timeout: object) -> bool:
    """Reject booleans, zero, negative, or non-numeric timeouts."""
    return isinstance(timeout, (int, float)) and not isinstance(timeout, bool) and timeout > 0


def _validate_measurement_record(
    record: object, *, expected_path: str, require_protocol: bool
) -> dict | None:
    """Validate a native measurement payload and return normalized copy or None."""
    if not isinstance(record, dict):
        return None
    if require_protocol:
        if record.get("protocol") != PROTOCOL or record.get("path") != expected_path:
            return None
    elif "path" in record and record.get("path") != expected_path:
        return None
    if not all(_is_non_negative_int(record.get(k)) for k in _NON_NEGATIVE_INT_FIELDS):
        return None
    errors = _valid_error_list(record.get("errors"))
    if errors is None:
        return None
    normalized = {
        "protocol": PROTOCOL,
        "path": expected_path,
        **{k: record[k] for k in _NON_NEGATIVE_INT_FIELDS},
        "errors": errors,
    }
    if not require_protocol:
        normalized["complete"] = len(errors) == 0
    return normalized


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
                validated = _validate_measurement_record(
                    data, expected_path=str(path), require_protocol=True
                )
                if validated is not None:
                    return validated
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
    return measure_python(path, exclude)


def measure_batch(
    paths: list[Path],
    exclude: tuple[str, ...] = (),
    *,
    native: bool = True,
    timeout: float = 120,
    python_fallback: bool = True,
) -> dict[str, dict]:
    """Measure multiple paths, accelerating with Rust batch measurement if available.

    Results are keyed by the resolved path.  ``python_fallback=False`` returns
    only verified native results (or ``{}`` when unavailable/failing) instead
    of an unbounded Python walk or fabricated empty records.
    """
    if not paths:
        return {}
    requested: dict[str, Path] = {}
    for p in paths:
        requested.setdefault(str(p.resolve()), p)

    res: dict[str, dict] = {}
    if native and not exclude and _valid_timeout(timeout):
        executable = find_native_binary()
        if executable and executable.is_absolute():
            try:
                result = subprocess.run(
                    [str(executable), "batch-measure", *requested.keys()],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=True,
                )
                data = json.loads(result.stdout)
                if (
                    isinstance(data, dict)
                    and data.get("protocol") == PROTOCOL
                    and isinstance(data.get("measurements"), dict)
                    and set(data["measurements"].keys()).issubset(requested.keys())
                ):
                    measurements = data["measurements"]
                    for p_str in requested:
                        if p_str in measurements:
                            validated = _validate_measurement_record(
                                measurements[p_str],
                                expected_path=p_str,
                                require_protocol=False,
                            )
                            if validated is not None:
                                res[p_str] = validated
            except (OSError, ValueError, subprocess.SubprocessError):
                res = {}

    missing = [p_str for p_str in requested if p_str not in res]
    if missing and python_fallback:
        for p_str in missing:
            fallback = measure_python(requested[p_str], exclude)
            res[p_str] = {
                **fallback,
                "path": p_str,
                "complete": len(fallback["errors"]) == 0,
            }
    return res


def _scan_dir_root_binding_valid(data: dict, base_str: str) -> bool:
    """Verify scan-dir response binds explicitly to expected base path without root errors."""
    if data.get("protocol") != PROTOCOL:
        return False
    has_binding = False
    for key in ("path", "base"):
        if key in data:
            if data[key] != base_str:
                return False
            has_binding = True
    if not has_binding:
        return False
    if "errors" in data:
        root_errors = _valid_error_list(data.get("errors"))
        if root_errors is None or root_errors:
            return False
    return isinstance(data.get("entries"), list)


def _validate_scan_dir_entry(
    entry: object, base_resolved: Path, min_bytes: int, exclude_set: set[str], seen_names: set[str]
) -> dict | None:
    """Validate one scan-dir entry dictionary against root, exclude, and size contracts."""
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or name in exclude_set
        or name in seen_names
    ):
        return None
    if entry.get("path") != str(base_resolved / name):
        return None
    size_bytes = entry.get("bytes")
    if not _is_non_negative_int(size_bytes) or size_bytes < min_bytes:
        return None
    for opt_field in ("entries", "mtime_ns", "atime_ns"):
        if opt_field in entry and not _is_non_negative_int(entry.get(opt_field)):
            return None
    if "errors" in entry:
        entry_errors = _valid_error_list(entry.get("errors"))
        if entry_errors is None:
            return None
    else:
        entry_errors = []
    seen_names.add(name)
    validated = {
        "name": name,
        "path": str(base_resolved / name),
        "bytes": size_bytes,
        "errors": entry_errors,
        "complete": len(entry_errors) == 0,
    }
    for opt_field in ("entries", "mtime_ns", "atime_ns"):
        if opt_field in entry:
            validated[opt_field] = entry[opt_field]
    return validated


def scan_dir_native(
    base: Path,
    min_bytes: int = 0,
    exclude: tuple[str, ...] = (),
    *,
    timeout: float = 120,
) -> list[dict] | None:
    """Scan subdirectories of base in Rust, returning validated entries or None on incomplete/invalid output."""
    if (
        not isinstance(base, Path)
        or not base.is_absolute()
        or base.is_symlink()
        or not base.is_dir()
        or not _is_non_negative_int(min_bytes)
        or not _valid_timeout(timeout)
    ):
        return None
    base_resolved = base.resolve()
    exclude_set = {item for item in exclude if item}
    observed_subdirs: set[str] = set()
    unreadable_subdirs: set[str] = set()
    try:
        with os.scandir(base_resolved) as entries:
            for dir_entry in entries:
                if dir_entry.name in exclude_set:
                    continue
                if dir_entry.is_dir(follow_symlinks=False):
                    observed_subdirs.add(dir_entry.name)
                    if not os.access(dir_entry.path, os.R_OK | os.X_OK):
                        unreadable_subdirs.add(dir_entry.name)
    except OSError:
        return None

    executable = find_native_binary()
    if not executable or not executable.is_absolute():
        return None
    try:
        cmd = [str(executable), "scan-dir", str(base_resolved), str(min_bytes)]
        if exclude_set:
            cmd.append(",".join(sorted(exclude_set)))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or not _scan_dir_root_binding_valid(data, str(base_resolved)):
            return None
        validated: list[dict] = []
        seen_names: set[str] = set()
        for raw_entry in data["entries"]:
            item = _validate_scan_dir_entry(
                raw_entry, base_resolved, min_bytes, exclude_set, seen_names
            )
            if item is None:
                return None
            validated.append(item)
        if min_bytes == 0 and not observed_subdirs.issubset(seen_names):
            return None
        if unreadable_subdirs - seen_names:
            return None
        return validated
    except (OSError, ValueError, subprocess.SubprocessError):
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
