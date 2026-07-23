#!/usr/bin/env python3
"""
Service Data Scanner for fixOS
Scans data from various services (Docker, Ollama, etc.) and allows cleanup

Refactored: Now uses ServiceDetailsProvider and ServiceCleaner for detailed operations.
"""

import os
import glob
import json
import re
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .service_details import ServiceDetailsProvider
from .service_cleanup import ServiceCleaner
from ..constants import SERVICE_SCAN_THRESHOLD_MB


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
    items_count: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = RiskLevel.REVIEW.value


class ServiceDataScanner:
    """Scans for large service data directories and allows cleanup."""

    DEFAULT_THRESHOLD_MB = SERVICE_SCAN_THRESHOLD_MB

    SERVICE_PATHS = {
        ServiceType.DOCKER: ["/var/lib/docker", "~/.docker"],
        ServiceType.OLLAMA: [
            "~/.ollama/models",
            "~/.ollama/blobs",
            "/usr/share/ollama/.ollama/models",
        ],
        ServiceType.CONTAINERD: ["/var/lib/containerd", "/run/containerd"],
        ServiceType.PODMAN: ["~/.local/share/containers", "~/.config/containers"],
        ServiceType.NPM: ["~/.npm", "~/.cache/npm"],
        ServiceType.YARN: ["~/.cache/yarn", "~/.yarn", "~/.config/yarn"],
        ServiceType.PNPM: ["~/.pnpm-store", "~/.local/share/pnpm"],
        ServiceType.PIP: ["~/.cache/pip"],
        ServiceType.CONDA: [
            "~/miniconda3/pkgs",
            "~/anaconda3/pkgs",
            "~/.conda/pkgs",
            "~/miniconda3/envs/*/pkgs",
            "~/anaconda3/envs/*/pkgs",
        ],
        ServiceType.POETRY: ["~/.cache/pypoetry"],
        ServiceType.GRADLE: ["~/.gradle", "~/.cache/gradle"],
        ServiceType.MAVEN: ["~/.m2"],
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
        ServiceType.FIREFOX: ["~/.cache/mozilla", "~/.mozilla/firefox/*/cache2"],
        ServiceType.EDGE: ["~/.cache/microsoft-edge"],
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
        ServiceType.LOGS: ["~/.cache/log", "~/.local/state"],
        ServiceType.NVIDIA: [
            "~/.cache/nvidia",
            "~/.nv/ComputeCache",
            "~/.cache/mesa_shader_cache",
        ],
        ServiceType.UV: ["~/.cache/uv", "~/.local/share/uv"],
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

    def __init__(self, threshold_mb: int = None):
        self.threshold_mb = threshold_mb or self.DEFAULT_THRESHOLD_MB
        self.threshold_gb = self.threshold_mb / 1024
        self._details_provider = ServiceDetailsProvider()
        self._cleaner = ServiceCleaner(self)
        self._docker_usage_cache: Optional[Dict[str, Any]] = None

    def scan_all_services(self) -> List[ServiceDataInfo]:
        """Scan all known services for data above threshold."""
        from .cache_discovery import discover_additional_caches

        results: List[ServiceDataInfo] = []
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

    def _collect_covered_paths(self, results: List[ServiceDataInfo]) -> set[str]:
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

    def scan_service(self, service_type: ServiceType) -> List[ServiceDataInfo]:
        """Scan specific service type for data."""
        results = []
        paths = self.SERVICE_PATHS.get(service_type, [])
        for path_pattern in paths:
            expanded_path = os.path.expanduser(path_pattern)
            matching_paths = glob.glob(expanded_path) or [expanded_path]
            for path in matching_paths:
                if os.path.exists(path):
                    info = self._analyze_service_path(service_type, path)
                    if info and info.size_mb >= self.threshold_mb:
                        results.append(info)
        if len(results) > 1:
            return self._merge_by_risk(results)
        return results

    def _merge_by_risk(self, results: List[ServiceDataInfo]) -> List[ServiceDataInfo]:
        """Merge same-service paths, but never blend risk tiers together.

        A pure cache dir (e.g. Cursor's ``Cache``) and a directory holding
        real installed data (e.g. Cursor's ``extensions``) must stay separate
        so the risky one is never hidden inside a "safe" summary entry.
        """
        groups: Dict[str, List[ServiceDataInfo]] = {}
        for item in results:
            groups.setdefault(item.risk_level, []).append(item)

        merged = [
            items[0] if len(items) == 1 else self._merge_service_entries(items)
            for items in groups.values()
        ]
        merged.sort(key=lambda item: item.size_mb, reverse=True)
        return merged

    def _merge_service_entries(
        self, results: List[ServiceDataInfo]
    ) -> ServiceDataInfo:
        """Combine multiple same-risk paths for a service into one summary entry."""
        primary = max(results, key=lambda item: item.size_mb)
        total_mb = sum(item.size_mb for item in results)
        paths = [item.path for item in results]

        return ServiceDataInfo(
            service_type=primary.service_type,
            name=primary.name,
            path=primary.path,
            size_mb=round(total_mb, 2),
            size_gb=round(total_mb / 1024, 3),
            description=primary.description,
            can_cleanup=primary.can_cleanup,
            cleanup_command=primary.cleanup_command,
            preview_command=primary.preview_command,
            safe_to_cleanup=all(item.safe_to_cleanup for item in results),
            impact="high" if total_mb / 1024 > 1.0 else "medium",
            items_count=primary.items_count,
            details={
                **primary.details,
                "paths": paths,
                "merged_count": len(results),
            },
            risk_level=primary.risk_level,
        )

    def _analyze_service_path(
        self, service_type: ServiceType, path: str
    ) -> Optional[ServiceDataInfo]:
        """Analyze a specific service path."""
        try:
            size_mb = self.measure_service_size_mb(service_type, path)

            if service_type == ServiceType.DOCKER and path == "/var/lib/docker":
                # /var/lib/docker is normally root-only (0710), so `du` sees
                # "permission denied" and silently reports ~0 here even when
                # Docker holds tens/hundreds of GB. Ask the daemon directly
                # instead — it works regardless of filesystem permissions.
                daemon_size_mb = self._get_docker_daemon_size_mb()
                if daemon_size_mb and daemon_size_mb > size_mb:
                    size_mb = daemon_size_mb

            size_gb = size_mb / 1024
            if size_mb < self.threshold_mb:
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
        except Exception as e:
            return ServiceDataInfo(
                service_type=service_type,
                name=service_type.value.title(),
                path=path,
                size_mb=0,
                size_gb=0,
                description=f"Error analyzing: {str(e)}",
                can_cleanup=False,
                cleanup_command="",
                preview_command="",
                safe_to_cleanup=False,
                impact="none",
                details={"error": str(e)},
                risk_level=RiskLevel.REVIEW.value,
            )

    def _get_path_size_mb(self, path: str) -> float:
        """Get size of path in MB using du, falling back to os.walk."""
        try:
            result = subprocess.run(
                ["du", "-sk", "--", path],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                kb = int(result.stdout.strip().splitlines()[-1].split()[0])
                return kb / 1024
        except (OSError, ValueError, subprocess.TimeoutExpired, IndexError):
            pass

        total_size = 0
        if os.path.isfile(path):
            return os.path.getsize(path) / (1024 * 1024)

        try:
            root_dev = os.stat(path).st_dev if os.path.exists(path) else None
            for dirpath, dirnames, filenames in os.walk(path):
                if root_dev is not None:
                    dirnames[:] = [
                        name
                        for name in dirnames
                        if self._should_descend(
                            os.path.join(dirpath, name), root_dev
                        )
                    ]
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, PermissionError):
            pass
        return total_size / (1024 * 1024)

    def measure_service_size_mb(
        self, service_type: ServiceType, path: str, *, refresh: bool = False
    ) -> float:
        """Measure a service with the same source before and after cleanup.

        Root-owned Docker storage cannot be measured reliably with an
        unprivileged ``du``.  Using the daemon here also prevents cleanup from
        falsely reporting that the whole Docker directory was freed when the
        post-cleanup ``du`` returned zero due to permissions.
        """
        if service_type == ServiceType.DOCKER and path == "/var/lib/docker":
            daemon_size = (
                self._get_docker_daemon_size_mb(refresh=True)
                if refresh
                else self._get_docker_daemon_size_mb()
            )
            if daemon_size is not None:
                return daemon_size
        return self._get_path_size_mb(path)

    def _get_docker_daemon_size_mb(self, *, refresh: bool = False) -> Optional[float]:
        """Total Docker disk usage as reported by the daemon itself."""
        usage = self._get_docker_daemon_usage(refresh=refresh)
        if usage is None:
            return None
        return float(usage["size_mb"])

    def _get_docker_daemon_usage(
        self, *, refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Return one stable Docker usage snapshot.

        Asking the daemon (``docker system df``) works even when the caller
        can't read /var/lib/docker directly (typically root-only, mode 0710).
        Docker can take tens of seconds with thousands of images, so one
        snapshot is cached for the whole scan and reused for details/counts.
        """
        if self._docker_usage_cache is not None and not refresh:
            return self._docker_usage_cache

        try:
            result = subprocess.run(
                ["docker", "system", "df", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

        if result.returncode != 0 or not result.stdout.strip():
            return None

        rows: Dict[str, Dict[str, Any]] = {}
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
        return self._docker_usage_cache

    @staticmethod
    def _docker_usage_details(usage: Dict[str, Any]) -> Dict[str, Any]:
        rows = usage.get("rows", {})
        return {
            "items_count": sum(
                int(row.get("total", 0)) for row in rows.values()
            ),
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
        multipliers = {"B": 1 / 1024**2, "KB": 1 / 1024, "MB": 1, "GB": 1024, "TB": 1024**2}
        return amount * multipliers.get(unit, 0.0)

    @staticmethod
    def _should_descend(path: str, root_dev: int) -> bool:
        """Skip mount points so loop-mounted snaps are not double-counted."""
        try:
            return os.stat(path).st_dev == root_dev
        except OSError:
            return False

    def get_cleanup_plan(self, selected_services: List[str] = None) -> Dict[str, Any]:
        """Generate cleanup plan for services."""
        return self._cleaner.get_cleanup_plan(selected_services)

    def cleanup_service(
        self, service_type: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute cleanup for a specific service."""
        return self._cleaner.cleanup_service(service_type, dry_run)


def main():
    """Test the service data scanner."""
    scanner = ServiceDataScanner(threshold_mb=100)
    plan = scanner.get_cleanup_plan()
    print(json.dumps(plan, indent=2, default=str))


if __name__ == "__main__":
    main()
