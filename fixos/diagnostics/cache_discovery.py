"""
Generic cross-platform cache discovery for fixOS cleanup.

Finds large cache directories and Electron/Chromium app caches on Linux
(``~/.cache``, ``~/.config``), macOS (``~/Library/Caches``,
``~/Library/Application Support``), and Windows (``%LOCALAPPDATA%``,
``%APPDATA%``) without misclassifying application state or user data.
"""

from __future__ import annotations

import glob
import os
import platform
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service_scanner import ServiceDataInfo, ServiceType

from ..constants import GENERIC_CACHE_THRESHOLD_MB
from .native_scan import scan_dir_native

# Top-level cache names already handled by dedicated ServiceType scanners or
# protected system subsystems.
KNOWN_CACHE_DIR_NAMES = frozenset(
    {
        "pip",
        "npm",
        "npm-cache",
        "yarn",
        "Yarn",
        "pnpm",
        "pnpm-cache",
        "pypoetry",
        "huggingface",
        "google-chrome",
        "Google",
        "microsoft-edge",
        "mozilla",
        "Mozilla",
        "Firefox",
        "thumbnails",
        "gcloud",
        "JetBrains",
        "gradle",
        "uv",
        "torch",
        "nvidia",
        "mesa_shader_cache",
        "ms-playwright",
        "puppeteer",
        "helm",
        "bazel",
        "gh",
        "lm-studio",
        "BraveSoftware",
        "spotify",
        "log",
        "go-build",
        "ruff",
        "fixos",
    }
)

KNOWN_MACOS_SYSTEM_CACHES = frozenset(
    {
        "CloudKit",
        "FamilyCircle",
        "GeoServices",
        "PassKit",
        "Safari",
        "Homebrew",
    }
)

KNOWN_WINDOWS_LOCALAPPDATA_SKIP = frozenset(
    {
        "Application Data",
        "ConnectedDevicesPlatform",
        "Comms",
        "D3DSCache",
        "Diagnostics",
        "ElevatedDiagnostics",
        "History",
        "Microsoft",
        "Packages",
        "Programs",
        "Publishers",
        "Temp",
        "Temporary Internet Files",
        "VirtualStore",
        "pnpm-store",
    }
)

# Electron/Chromium apps scanned explicitly elsewhere or protected OS roots.
KNOWN_CONFIG_APPS = frozenset(
    {
        "Application Data",
        "google-chrome",
        "Google",
        "History",
        "microsoft-edge",
        "Microsoft",
        "BraveSoftware",
        "Code",
        "Cursor",
        "discord",
        "Slack",
        "spotify",
        "Apple",
        "AddressBook",
        "Dock",
        "Knowledge",
        "MobileSync",
        "Packages",
        "Programs",
        "Temp",
        "Temporary Internet Files",
        "VirtualStore",
    }
)

SKIP_ELECTRON_APP_DIRS = (
    KNOWN_CONFIG_APPS | KNOWN_CACHE_DIR_NAMES | KNOWN_WINDOWS_LOCALAPPDATA_SKIP
)

ELECTRON_CACHE_DIR_NAMES = (
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnCache",
    "GrShaderCache",
    "ShaderCache",
    "Service Worker",
)

GENERIC_SAFE_NAME_HINTS = (
    "cache",
    "shader",
    "tmp",
    "temp",
    "log",
    "crash",
    "thumb",
)


def normalize_path(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.expanduser(path)))


def path_is_covered(path: str, covered_paths: Iterable[str]) -> bool:
    """Return True when path is already represented by a known service scan."""
    norm_target = Path(normalize_path(path))
    for covered in covered_paths:
        expanded = os.path.expanduser(covered)
        norm_cov = Path(os.path.normcase(os.path.realpath(expanded)))
        if (
            norm_target == norm_cov
            or norm_target.is_relative_to(norm_cov)
            or norm_cov.is_relative_to(norm_target)
        ):
            return True
    return False


def is_generic_cache_safe(path: str) -> bool:
    """Heuristic safety check for unknown cache directories across POSIX/Windows."""
    cleaned = path.rstrip("/\\")
    base = cleaned.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return any(hint in base for hint in GENERIC_SAFE_NAME_HINTS)


def _is_link_or_junction(path: str) -> bool:
    """Return True when path is a symlink or a Windows NTFS junction."""
    if os.path.islink(path):
        return True
    is_junction = getattr(os.path, "isjunction", None)
    return bool(is_junction and is_junction(path))


def _expand_norm(path: str) -> str:
    return os.path.normpath(os.path.expanduser(path))


def _resolve_platform_roots(system_name: str) -> tuple[list[tuple[str, bool]], list[str]]:
    """Return ``(cache_roots_with_strict_flag, electron_app_roots)`` for ``system_name``.

    When ``strict_cache_subpath`` is True (Windows ``%LOCALAPPDATA%``), arbitrary
    top-level application directories are NOT treated as generic caches unless their
    directory name matches ``is_generic_cache_safe`` or they contain an explicit
    ``Cache`` / ``Caches`` subdirectory.
    """
    xdg_cache = _expand_norm("~/.cache")
    xdg_config = _expand_norm("~/.config")

    if system_name == "Darwin":
        macos_caches = _expand_norm("~/Library/Caches")
        macos_app_support = _expand_norm("~/Library/Application Support")
        return (
            [(macos_caches, False), (xdg_cache, False)],
            [macos_app_support, xdg_config],
        )

    if system_name == "Windows":
        local_app = os.path.normpath(
            os.environ.get("LOCALAPPDATA") or _expand_norm("~/AppData/Local")
        )
        roaming_app = os.path.normpath(
            os.environ.get("APPDATA") or _expand_norm("~/AppData/Roaming")
        )
        electron_roots = [roaming_app]
        if local_app != roaming_app:
            electron_roots.append(local_app)
        if xdg_config not in electron_roots:
            electron_roots.append(xdg_config)
        return ([(local_app, True), (xdg_cache, False)], electron_roots)

    return ([(xdg_cache, False)], [xdg_config])


def discover_additional_caches(
    get_size_mb: Callable[[str], float],
    threshold_mb: int,
    covered_paths: set[str],
    *,
    system_name: str | None = None,
) -> list[ServiceDataInfo]:
    """Discover large caches not already covered by known service scanners."""
    effective_os = system_name or platform.system()
    generic_threshold = max(threshold_mb, GENERIC_CACHE_THRESHOLD_MB)
    cache_roots, electron_roots = _resolve_platform_roots(effective_os)

    results: list[ServiceDataInfo] = []
    seen_paths: set[str] = set()

    for cache_root, strict_mode in cache_roots:
        for info in _discover_cache_root_dirs(
            cache_root,
            get_size_mb,
            generic_threshold,
            covered_paths,
            system_name=effective_os,
            strict_windows_layout=strict_mode,
        ):
            norm = normalize_path(info.path)
            if norm not in seen_paths:
                seen_paths.add(norm)
                results.append(info)

    for app_root in electron_roots:
        for info in _discover_electron_caches_in_root(
            app_root,
            get_size_mb,
            threshold_mb,
            covered_paths,
        ):
            norm = normalize_path(info.path)
            if norm not in seen_paths:
                seen_paths.add(norm)
                results.append(info)

    results.sort(key=lambda item: item.size_mb, reverse=True)
    return results


def _discover_cache_root_dirs(
    cache_root: str,
    get_size_mb: Callable[[str], float],
    threshold_mb: int,
    covered_paths: set[str],
    *,
    system_name: str,
    strict_windows_layout: bool,
) -> list[ServiceDataInfo]:
    if not os.path.isdir(cache_root):
        return []

    skip_names = set(KNOWN_CACHE_DIR_NAMES)
    if system_name == "Darwin":
        skip_names |= KNOWN_MACOS_SYSTEM_CACHES
    elif system_name == "Windows":
        skip_names |= KNOWN_WINDOWS_LOCALAPPDATA_SKIP

    results: list[ServiceDataInfo] = []

    use_native = (
        not strict_windows_layout
        and getattr(get_size_mb, "__name__", "") in ("_get_path_size_mb", "measure_tree")
    )
    if use_native:
        native_entries = scan_dir_native(
            Path(cache_root),
            min_bytes=threshold_mb * 1024 * 1024,
            exclude=tuple(skip_names),
        )
    else:
        native_entries = None

    if native_entries is not None:
        for item in native_entries:
            name = item.get("name", "")
            path = item.get("path", "")
            if (
                not path
                or name.startswith("com.apple.")
                or path_is_covered(path, covered_paths)
            ):
                continue
            size_mb = item.get("bytes", 0) / (1024 * 1024)
            if size_mb < threshold_mb:
                continue
            safe = system_name == "Darwin" or is_generic_cache_safe(path)
            results.append(
                _build_generic_entry(
                    label=f"Cache: {name}",
                    path=path,
                    size_mb=round(size_mb, 2),
                    safe=safe,
                    description=f"Discovered cache directory ({path})",
                )
            )
        return results

    try:
        entries = sorted(os.listdir(cache_root))
    except OSError:
        return []

    for entry in entries:
        if entry in skip_names or (
            system_name == "Darwin" and entry.startswith("com.apple.")
        ):
            continue

        path = os.path.join(cache_root, entry)
        if not os.path.isdir(path) or _is_link_or_junction(path):
            continue
        if path_is_covered(path, covered_paths):
            continue

        if strict_windows_layout:
            if is_generic_cache_safe(entry):
                size_mb = get_size_mb(path)
                if size_mb >= threshold_mb:
                    results.append(
                        _build_generic_entry(
                            label=f"Cache: {entry}",
                            path=path,
                            size_mb=size_mb,
                            safe=True,
                            description=f"Discovered Windows cache directory ({path})",
                        )
                    )
                continue

            # Inside %LOCALAPPDATA%\<App>, only explicit Cache/Caches subdirs qualify,
            # preserving non-cache application state.
            for sub_name in ("Cache", "Caches", "cache"):
                sub_path = os.path.join(path, sub_name)
                if (
                    not os.path.isdir(sub_path)
                    or _is_link_or_junction(sub_path)
                    or path_is_covered(sub_path, covered_paths)
                ):
                    continue
                size_mb = get_size_mb(sub_path)
                if size_mb >= threshold_mb:
                    results.append(
                        _build_generic_entry(
                            label=f"Cache: {entry}",
                            path=sub_path,
                            size_mb=size_mb,
                            safe=True,
                            description=f"Discovered Windows app cache ({sub_path})",
                        )
                    )
            continue

        size_mb = get_size_mb(path)
        if size_mb < threshold_mb:
            continue

        # Under macOS ~/Library/Caches, every non-system bundle cache is a cache root;
        # under ~/.cache we retain name-hint classification (safe vs review).
        safe = True if system_name == "Darwin" else is_generic_cache_safe(path)
        results.append(
            _build_generic_entry(
                label=f"Cache: {entry}",
                path=path,
                size_mb=size_mb,
                safe=safe,
                description=f"Discovered cache directory ({path})",
            )
        )

    return results


def _discover_electron_caches_in_root(
    config_root: str,
    get_size_mb: Callable[[str], float],
    threshold_mb: int,
    covered_paths: set[str],
) -> list[ServiceDataInfo]:
    from .service_scanner import ServiceType

    if not os.path.isdir(config_root):
        return []

    results: list[ServiceDataInfo] = []
    seen_local: set[str] = set()
    for app_dir in sorted(glob.glob(os.path.join(config_root, "*"))):
        app_name = os.path.basename(app_dir)
        if (
            app_name in SKIP_ELECTRON_APP_DIRS
            or not os.path.isdir(app_dir)
            or _is_link_or_junction(app_dir)
        ):
            continue

        for cache_name in ELECTRON_CACHE_DIR_NAMES:
            # Electron apps store caches either directly under <App>/<CacheName>
            # (macOS/Windows Roaming) or under <App>/<Profile>/<CacheName>.
            candidates = [
                os.path.join(app_dir, cache_name),
                *glob.glob(os.path.join(app_dir, "*", cache_name)),
            ]
            for path in candidates:
                if (
                    not os.path.isdir(path)
                    or _is_link_or_junction(path)
                    or path in seen_local
                    or path_is_covered(path, covered_paths)
                ):
                    continue
                seen_local.add(path)

                size_mb = get_size_mb(path)
                if size_mb < threshold_mb:
                    continue

                results.append(
                    _build_generic_entry(
                        label=f"{app_name} cache",
                        path=path,
                        size_mb=size_mb,
                        safe=True,
                        description=f"Electron/Chromium cache for {app_name}",
                        service_type=ServiceType.ELECTRON,
                    )
                )

    return results


def _build_generic_entry(
    *,
    label: str,
    path: str,
    size_mb: float,
    safe: bool,
    description: str,
    service_type: ServiceType | None = None,
) -> ServiceDataInfo:
    from .service_cleanup import ServiceCleaner
    from .service_scanner import RiskLevel, ServiceDataInfo, ServiceType

    if service_type is None:
        service_type = ServiceType.GENERIC_CACHE
    size_gb = size_mb / 1024
    cleanup_command = ServiceCleaner.get_cleanup_command(service_type, path)
    risk_level = RiskLevel.SAFE.value if safe else RiskLevel.REVIEW.value
    return ServiceDataInfo(
        service_type=service_type,
        name=label,
        path=path,
        size_mb=round(size_mb, 2),
        size_gb=round(size_gb, 3),
        description=description,
        can_cleanup=True,
        cleanup_command=cleanup_command,
        preview_command=ServiceCleaner.get_preview_command(service_type, path),
        safe_to_cleanup=safe,
        impact="high" if size_gb > 1.0 else "medium",
        details={"discovered": True, "source": "cache_discovery"},
        risk_level=risk_level,
    )
