"""
Generic cache discovery for fixOS cleanup.

Finds large cache directories under ~/.cache and Electron app caches under
~/.config that are not already covered by known service scanners.
"""

from __future__ import annotations

import glob
import os
from typing import Callable, Iterable, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .service_scanner import ServiceDataInfo, ServiceType

from ..constants import GENERIC_CACHE_THRESHOLD_MB

# Top-level ~/.cache names already handled by dedicated ServiceType scanners.
KNOWN_CACHE_DIR_NAMES = frozenset(
    {
        "pip",
        "npm",
        "yarn",
        "pypoetry",
        "huggingface",
        "google-chrome",
        "microsoft-edge",
        "mozilla",
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
    }
)

# Electron/Chromium apps scanned explicitly elsewhere or via dedicated types.
KNOWN_CONFIG_APPS = frozenset(
    {
        "google-chrome",
        "microsoft-edge",
        "BraveSoftware",
        "Code",
        "Cursor",
        "discord",
        "Slack",
        "spotify",
    }
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
    return os.path.realpath(os.path.expanduser(path))


def path_is_covered(path: str, covered_paths: Iterable[str]) -> bool:
    """Return True when path is already represented by a known service scan."""
    normalized = normalize_path(path)
    for covered in covered_paths:
        covered_norm = normalize_path(covered)
        if normalized == covered_norm:
            return True
        if normalized.startswith(f"{covered_norm}/"):
            return True
        if covered_norm.startswith(f"{normalized}/"):
            return True
    return False


def is_generic_cache_safe(path: str) -> bool:
    """Heuristic safety check for unknown cache directories."""
    base = os.path.basename(path.rstrip("/")).lower()
    return any(hint in base for hint in GENERIC_SAFE_NAME_HINTS)


def discover_additional_caches(
    get_size_mb: Callable[[str], float],
    threshold_mb: int,
    covered_paths: Set[str],
) -> list["ServiceDataInfo"]:
    """Discover large caches not already covered by known service scanners."""
    from .service_scanner import ServiceDataInfo, ServiceType

    generic_threshold = max(threshold_mb, GENERIC_CACHE_THRESHOLD_MB)
    results: list[ServiceDataInfo] = []
    seen_paths: set[str] = set()

    for info in _discover_xdg_cache_dirs(get_size_mb, generic_threshold, covered_paths):
        norm = normalize_path(info.path)
        if norm not in seen_paths:
            seen_paths.add(norm)
            results.append(info)

    for info in _discover_electron_caches(get_size_mb, threshold_mb, covered_paths):
        norm = normalize_path(info.path)
        if norm not in seen_paths:
            seen_paths.add(norm)
            results.append(info)

    results.sort(key=lambda item: item.size_mb, reverse=True)
    return results


def _discover_xdg_cache_dirs(
    get_size_mb: Callable[[str], float],
    threshold_mb: int,
    covered_paths: Set[str],
) -> list["ServiceDataInfo"]:
    cache_root = os.path.expanduser("~/.cache")
    if not os.path.isdir(cache_root):
        return []

    results: list[ServiceDataInfo] = []
    try:
        entries = sorted(os.listdir(cache_root))
    except OSError:
        return []

    for entry in entries:
        if entry in KNOWN_CACHE_DIR_NAMES:
            continue

        path = os.path.join(cache_root, entry)
        if not os.path.isdir(path):
            continue
        if path_is_covered(path, covered_paths):
            continue

        size_mb = get_size_mb(path)
        if size_mb < threshold_mb:
            continue

        safe = is_generic_cache_safe(path)
        results.append(
            _build_generic_entry(
                label=f"Cache: {entry}",
                path=path,
                size_mb=size_mb,
                safe=safe,
                description=f"Discovered cache directory (~/.cache/{entry})",
            )
        )

    return results


def _discover_electron_caches(
    get_size_mb: Callable[[str], float],
    threshold_mb: int,
    covered_paths: Set[str],
) -> list["ServiceDataInfo"]:
    from .service_scanner import ServiceType

    config_root = os.path.expanduser("~/.config")
    if not os.path.isdir(config_root):
        return []

    results: list[ServiceDataInfo] = []
    for app_dir in sorted(glob.glob(os.path.join(config_root, "*"))):
        app_name = os.path.basename(app_dir)
        if app_name in KNOWN_CONFIG_APPS or not os.path.isdir(app_dir):
            continue

        for cache_name in ELECTRON_CACHE_DIR_NAMES:
            for path in glob.glob(os.path.join(app_dir, "*", cache_name)):
                if not os.path.isdir(path):
                    continue
                if path_is_covered(path, covered_paths):
                    continue

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
    service_type: "ServiceType" = None,
) -> "ServiceDataInfo":
    from .service_cleanup import ServiceCleaner
    from .service_scanner import ServiceDataInfo, ServiceType

    if service_type is None:
        service_type = ServiceType.GENERIC_CACHE
    size_gb = size_mb / 1024
    cleanup_command = ServiceCleaner.get_cleanup_command(service_type, path)
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
    )
