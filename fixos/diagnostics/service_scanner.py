"""
Service Data Scanner for fixOS
Scans data from various services (Docker, Ollama, etc.) and allows cleanup

Refactored: Now uses ServiceDetailsProvider and ServiceCleaner for detailed operations.
"""

import glob
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from ..constants import SERVICE_SCAN_THRESHOLD_MB
from .native_scan import measure_tree
from .service_cleanup import ServiceCleaner
from .service_details import ServiceDetailsProvider


class ServiceType(Enum):
    """Service types that can be scanned and cleaned."""

    DOCKER = "docker"
    OLLAMA = "ollama"
    CONTAINERD = "containerd"
    PODMAN = "podman"
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"
    PIP = "pip"
    CONDA = "conda"
    POETRY = "poetry"
    GRADLE = "gradle"
    MAVEN = "maven"
    CARGO = "cargo"
    GO = "go"
    FLUTTER = "flutter"
    DART = "dart"
    ANDROID = "android"
    SNAP = "snap"
    FLATPAK = "flatpak"
    APPIMAGE = "appimage"
    VAGRANT = "vagrant"
    VBOX = "virtualbox"
    VMWARE = "vmware"
    NIX = "nix"
    BREW = "brew"
    APT = "apt"
    DNF = "dnf"
    PACMAN = "pacman"
    YUM = "yum"
    ZYPPER = "zypper"
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    VSCODE = "vscode"
    JETBRAINS = "jetbrains"
    CURSOR = "cursor"
    HUGGINGFACE = "huggingface"
    AWS = "aws"
    GCLOUD = "gcloud"
    AZURE = "azure"
    TERRAFORM = "terraform"
    PULUMI = "pulumi"
    UNITY = "unity"
    UNREAL = "unreal"
    JUPYTER = "jupyter"
    THUMBNAILS = "thumbnails"
    TRASH = "trash"
    LOGS = "logs"
    NVIDIA = "nvidia"
    UV = "uv"
    TORCH = "torch"
    BUN = "bun"
    PLAYWRIGHT = "playwright"
    CCACHE = "ccache"
    HELM = "helm"
    MINIKUBE = "minikube"
    STEAM = "steam"
    LMSTUDIO = "lmstudio"
    BRAVE = "brave"
    DISCORD = "discord"
    SLACK = "slack"
    SPOTIFY = "spotify"
    BAZEL = "bazel"
    GH = "gh"
    ELECTRON = "electron"
    GENERIC_CACHE = "generic_cache"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """How risky it is to delete a scanned service's data.

    SAFE      – rebuildable cache (package/build caches, browser caches, ...).
    REVIEW    – recoverable but worth a look before deleting (reinstallable
                apps, long-unused tool data, unrecognized cache dirs).
    DANGEROUS – real installed application data (models, containers, VM
                disks, editor extensions) that is not a simple cache and may
                not be trivially recoverable. Never auto-selected for bulk
                cleanup and always requires an explicit, individual action.
    """

    SAFE = "safe"
    REVIEW = "review"
    DANGEROUS = "dangerous"


@dataclass(frozen=True)
class PathMeasurement:
    """Outcome of measuring a single filesystem path."""

    size_mb: float
    complete: bool = True
    errors: tuple[str, ...] = ()
    source: str = ""


@dataclass
class ServiceDataInfo:
    """Information about service data."""

    service_type: ServiceType
    name: str
    path: str
    size_mb: float
    size_gb: float
    description: str
    can_cleanup: bool
    cleanup_command: str
    preview_command: str
    safe_to_cleanup: bool
    impact: str = "medium"
    items_count: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    risk_level: str = RiskLevel.REVIEW.value


class ServiceDataScanner:
    """Scans for large service data directories and allows cleanup."""

    DEFAULT_THRESHOLD_MB = SERVICE_SCAN_THRESHOLD_MB

    SERVICE_PATHS: ClassVar[dict[ServiceType, list[str]]] = {
        ServiceType.DOCKER: ["/var/lib/docker", "~/.docker"],
        ServiceType.OLLAMA: [
            "~/.ollama/models",
            "~/.ollama/blobs",
            "/usr/share/ollama/.ollama/models",
        ],
        ServiceType.CONTAINERD: ["/var/lib/containerd", "/run/containerd"],
        ServiceType.PODMAN: ["~/.local/share/containers", "~/.config/containers"],
        ServiceType.NPM: [
            "~/.npm/_cacache",
            "~/.npm/_npx",
            "~/.npm/_prebuilds",
            "~/.cache/npm",
        ],
        ServiceType.YARN: ["~/.cache/yarn", "~/.yarn/berry/cache"],
        ServiceType.PNPM: ["~/.pnpm-store", "~/.local/share/pnpm/store"],
        ServiceType.PIP: ["~/.cache/pip"],
        ServiceType.CONDA: [
            "~/miniconda3/pkgs",
            "~/anaconda3/pkgs",
            "~/.conda/pkgs",
            "~/miniconda3/envs/*/pkgs",
            "~/anaconda3/envs/*/pkgs",
        ],
        # Only package caches: ~/.cache/pypoetry/virtualenvs holds real environments.
        ServiceType.POETRY: ["~/.cache/pypoetry/cache", "~/.cache/pypoetry/artifacts"],
        ServiceType.GRADLE: ["~/.gradle", "~/.cache/gradle"],
        ServiceType.MAVEN: ["~/.m2/repository"],
        ServiceType.CARGO: ["~/.cargo/registry", "~/.cargo/git"],
        ServiceType.GO: ["~/go/pkg", "~/.go/pkg"],
        ServiceType.FLUTTER: ["~/.flutter-sdk", "~/flutter", "~/.pub-cache"],
        ServiceType.DART: ["~/.pub-cache"],
        ServiceType.ANDROID: ["~/Android/Sdk", "~/.android"],
        ServiceType.SNAP: [
            "/var/lib/snapd/snaps",
            "/var/snap",
            "/var/lib/snapd/cache",
        ],
        ServiceType.FLATPAK: ["~/.local/share/flatpak", "/var/lib/flatpak"],
        ServiceType.APPIMAGE: ["~/.local/share/AppImage", "~/.cache/AppImage"],
        ServiceType.APT: ["/var/cache/apt/archives"],
        ServiceType.DNF: ["/var/cache/dnf"],
        ServiceType.YUM: ["/var/cache/yum"],
        ServiceType.PACMAN: ["/var/cache/pacman/pkg"],
        ServiceType.ZYPPER: ["/var/cache/zypp"],
        ServiceType.VAGRANT: ["~/.vagrant.d", "~/VirtualBox VMs"],
        ServiceType.VBOX: ["~/VirtualBox VMs", "~/.config/VirtualBox"],
        ServiceType.VMWARE: ["~/vmware", "~/Virtual Machines"],
        ServiceType.NIX: ["~/.nix-profile", "~/.nix-defexpr", "/nix"],
        ServiceType.BREW: ["~/homebrew", "/usr/local/Homebrew", "/opt/homebrew"],
        ServiceType.CHROME: [
            "~/.cache/google-chrome",
            "~/.config/google-chrome/*/Cache",
            "~/.config/google-chrome/*/Code Cache",
            "~/.config/google-chrome/*/GPUCache",
            "~/.config/google-chrome/*/DawnCache",
            "~/.config/google-chrome/*/GrShaderCache",
            "~/.config/google-chrome/*/ShaderCache",
            "~/.config/google-chrome/*/Service Worker",
        ],
        # Flatpak builds keep XDG_CACHE_HOME under ~/.var/app/<app-id>/cache.
        ServiceType.FIREFOX: [
            "~/.cache/mozilla",
            "~/.mozilla/firefox/*/cache2",
            "~/.var/app/org.mozilla.firefox/cache/mozilla",
        ],
        ServiceType.EDGE: [
            "~/.cache/microsoft-edge",
            "~/.var/app/com.microsoft.Edge/cache/microsoft-edge",
        ],
        ServiceType.VSCODE: ["~/.vscode/extensions", "~/.config/Code/Cache"],
        ServiceType.CURSOR: [
            "~/.config/Cursor/Cache",
            "~/.config/Cursor/CachedData",
            "~/.config/Cursor/CachedExtensionVSIXs",
            "~/.config/Cursor/logs",
            "~/.cursor/extensions",
        ],
        ServiceType.JETBRAINS: [
            "~/.cache/JetBrains",
            "~/.local/share/JetBrains/*/caches",
            "~/.local/share/JetBrains/*/index",
        ],
        ServiceType.HUGGINGFACE: ["~/.cache/huggingface"],
        ServiceType.AWS: ["~/.aws/sso/cache", "~/.aws/cli/cache"],
        ServiceType.GCLOUD: ["~/.config/gcloud/logs", "~/.cache/gcloud"],
        ServiceType.AZURE: ["~/.azure/telemetry", "~/.azure/logs"],
        ServiceType.TERRAFORM: ["~/.terraform.d/plugin-cache"],
        ServiceType.PULUMI: ["~/.pulumi/plugins"],
        ServiceType.UNITY: ["~/.config/unity3d", "~/.cache/unity3d"],
        ServiceType.UNREAL: ["~/.config/Epic"],
        ServiceType.JUPYTER: ["~/.local/share/jupyter"],
        ServiceType.THUMBNAILS: ["~/.cache/thumbnails", "~/.thumbnails"],
        ServiceType.TRASH: ["~/.local/share/Trash", "~/.Trash"],
        # Not ~/.local/state: XDG state holds application data (history,
        # agent artifacts), and the logs command only removes old *.log files.
        ServiceType.LOGS: ["~/.cache/log"],
        ServiceType.NVIDIA: [
            "~/.cache/nvidia",
            "~/.nv/ComputeCache",
            "~/.cache/mesa_shader_cache",
        ],
        ServiceType.UV: ["~/.cache/uv"],
        ServiceType.TORCH: ["~/.cache/torch", "~/.torch"],
        ServiceType.BUN: ["~/.bun/install/cache"],
        ServiceType.PLAYWRIGHT: ["~/.cache/ms-playwright", "~/.cache/puppeteer"],
        ServiceType.CCACHE: ["~/.ccache", "~/.cache/sccache"],
        ServiceType.HELM: ["~/.cache/helm"],
        ServiceType.MINIKUBE: ["~/.minikube"],
        ServiceType.STEAM: [
            "~/.local/share/Steam/steamapps/shadercache",
            "~/.local/share/Steam/appcache",
            "~/.local/share/Steam",
            "~/.steam",
        ],
        ServiceType.LMSTUDIO: [
            "~/.cache/lm-studio",
            "~/.lmstudio/models",
            "~/.lmstudio/.internal/cache",
        ],
        ServiceType.BRAVE: [
            "~/.cache/BraveSoftware",
            "~/.config/BraveSoftware/Brave-Browser/*/Cache",
            "~/.config/BraveSoftware/Brave-Browser/*/Code Cache",
            "~/.config/BraveSoftware/Brave-Browser/*/GPUCache",
        ],
        ServiceType.DISCORD: [
            "~/.config/discord/Cache",
            "~/.config/discord/Code Cache",
            "~/.config/discord/GPUCache",
        ],
        ServiceType.SLACK: [
            "~/.config/Slack/Cache",
            "~/.config/Slack/Code Cache",
            "~/.config/Slack/Service Worker",
        ],
        ServiceType.SPOTIFY: ["~/.cache/spotify", "~/.config/spotify/Data"],
        ServiceType.BAZEL: ["~/.cache/bazel"],
        ServiceType.GH: ["~/.cache/gh"],
    }

    _SKIP_ENUM_SCAN = frozenset(
        {ServiceType.UNKNOWN, ServiceType.GENERIC_CACHE, ServiceType.ELECTRON}
    )

    def __init__(self, threshold_mb: int | None = None):
        self.threshold_mb = (
            self.DEFAULT_THRESHOLD_MB if threshold_mb is None else threshold_mb
        )
        self.threshold_gb = self.threshold_mb / 1024
        self._details_provider = ServiceDetailsProvider()
        self._cleaner = ServiceCleaner(self)
        self._docker_usage_cache: dict[str, Any] | None = None
        self._docker_usage_failed = False
        self._docker_usage_timed_out = False
        self.scan_warnings: list[str] = []
        self._path_measurements: dict[str, PathMeasurement] = {}

    @staticmethod
    def _is_incomplete_or_error(info: ServiceDataInfo) -> bool:
        details = info.details or {}
        return bool(
            details.get("size_unknown")
            or details.get("measurement_incomplete")
            or details.get("error")
            or details.get("measurement_errors")
        )

    @staticmethod
    def _has_measurement_failure(info: ServiceDataInfo) -> bool:
        details = info.details or {}
        return bool(
            details.get("measurement_incomplete")
            or details.get("error")
            or details.get("measurement_errors")
        )

    def scan_all_services(self) -> list[ServiceDataInfo]:
        """Scan all known services for data above threshold."""
        from .cache_discovery import discover_additional_caches

        results: list[ServiceDataInfo] = []
        for service_type in ServiceType:
            if service_type in self._SKIP_ENUM_SCAN:
                continue
            service_data = self.scan_service(service_type)
            results.extend(service_data)

        covered_paths = self._collect_covered_paths(results)
        results.extend(
            discover_additional_caches(
                self._get_path_size_mb, self.threshold_mb, covered_paths
            )
        )
        results.sort(key=lambda x: x.size_mb, reverse=True)
        return results

    def _collect_covered_paths(self, results: list[ServiceDataInfo]) -> set[str]:
        """Paths already represented by dedicated service scanners."""
        covered: set[str] = set()
        for result in results:
            covered.add(result.path)
            for path in result.details.get("paths", []):
                covered.add(path)

        for paths in self.SERVICE_PATHS.values():
            for pattern in paths:
                expanded = os.path.expanduser(pattern)
                for path in glob.glob(expanded) or [expanded]:
                    covered.add(path)
        return covered

    def scan_service(self, service_type: ServiceType) -> list[ServiceDataInfo]:
        """Scan specific service type for data."""
        results = []
        paths = self.SERVICE_PATHS.get(service_type, [])
        for path_pattern in paths:
            expanded_path = os.path.expanduser(path_pattern)
            matching_paths = glob.glob(expanded_path) or [expanded_path]
            for path in matching_paths:
                if os.path.exists(path):
                    info = self._analyze_service_path(service_type, path)
                    # An unmeasurable or incomplete entry (slow Docker daemon,
                    # permission error, or analysis failure) must stay visible
                    # instead of being silently dropped by threshold filtering.
                    if info and (
                        info.size_mb >= self.threshold_mb
                        or self._is_incomplete_or_error(info)
                    ):
                        results.append(info)
        if len(results) > 1:
            return self._merge_by_risk(results)
        return results

    def _merge_by_risk(self, results: list[ServiceDataInfo]) -> list[ServiceDataInfo]:
        """Merge same-service paths, but never blend risk tiers together.

        A pure cache dir (e.g. Cursor's ``Cache``) and a directory holding
        real installed data (e.g. Cursor's ``extensions``) must stay separate
        so the risky one is never hidden inside a "safe" summary entry.
        """
        groups: dict[str, list[ServiceDataInfo]] = {}
        for item in results:
            groups.setdefault(item.risk_level, []).append(item)

        merged = [
            items[0] if len(items) == 1 else self._merge_service_entries(items)
            for items in groups.values()
        ]
        merged.sort(key=lambda item: item.size_mb, reverse=True)
        return merged

    def _merge_service_entries(self, results: list[ServiceDataInfo]) -> ServiceDataInfo:
        """Combine multiple same-risk paths for a service into one summary entry."""
        primary = max(results, key=lambda item: item.size_mb)
        total_mb = sum(item.size_mb for item in results)
        paths = [item.path for item in results]
        any_size_unknown = any(
            bool((item.details or {}).get("size_unknown")) for item in results
        )
        any_failure = any(self._has_measurement_failure(item) for item in results)
        incomplete_paths = [
            item.path for item in results if self._is_incomplete_or_error(item)
        ]
        merged_errors: list[str] = []
        for item in results:
            details = item.details or {}
            for err in details.get("measurement_errors") or ():
                text = str(err)
                if text and text not in merged_errors:
                    merged_errors.append(text)
            if details.get("error"):
                text = str(details["error"])
                if text and text not in merged_errors:
                    merged_errors.append(text)

        merged_details: dict[str, Any] = {
            **primary.details,
            "paths": paths,
            "merged_count": len(results),
        }
        if any_size_unknown:
            merged_details["size_unknown"] = True
        if any_failure:
            merged_details["measurement_incomplete"] = True
            merged_details["incomplete_paths"] = incomplete_paths
            if merged_errors:
                merged_details["measurement_errors"] = merged_errors
                merged_details["error"] = merged_errors[0]

        can_cleanup = all(item.can_cleanup for item in results) and not any_failure
        cleanup_command = primary.cleanup_command if can_cleanup else ""
        safe_to_cleanup = (
            all(item.safe_to_cleanup for item in results) and not any_size_unknown
        )

        return ServiceDataInfo(
            service_type=primary.service_type,
            name=primary.name,
            path=primary.path,
            size_mb=round(total_mb, 2),
            size_gb=round(total_mb / 1024, 3),
            description=primary.description,
            can_cleanup=can_cleanup,
            cleanup_command=cleanup_command,
            preview_command=primary.preview_command,
            safe_to_cleanup=safe_to_cleanup,
            impact="high" if total_mb / 1024 > 1.0 else "medium",
            items_count=primary.items_count,
            details=merged_details,
            risk_level=primary.risk_level,
        )

    def _analyze_service_path(
        self, service_type: ServiceType, path: str
    ) -> ServiceDataInfo | None:
        """Analyze a specific service path."""
        try:
            self._path_measurements.pop(path, None)
            size_mb = self.measure_service_size_mb(service_type, path)
            measurement = self._path_measurements.get(path)

            if service_type == ServiceType.DOCKER and path == "/var/lib/docker":
                # /var/lib/docker is normally root-only (0710), so `du` sees
                # "permission denied" and silently reports ~0 here even when
                # Docker holds tens/hundreds of GB. Ask the daemon directly
                # instead — it works regardless of filesystem permissions.
                daemon_size_mb = self._get_docker_daemon_size_mb()
                if daemon_size_mb and daemon_size_mb > size_mb:
                    size_mb = daemon_size_mb
                if daemon_size_mb is not None:
                    measurement = PathMeasurement(
                        size_mb=size_mb,
                        complete=True,
                        errors=(),
                        source="docker-system-df",
                    )
                elif self._docker_usage_timed_out:
                    return self._docker_unknown_size_service(path)

            is_incomplete = measurement is not None and not measurement.complete
            size_gb = size_mb / 1024
            if not is_incomplete and size_mb < self.threshold_mb:
                return None
            if service_type == ServiceType.DOCKER and self._docker_usage_cache:
                details = self._docker_usage_details(self._docker_usage_cache)
            else:
                details = self._details_provider.get_details(service_type, path)
            risk_level = ServiceCleaner.get_risk_level(service_type, path)
            cleanup_command = ServiceCleaner.get_cleanup_command(service_type, path)
            name = service_type.value.title()
            if (
                service_type in (ServiceType.CURSOR, ServiceType.VSCODE)
                and os.path.basename(path.rstrip("/")) == "extensions"
            ):
                name = f"{name} Extensions"
            if is_incomplete:
                errors = list(measurement.errors) or [
                    f"{path}: incomplete storage measurement"
                ]
                warning = (
                    f"{name} ({path}): niepełny pomiar "
                    f"({measurement.source or 'scan'}): {errors[0]}"
                )
                if warning not in self.scan_warnings:
                    self.scan_warnings.append(warning)
                effective_risk = (
                    RiskLevel.REVIEW.value
                    if risk_level == RiskLevel.SAFE.value
                    else risk_level
                )
                return ServiceDataInfo(
                    service_type=service_type,
                    name=name,
                    path=path,
                    size_mb=round(size_mb, 2),
                    size_gb=round(size_gb, 3),
                    description=(
                        f"{ServiceCleaner.get_service_description(service_type)} "
                        "(niepełny pomiar)"
                    ),
                    can_cleanup=False,
                    cleanup_command="",
                    preview_command=ServiceCleaner.get_preview_command(
                        service_type, path
                    ),
                    safe_to_cleanup=False,
                    impact="high" if size_gb > 1.0 else "medium",
                    items_count=details.get("items_count"),
                    details={
                        **details,
                        "size_unknown": True,
                        "measurement_incomplete": True,
                        "measurement_errors": errors,
                        "measurement_source": measurement.source,
                        "observed_partial_size_mb": round(size_mb, 2),
                        "error": errors[0],
                    },
                    risk_level=effective_risk,
                )
            return ServiceDataInfo(
                service_type=service_type,
                name=name,
                path=path,
                size_mb=round(size_mb, 2),
                size_gb=round(size_gb, 3),
                description=ServiceCleaner.get_service_description(service_type),
                can_cleanup=bool(cleanup_command),
                cleanup_command=cleanup_command,
                preview_command=ServiceCleaner.get_preview_command(service_type, path),
                safe_to_cleanup=risk_level == RiskLevel.SAFE.value,
                impact="high" if size_gb > 1.0 else "medium",
                items_count=details.get("items_count"),
                details=details,
                risk_level=risk_level,
            )
        except Exception as e:  # noqa: BLE001 - one bad path must not abort the whole scan
            warning = f"{service_type.value.title()} ({path}): błąd analizy pomiaru: {e!s}"
            if warning not in self.scan_warnings:
                self.scan_warnings.append(warning)
            return ServiceDataInfo(
                service_type=service_type,
                name=service_type.value.title(),
                path=path,
                size_mb=0,
                size_gb=0,
                description=f"Error analyzing: {e!s}",
                can_cleanup=False,
                cleanup_command="",
                preview_command="",
                safe_to_cleanup=False,
                impact="none",
                details={
                    "error": str(e),
                    "size_unknown": True,
                    "measurement_incomplete": True,
                    "measurement_errors": [str(e)],
                },
                risk_level=RiskLevel.REVIEW.value,
            )

    def _measure_path_mb(self, path: str) -> PathMeasurement:
        """Measure path size while preserving incomplete-scan and error state."""
        p = Path(path)
        try:
            is_file = p.is_file()
            is_dir = p.is_dir()
        except OSError as exc:
            return PathMeasurement(
                size_mb=0.0, complete=False, errors=(f"{path}: {exc}",), source="stat"
            )

        if is_file:
            try:
                return PathMeasurement(
                    size_mb=p.stat().st_size / (1024 * 1024),
                    complete=True,
                    errors=(),
                    source="stat",
                )
            except OSError as exc:
                return PathMeasurement(
                    size_mb=0.0,
                    complete=False,
                    errors=(f"{path}: {exc}",),
                    source="stat",
                )

        if is_dir:
            try:
                m = measure_tree(p, native=True)
                if (
                    isinstance(m, dict)
                    and "bytes" in m
                    and isinstance(m["bytes"], (int, float))
                    and not isinstance(m["bytes"], bool)
                    and m["bytes"] >= 0
                ):
                    raw_errors = m.get("errors")
                    errors = (
                        tuple(str(err) for err in raw_errors if str(err))
                        if isinstance(raw_errors, list)
                        else ()
                    )
                    complete = (m.get("complete") is not False) and (
                        raw_errors is None
                        or (isinstance(raw_errors, list) and len(errors) == 0)
                    )
                    size_mb = float(m["bytes"]) / (1024 * 1024)
                    if complete:
                        return PathMeasurement(
                            size_mb=size_mb,
                            complete=True,
                            errors=(),
                            source="measure_tree",
                        )
                    return PathMeasurement(
                        size_mb=size_mb,
                        complete=False,
                        errors=errors or (f"{path}: incomplete measure_tree result",),
                        source="measure_tree",
                    )
            except (OSError, ValueError, TypeError, subprocess.SubprocessError):
                pass

        du_error: str | None = None
        try:
            result = subprocess.run(
                ["du", "-sk", "--", path],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            stdout = (result.stdout or "").strip()
            if result.returncode == 0 and stdout:
                kb = int(stdout.splitlines()[-1].split()[0])
                return PathMeasurement(
                    size_mb=kb / 1024, complete=True, errors=(), source="du"
                )
            if result.returncode != 0:
                stderr_detail = (
                    result.stderr or ""
                ).strip() or f"du exited with status {result.returncode}"
                du_error = f"{path}: {stderr_detail}"
                # du exits 1 when a subdirectory is unreadable but still prints
                # the readable total; keep the total while marking incomplete.
                if stdout:
                    kb = int(stdout.splitlines()[-1].split()[0])
                    return PathMeasurement(
                        size_mb=kb / 1024,
                        complete=False,
                        errors=(du_error,),
                        source="du",
                    )
        except (OSError, ValueError, subprocess.TimeoutExpired, IndexError) as exc:
            du_error = f"{path}: {exc}"

        total_size = 0
        if os.path.isfile(path):
            try:
                return PathMeasurement(
                    size_mb=os.path.getsize(path) / (1024 * 1024),
                    complete=True,
                    errors=(),
                    source="stat",
                )
            except OSError as exc:
                return PathMeasurement(
                    size_mb=0.0,
                    complete=False,
                    errors=(f"{path}: {exc}",),
                    source="stat",
                )

        walk_errors: list[str] = []
        try:
            root_dev = os.stat(path).st_dev if os.path.exists(path) else None
            for dirpath, dirnames, filenames in os.walk(
                path,
                onerror=lambda exc: walk_errors.append(
                    f"{getattr(exc, 'filename', path) or path}: {exc}"
                ),
            ):
                if root_dev is not None:
                    kept_dirs: list[str] = []
                    for name in dirnames:
                        child = os.path.join(dirpath, name)
                        if self._should_descend(child, root_dev):
                            kept_dirs.append(name)
                        else:
                            try:
                                os.stat(child)
                            except OSError as exc:
                                walk_errors.append(f"{child}: {exc}")
                    dirnames[:] = kept_dirs
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except OSError as exc:
                        walk_errors.append(f"{filepath}: {exc}")
        except OSError as exc:
            walk_errors.append(f"{path}: {exc}")

        if walk_errors:
            return PathMeasurement(
                size_mb=total_size / (1024 * 1024),
                complete=False,
                errors=tuple(walk_errors),
                source="os.walk",
            )
        if du_error and not os.path.exists(path):
            return PathMeasurement(
                size_mb=0.0, complete=False, errors=(du_error,), source="du"
            )
        return PathMeasurement(
            size_mb=total_size / (1024 * 1024),
            complete=True,
            errors=(),
            source="os.walk",
        )

    def _get_path_size_mb(self, path: str) -> float:
        """Get size of path in MB using native measure_tree, falling back to du / os.walk."""
        measurement = self._measure_path_mb(path)
        self._path_measurements[path] = measurement
        return measurement.size_mb

    def measure_service_size_mb(
        self, service_type: ServiceType, path: str, *, refresh: bool = False
    ) -> float:
        """Measure a service with the same source before and after cleanup.

        Root-owned Docker storage cannot be measured reliably with an
        unprivileged ``du``.  Using the daemon here also prevents cleanup from
        falsely reporting that the whole Docker directory was freed when the
        post-cleanup ``du`` returned zero due to permissions.
        """
        self._path_measurements.pop(path, None)
        if service_type == ServiceType.DOCKER and path == "/var/lib/docker":
            daemon_size = (
                self._get_docker_daemon_size_mb(refresh=True)
                if refresh
                else self._get_docker_daemon_size_mb()
            )
            if daemon_size is not None:
                self._path_measurements[path] = PathMeasurement(
                    size_mb=daemon_size,
                    complete=True,
                    errors=(),
                    source="docker-system-df",
                )
                return daemon_size
        return self._get_path_size_mb(path)

    def _docker_unknown_size_service(self, path: str) -> ServiceDataInfo:
        """Keep Docker reviewable when the daemon is too slow to size it.

        On a full or busy disk ``docker system df`` can exceed its timeout,
        which is exactly when Docker is most likely to hold reclaimable data.
        The entry carries no size claim and only the bounded build-cache prune.
        """
        cleanup_command = ServiceCleaner.get_cleanup_command(ServiceType.DOCKER, path)
        return ServiceDataInfo(
            service_type=ServiceType.DOCKER,
            name="Docker",
            path=path,
            size_mb=0.0,
            size_gb=0.0,
            description=ServiceCleaner.get_service_description(ServiceType.DOCKER),
            can_cleanup=bool(cleanup_command),
            cleanup_command=cleanup_command,
            preview_command=ServiceCleaner.get_preview_command(ServiceType.DOCKER, path),
            safe_to_cleanup=False,
            impact="high",
            details={
                "size_unknown": True,
                "reason": "docker_system_df_timeout",
                "fast_inventory": self._docker_fast_inventory(),
            },
            risk_level=ServiceCleaner.get_risk_level(ServiceType.DOCKER, path),
        )

    @staticmethod
    def _docker_fast_inventory(timeout_s: float = 10.0) -> dict[str, Any]:
        """Counts and build-cache size from Docker commands that stay fast.

        ``docker system df`` walks every volume to size it; with hundreds of
        volumes it can take minutes even on an idle host.  Listing objects and
        ``docker builder du`` answer in well under a second, so a timed-out
        scan can still show where Docker holds data.  Volume sizes stay
        unknown; orphaned volumes are data and are only counted.
        """

        def lines(*args: str) -> list[str] | None:
            try:
                result = subprocess.run(
                    ["docker", *args],
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                return None
            if result.returncode != 0:
                return None
            return [line for line in result.stdout.splitlines() if line.strip()]

        inventory: dict[str, Any] = {}
        queries = {
            "images": ("image", "ls", "-q", "--no-trunc"),
            "dangling_images": ("image", "ls", "-q", "--no-trunc", "-f", "dangling=true"),
            "containers": ("ps", "-aq"),
            "stopped_containers": ("ps", "-aq", "-f", "status=exited"),
            "volumes": ("volume", "ls", "-q"),
            "dangling_volumes": ("volume", "ls", "-q", "-f", "dangling=true"),
        }
        for key, args in queries.items():
            found = lines(*args)
            if found is not None:
                inventory[key] = len(set(found))

        builder = lines("builder", "du")
        if builder is not None:
            for line in builder:
                label, _, value = line.partition(":")
                label = label.strip().lower()
                if label in ("total", "reclaimable") and value.strip():
                    size_mb = ServiceDataScanner._parse_human_size_to_mb(value.strip())
                    inventory[f"build_cache_{label}_gb"] = round(size_mb / 1024, 3)
        return inventory

    def _get_docker_daemon_size_mb(self, *, refresh: bool = False) -> float | None:
        """Total Docker disk usage as reported by the daemon itself."""
        usage = self._get_docker_daemon_usage(refresh=refresh)
        if usage is None:
            return None
        return float(usage["size_mb"])

    def _get_docker_daemon_usage(
        self, *, refresh: bool = False
    ) -> dict[str, Any] | None:
        """Return one stable Docker usage snapshot.

        Asking the daemon (``docker system df``) works even when the caller
        can't read /var/lib/docker directly (typically root-only, mode 0710).
        Docker can take tens of seconds with thousands of images, so one
        snapshot is cached for the whole scan and reused for details/counts.
        A failed probe is cached too, so a slow daemon costs one timeout per
        scan, and is reported in ``scan_warnings`` instead of silently hiding
        Docker from the plan.
        """
        if not refresh:
            if self._docker_usage_cache is not None:
                return self._docker_usage_cache
            if self._docker_usage_failed:
                return None

        timeout_s = int(os.environ.get("FIXOS_DOCKER_TIMEOUT", "5"))
        self._docker_usage_failed = True
        self._docker_usage_timed_out = False
        try:
            result = subprocess.run(
                ["docker", "system", "df", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self._docker_usage_timed_out = True
            self.scan_warnings.append(
                f"Docker: `docker system df` nie odpowiedział w {timeout_s} s — "
                "rozmiar Dockera nieznany; ograniczony prune cache buildów nadal "
                "jest dostępny do świadomego wyboru."
            )
            return None
        except OSError:
            return None

        if result.returncode != 0:
            reason = (result.stderr or "").strip().splitlines()[:1]
            self.scan_warnings.append(
                "Docker: `docker system df` zakończył się błędem"
                f"{': ' + reason[0] if reason else ''} — dane Dockera pominięto w raporcie."
            )
            return None
        if not result.stdout.strip():
            return None

        rows: dict[str, dict[str, Any]] = {}
        total_mb = 0.0
        reclaimable_mb = 0.0
        for line in result.stdout.strip().splitlines():
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            kind = str(row.get("Type", "")).strip()
            if not kind:
                continue
            size_mb = self._parse_human_size_to_mb(str(row.get("Size", "0B")))
            reclaimable_text = str(row.get("Reclaimable", "0B")).split("(", 1)[0]
            row_reclaimable_mb = self._parse_human_size_to_mb(reclaimable_text)
            total_mb += size_mb
            reclaimable_mb += row_reclaimable_mb
            rows[kind] = {
                "total": self._parse_int(row.get("TotalCount")),
                "active": self._parse_int(row.get("Active")),
                "size_mb": round(size_mb, 2),
                "size_gb": round(size_mb / 1024, 3),
                "reclaimable_mb": round(row_reclaimable_mb, 2),
                "reclaimable_gb": round(row_reclaimable_mb / 1024, 3),
            }

        if total_mb <= 0:
            return None

        self._docker_usage_cache = {
            "size_mb": round(total_mb, 2),
            "size_gb": round(total_mb / 1024, 3),
            "reclaimable_mb": round(reclaimable_mb, 2),
            "reclaimable_gb": round(reclaimable_mb / 1024, 3),
            "rows": rows,
        }
        self._docker_usage_failed = False
        self._docker_usage_timed_out = False
        self._persist_docker_usage(self._docker_usage_cache)
        return self._docker_usage_cache

    @staticmethod
    def _persist_docker_usage(usage: dict[str, Any]) -> None:
        """Make an expensive Docker measurement reusable by the quick path."""
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        path = cache_root / "fixos" / "docker-usage.json"
        tmp_name = ""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "generated_at": datetime.now().astimezone().isoformat(),
                "usage": usage,
            }
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=path.parent, delete=False
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False)
                tmp_name = handle.name
            os.replace(tmp_name, path)
        except OSError:
            pass
        finally:
            if tmp_name:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _docker_usage_details(usage: dict[str, Any]) -> dict[str, Any]:
        rows = usage.get("rows", {})
        return {
            "items_count": sum(int(row.get("total", 0)) for row in rows.values()),
            "components": {
                kind.lower().replace(" ", "_"): int(row.get("total", 0))
                for kind, row in rows.items()
            },
            "usage": rows,
            "reclaimable_size_mb": usage.get("reclaimable_mb", 0.0),
            "reclaimable_size_gb": usage.get("reclaimable_gb", 0.0),
            "measurement_source": "docker-system-df",
        }

    @staticmethod
    def _parse_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _parse_human_size_to_mb(value: str) -> float:
        """Parse a docker-style human size ("158.3GB", "0B", ...) to MB."""
        match = re.match(r"\s*([\d.]+)\s*([KMGTP]?B)\s*$", value, re.IGNORECASE)
        if not match:
            return 0.0
        amount = float(match.group(1))
        unit = match.group(2).upper()
        multipliers = {
            "B": 1 / 1024**2,
            "KB": 1 / 1024,
            "MB": 1,
            "GB": 1024,
            "TB": 1024**2,
        }
        return amount * multipliers.get(unit, 0.0)

    @staticmethod
    def _should_descend(path: str, root_dev: int) -> bool:
        """Skip mount points so loop-mounted snaps are not double-counted."""
        try:
            return os.stat(path).st_dev == root_dev
        except OSError:
            return False

    def get_cleanup_plan(
        self, selected_services: list[str] | None = None
    ) -> dict[str, Any]:
        """Generate cleanup plan for services."""
        return self._cleaner.get_cleanup_plan(selected_services)

    def cleanup_service(
        self,
        service_type: str,
        dry_run: bool = False,
        planned_service: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute cleanup for a specific service."""
        return self._cleaner.cleanup_service(
            service_type,
            dry_run,
            planned_service=planned_service,
        )


def main():
    """Test the service data scanner."""
    scanner = ServiceDataScanner(threshold_mb=100)
    plan = scanner.get_cleanup_plan()
    print(json.dumps(plan, indent=2, default=str))


if __name__ == "__main__":
    main()
