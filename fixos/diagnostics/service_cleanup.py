"""
Service Cleanup for fixOS
Handles planning and execution of service data cleanup operations.
"""

import os
import shlex
import subprocess
from typing import Dict, Any, List
from ..constants import (
    DEFAULT_COMMAND_TIMEOUT,
)


class ServiceCleaner:
    """Plans and executes cleanup of service data."""

    def __init__(self, scanner):
        """Initialize with a ServiceDataScanner instance."""
        self.scanner = scanner

    def get_cleanup_plan(self, selected_services: List[str] = None) -> Dict[str, Any]:
        """Generate cleanup plan for services, split into 3 risk tiers."""
        from .service_scanner import RiskLevel

        services = self.scanner.scan_all_services()

        if selected_services:
            services = [
                s for s in services if s.service_type.value in selected_services
            ]

        total_size_gb = sum(s.size_gb for s in services)
        safe_services = [s for s in services if s.risk_level == RiskLevel.SAFE.value]
        review_services = [
            s for s in services if s.risk_level == RiskLevel.REVIEW.value
        ]
        dangerous_services = [
            s for s in services if s.risk_level == RiskLevel.DANGEROUS.value
        ]

        plan = {
            "threshold_mb": self.scanner.threshold_mb,
            "services_found": len(services),
            "total_size_gb": round(total_size_gb, 2),
            "safe_cleanup_gb": round(sum(s.size_gb for s in safe_services), 2),
            "requires_review_gb": round(sum(s.size_gb for s in review_services), 2),
            "dangerous_gb": round(sum(s.size_gb for s in dangerous_services), 2),
            "services": [self._service_to_dict(s) for s in services],
            "safe_to_cleanup": [self._service_to_dict(s) for s in safe_services],
            "requires_review": [self._service_to_dict(s) for s in review_services],
            "dangerous": [self._service_to_dict(s) for s in dangerous_services],
        }

        return plan

    def cleanup_service(
        self, service_type: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute cleanup for a specific service."""
        from .service_scanner import ServiceType

        result = {
            "service": service_type,
            "dry_run": dry_run,
            "success": False,
            "space_freed_gb": 0,
            "output": "",
            "error": "",
        }

        try:
            service_enum = ServiceType(service_type)
            services = self.scanner.scan_service(service_enum)

            if not services:
                result["error"] = f"No {service_type} data found above threshold"
                return result

            service = services[0]  # Take first (largest)
            initial_size = service.size_gb

            if dry_run:
                result["success"] = True
                result["output"] = f"[DRY RUN] Would execute: {service.cleanup_command}"
                result["space_freed_gb"] = initial_size
                return result

            # Execute cleanup
            cleanup_result = subprocess.run(
                service.cleanup_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=DEFAULT_COMMAND_TIMEOUT,
            )

            # Check new size
            new_size_mb = self.scanner._get_path_size_mb(service.path)
            new_size_gb = new_size_mb / 1024
            freed_gb = max(0, initial_size - new_size_gb)

            result["success"] = cleanup_result.returncode == 0
            result["output"] = cleanup_result.stdout
            result["error"] = cleanup_result.stderr
            result["space_freed_gb"] = round(freed_gb, 3)
            result["initial_size_gb"] = initial_size
            result["remaining_size_gb"] = round(new_size_gb, 3)

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def _service_to_dict(service) -> Dict[str, Any]:
        """Convert ServiceDataInfo to dictionary."""
        return {
            "service_type": service.service_type.value,
            "name": service.name,
            "path": service.path,
            "size_mb": service.size_mb,
            "size_gb": service.size_gb,
            "description": service.description,
            "can_cleanup": service.can_cleanup,
            "cleanup_command": service.cleanup_command,
            "preview_command": service.preview_command,
            "safe_to_cleanup": service.safe_to_cleanup,
            "risk_level": service.risk_level,
            "impact": service.impact,
            "items_count": service.items_count,
            "details": service.details,
        }

    @staticmethod
    def get_risk_level(service_type, path: str | None = None) -> str:
        """Classify cleanup risk for a service path.

        Returns one of ``RiskLevel.SAFE`` / ``REVIEW`` / ``DANGEROUS``
        (as their string values):

        - safe: rebuildable cache — re-downloads or regenerates itself
          (package/build caches, browser caches, system package caches).
        - review: recoverable but worth a look before deleting — reinstallable
          apps, long-unused tool data, or unrecognized cache directories.
        - dangerous: real installed application data that is not a simple
          cache (AI models, containers/volumes, VM disks, editor extensions)
          and may not be trivially recoverable.
        """
        from .service_scanner import RiskLevel, ServiceType

        normalized_path = os.path.expanduser(path or "").rstrip("/")

        if service_type == ServiceType.CHROME:
            chrome_cache_root = os.path.expanduser("~/.cache/google-chrome").rstrip("/")
            chrome_cache_names = {
                "Cache",
                "Code Cache",
                "GPUCache",
                "DawnCache",
                "GrShaderCache",
                "ShaderCache",
                "Service Worker",
            }

            if normalized_path == chrome_cache_root or normalized_path.startswith(
                f"{chrome_cache_root}/"
            ):
                return RiskLevel.SAFE.value

            if os.path.basename(normalized_path) in chrome_cache_names:
                return RiskLevel.SAFE.value

            return RiskLevel.REVIEW.value

        if service_type == ServiceType.BRAVE:
            if "/Cache" in normalized_path or normalized_path.endswith(
                ("GPUCache", "Code Cache")
            ):
                return RiskLevel.SAFE.value
            if normalized_path.endswith("BraveSoftware") or "/BraveSoftware/" in (
                normalized_path
            ):
                return RiskLevel.SAFE.value
            return RiskLevel.REVIEW.value

        if service_type == ServiceType.STEAM:
            safe_suffixes = ("shadercache", "appcache")
            if any(normalized_path.endswith(suffix) for suffix in safe_suffixes):
                return RiskLevel.SAFE.value
            # Anything else is the actual Steam library/client: installed
            # games and their save data, not a cache.
            return RiskLevel.DANGEROUS.value

        if service_type in (ServiceType.CURSOR, ServiceType.VSCODE):
            # The extensions directory holds real installed extensions (and
            # any local-only extension data), not a cache — reinstalling
            # each one by hand is real work and some local state won't come
            # back. Everything else these two scan (Cache/CachedData/logs)
            # is a plain, rebuildable cache.
            if os.path.basename(normalized_path) == "extensions":
                return RiskLevel.DANGEROUS.value
            return RiskLevel.SAFE.value

        if service_type in (ServiceType.GENERIC_CACHE, ServiceType.ELECTRON):
            base = os.path.basename(normalized_path).lower()
            if any(
                hint in base
                for hint in ("cache", "shader", "tmp", "temp", "log", "crash", "thumb")
            ):
                return RiskLevel.SAFE.value
            return RiskLevel.REVIEW.value

        dangerous_services = {
            # Bulk-wipe commands that remove every installed model/container,
            # not just unused/old ones.
            ServiceType.DOCKER,
            ServiceType.CONTAINERD,
            ServiceType.PODMAN,
            ServiceType.OLLAMA,
            ServiceType.LMSTUDIO,
            ServiceType.HUGGINGFACE,
            ServiceType.JUPYTER,
            ServiceType.MINIKUBE,
            # Actual installed apps, not a cache directory.
            ServiceType.APPIMAGE,
            # VM disks/snapshots: unique state, not redownloadable.
            ServiceType.VBOX,
            ServiceType.VMWARE,
        }
        if service_type in dangerous_services:
            return RiskLevel.DANGEROUS.value

        safe_services = {
            # Package caches (can be re-downloaded)
            ServiceType.NPM,
            ServiceType.YARN,
            ServiceType.PNPM,
            ServiceType.PIP,
            ServiceType.CONDA,
            ServiceType.POETRY,
            ServiceType.GRADLE,
            ServiceType.MAVEN,
            ServiceType.CARGO,
            ServiceType.GO,
            ServiceType.UV,
            ServiceType.TORCH,
            ServiceType.BUN,
            ServiceType.PLAYWRIGHT,
            ServiceType.CCACHE,
            ServiceType.HELM,
            ServiceType.BAZEL,
            ServiceType.GH,
            ServiceType.NVIDIA,
            ServiceType.DISCORD,
            ServiceType.SLACK,
            ServiceType.SPOTIFY,
            ServiceType.BRAVE,
            ServiceType.NIX,
            ServiceType.BREW,
            # System caches
            ServiceType.APT,
            ServiceType.DNF,
            ServiceType.PACMAN,
            ServiceType.YUM,
            ServiceType.ZYPPER,
            # Browser caches
            ServiceType.FIREFOX,
            ServiceType.EDGE,
            # App caches
            ServiceType.THUMBNAILS,
            ServiceType.LOGS,
            # Cloud CLI caches
            ServiceType.AWS,
            ServiceType.GCLOUD,
            ServiceType.AZURE,
            # IaC caches
            ServiceType.TERRAFORM,
            ServiceType.PULUMI,
        }
        if service_type in safe_services:
            return RiskLevel.SAFE.value

        # Default: reinstallable apps / long-unused tool data / unclassified
        # (Flatpak, Snap, Android SDK, JetBrains, Vagrant, Unity, ...) —
        # worth a look before deleting, but not flagged as high-risk.
        return RiskLevel.REVIEW.value

    @staticmethod
    def is_safe_cleanup(service_type, path: str | None = None) -> bool:
        """Backward-compatible bool view of get_risk_level() == SAFE."""
        from .service_scanner import RiskLevel

        return ServiceCleaner.get_risk_level(service_type, path) == RiskLevel.SAFE.value

    @staticmethod
    def get_cleanup_hints(service_type, size_gb: float) -> List[str]:
        """Get helpful hints for cleaning services that require manual review."""
        from .service_scanner import ServiceType

        hints = []

        if service_type == ServiceType.FLATPAK:
            hints.extend(
                [
                    "🔥 FLATPAK CLEANUP (most common solution):",
                    "  flatpak uninstall --unused -y",
                    "  # Safe: removes unused runtimes and old versions",
                    "  # Often recovers 10-50 GB",
                    "",
                    "  flatpak repair",
                    "  # Optional: repairs Flatpak installation",
                    "",
                    "📊 To investigate further:",
                    "  du -h /var/lib/flatpak | sort -h | tail -20",
                    "  # Shows largest directories",
                    "",
                    "  flatpak list --app --columns=name,size",
                    "  # Lists apps with sizes",
                    "",
                    "⚠️  Note: Runtime removal won't affect used apps",
                    "    Each app depends on specific runtime versions",
                    "    Unused runtimes accumulate over time",
                ]
            )

            if size_gb > 50:
                hints.extend(
                    [
                        "",
                        f"💡 With {size_gb:.1f} GB used, you likely have:",
                        "   - Multiple GNOME runtime versions (2-3 GB each)",
                        "   - freedesktop runtime versions",
                        "   - Old app versions",
                        "   - Possibly unused SDKs",
                    ]
                )

        elif service_type == ServiceType.DOCKER:
            hints.extend(
                [
                    "🐳 DOCKER CLEANUP:",
                    "  docker system prune -a -f",
                    "  # Removes all unused images, containers, networks",
                    "",
                    "  docker volume prune -f",
                    "  # Removes unused volumes (check first!)",
                    "",
                    "📊 Check usage:",
                    "  docker system df",
                ]
            )

        elif service_type == ServiceType.OLLAMA:
            hints.extend(
                [
                    "🤖 OLLAMA CLEANUP:",
                    "  ollama list",
                    "  # See installed models",
                    "",
                    "  ollama rm <model_name>",
                    "  # Remove specific model",
                    "",
                    "💡 Models can be 5-50 GB each",
                ]
            )

        elif service_type == ServiceType.STEAM:
            hints.extend(
                [
                    "🎮 STEAM CLEANUP:",
                    "  rm -rf ~/.local/share/Steam/steamapps/shadercache",
                    "  # Safe: shader cache rebuilds automatically",
                    "",
                    "  steamcmd +app_update ...",
                    "  # Games themselves require manual uninstall in Steam UI",
                    "",
                    "📊 Check usage:",
                    "  du -sh ~/.local/share/Steam/steamapps/common/* | sort -hr | head",
                ]
            )

        elif service_type == ServiceType.MINIKUBE:
            hints.extend(
                [
                    "☸️ MINIKUBE CLEANUP:",
                    "  minikube stop",
                    "  minikube delete --all",
                    "  # Removes local Kubernetes cluster and VM data",
                    "",
                    "💡 Docker driver images may remain in Docker cache",
                ]
            )

        elif service_type == ServiceType.LMSTUDIO:
            hints.extend(
                [
                    "🤖 LM STUDIO CLEANUP:",
                    "  ls ~/.lmstudio/models",
                    "  # Review downloaded models before deleting",
                    "",
                    "  rm -rf ~/.lmstudio/models/<model>",
                    "  # Remove one model at a time",
                ]
            )

        elif service_type == ServiceType.GENERIC_CACHE:
            hints.extend(
                [
                    "📂 UNKNOWN CACHE:",
                    "  du -sh ~/.cache/<dir>",
                    "  # Inspect contents before deleting",
                    "",
                    "  rm -rf <path>",
                    "  # Only if you recognize it as rebuildable cache",
                ]
            )

        return hints

    @staticmethod
    def get_service_description(service_type) -> str:
        """Get description for service type."""
        from .service_scanner import ServiceType

        descriptions = {
            # Containers
            ServiceType.DOCKER: "Docker images, containers, and volumes",
            ServiceType.OLLAMA: "Ollama AI model files",
            ServiceType.CONTAINERD: "Containerd container runtime data",
            ServiceType.PODMAN: "Podman containers and images",
            # JS/Node
            ServiceType.NPM: "NPM package cache",
            ServiceType.YARN: "Yarn package cache",
            ServiceType.PNPM: "PNPM store cache",
            # Python
            ServiceType.PIP: "Python pip cache",
            ServiceType.CONDA: "Conda package cache (pkgs directories)",
            ServiceType.POETRY: "Poetry virtual environments and cache",
            # Java
            ServiceType.GRADLE: "Gradle build cache",
            ServiceType.MAVEN: "Maven repository cache",
            # Rust/Go
            ServiceType.CARGO: "Rust Cargo registry cache",
            ServiceType.GO: "Go modules cache",
            # Mobile
            ServiceType.FLUTTER: "Flutter SDK and pub cache",
            ServiceType.DART: "Dart pub cache",
            ServiceType.ANDROID: "Android SDK and build cache",
            # System packages
            ServiceType.SNAP: "Snap packages and cache",
            ServiceType.FLATPAK: "Flatpak applications and runtimes",
            ServiceType.APPIMAGE: "AppImage applications",
            ServiceType.APT: "APT package cache",
            ServiceType.DNF: "DNF package cache",
            ServiceType.PACMAN: "Pacman package cache",
            ServiceType.YUM: "Yum package cache",
            ServiceType.ZYPPER: "Zypper package cache",
            # Virtualization
            ServiceType.VAGRANT: "Vagrant boxes and VMs",
            ServiceType.VBOX: "VirtualBox VMs and cache",
            ServiceType.VMWARE: "VMware virtual machines",
            # Package managers
            ServiceType.NIX: "Nix store and profiles",
            ServiceType.BREW: "Homebrew cache and Cellar",
            # Browsers
            ServiceType.CHROME: "Google Chrome cache and data",
            ServiceType.FIREFOX: "Firefox cache and data",
            ServiceType.EDGE: "Microsoft Edge cache and data",
            # IDEs
            ServiceType.VSCODE: "VS Code extensions and cache",
            ServiceType.CURSOR: "Cursor editor cache",
            ServiceType.JETBRAINS: "JetBrains IDE caches and indexes",
            # Cloud/ML
            ServiceType.HUGGINGFACE: "HuggingFace models cache",
            ServiceType.AWS: "AWS CLI cache and logs",
            ServiceType.GCLOUD: "Google Cloud CLI cache",
            ServiceType.AZURE: "Azure CLI telemetry and logs",
            # IaC
            ServiceType.TERRAFORM: "Terraform provider plugins cache",
            ServiceType.PULUMI: "Pulumi plugins cache",
            # Game engines
            ServiceType.UNITY: "Unity Editor cache and data",
            ServiceType.UNREAL: "Unreal Engine cache",
            # Other
            ServiceType.JUPYTER: "Jupyter runtime and kernels",
            ServiceType.THUMBNAILS: "Thumbnail cache",
            ServiceType.TRASH: "Trash/Recycle Bin",
            ServiceType.LOGS: "Application logs",
            ServiceType.NVIDIA: "NVIDIA and Mesa GPU shader cache",
            ServiceType.UV: "uv Python package manager cache",
            ServiceType.TORCH: "PyTorch hub and model cache",
            ServiceType.BUN: "Bun JavaScript runtime cache",
            ServiceType.PLAYWRIGHT: "Playwright/Puppeteer browser binaries",
            ServiceType.CCACHE: "C/C++ compiler cache (ccache/sccache)",
            ServiceType.HELM: "Helm chart cache",
            ServiceType.MINIKUBE: "Minikube local Kubernetes cluster data",
            ServiceType.STEAM: "Steam games, shaders and client cache",
            ServiceType.LMSTUDIO: "LM Studio local AI models",
            ServiceType.BRAVE: "Brave browser cache",
            ServiceType.DISCORD: "Discord client cache",
            ServiceType.SLACK: "Slack client cache",
            ServiceType.SPOTIFY: "Spotify offline/cache data",
            ServiceType.BAZEL: "Bazel build cache",
            ServiceType.GH: "GitHub CLI cache",
            ServiceType.ELECTRON: "Electron/Chromium application cache",
            ServiceType.GENERIC_CACHE: "Discovered cache directory",
        }
        return descriptions.get(service_type, f"{service_type.value} data")

    @staticmethod
    def get_cleanup_command(service_type, path: str) -> str:
        """Get cleanup command for service."""
        from .service_scanner import ServiceType

        commands = {
            # Containers
            ServiceType.DOCKER: "docker system prune -af --volumes",
            ServiceType.OLLAMA: "ollama rm $(ollama list | tail -n +2 | awk '{print $1}') 2>/dev/null || true && rm -rf ~/.ollama/models/*",
            ServiceType.CONTAINERD: "sudo rm -rf /var/lib/containerd",
            ServiceType.PODMAN: "podman system prune -af --volumes",
            # JS/Node
            ServiceType.NPM: "npm cache clean --force",
            ServiceType.YARN: "yarn cache clean --all",
            ServiceType.PNPM: "pnpm store prune",
            # Python
            ServiceType.PIP: "pip cache purge || rm -rf ~/.cache/pip/*",
            ServiceType.CONDA: "conda clean --all -y || rm -rf ~/.conda/envs/*/pkgs",
            ServiceType.POETRY: "poetry cache clear --all pypi || rm -rf ~/.cache/pypoetry",
            # Java
            ServiceType.GRADLE: "rm -rf ~/.gradle/caches ~/.gradle/daemon ~/.gradle/wrapper",
            ServiceType.MAVEN: "rm -rf ~/.m2/repository",
            # Rust/Go
            ServiceType.CARGO: "cargo clean --registry || rm -rf ~/.cargo/registry/cache",
            ServiceType.GO: "go clean -cache -modcache && rm -rf ~/go/pkg",
            # Mobile
            ServiceType.FLUTTER: "flutter pub cache clean && rm -rf ~/.pub-cache",
            ServiceType.DART: "rm -rf ~/.pub-cache",
            ServiceType.ANDROID: "rm -rf ~/.android/build-cache ~/Android/Sdk/build-tools/*/preview",
            # System packages
            ServiceType.SNAP: 'snap list --all | awk \'/disabled/{print $1, $3}\' | while read snapname revision; do sudo snap remove "$snapname" --revision="$revision"; done',
            ServiceType.FLATPAK: "flatpak uninstall --unused -y && flatpak repair",
            ServiceType.APPIMAGE: "rm -rf ~/.local/share/AppImage ~/.cache/AppImage",
            ServiceType.APT: "sudo apt-get clean && sudo apt-get autoclean",
            ServiceType.DNF: "sudo dnf clean all",
            ServiceType.PACMAN: "sudo pacman -Scc --noconfirm",
            ServiceType.YUM: "sudo yum clean all",
            ServiceType.ZYPPER: "sudo zypper clean --all",
            # Virtualization
            ServiceType.VAGRANT: "vagrant box prune --force",
            ServiceType.VBOX: "rm -rf ~/VirtualBox\\ VMs/*/Snapshots",
            ServiceType.VMWARE: "rm -rf ~/vmware/*.log ~/vmware/*.vmss",
            # Package managers
            ServiceType.NIX: "nix-collect-garbage -d || nix store gc",
            ServiceType.BREW: "brew cleanup --prune=all && brew autoremove",
            # Browsers
            ServiceType.CHROME: ServiceCleaner._chrome_cleanup_command(path),
            ServiceType.FIREFOX: "rm -rf ~/.cache/mozilla ~/.mozilla/firefox/*/cache2",
            ServiceType.EDGE: "rm -rf ~/.cache/microsoft-edge",
            # IDEs
            ServiceType.VSCODE: "rm -rf ~/.config/Code/Cache ~/.config/Code/CachedData ~/.vscode/extensions/*/out",
            ServiceType.CURSOR: "rm -rf ~/.config/Cursor/Cache ~/.config/Cursor/CachedData ~/.cursor/extensions/*/out",
            ServiceType.JETBRAINS: "find ~/.cache/JetBrains -name 'index' -type d -exec rm -rf {} + 2>/dev/null; find ~/.JetBrains -name 'caches' -type d -exec rm -rf {} + 2>/dev/null",
            # Cloud/ML
            ServiceType.HUGGINGFACE: "rm -rf ~/.cache/huggingface/hub/*",
            ServiceType.AWS: "rm -rf ~/.aws/sso/cache ~/.aws/cli/cache",
            ServiceType.GCLOUD: "gcloud auth application-default revoke 2>/dev/null; rm -rf ~/.config/gcloud/logs ~/.cache/gcloud",
            ServiceType.AZURE: "rm -rf ~/.azure/telemetry ~/.azure/logs",
            # IaC
            ServiceType.TERRAFORM: "rm -rf ~/.terraform.d/plugin-cache",
            ServiceType.PULUMI: "pulumi plugin rm --all --yes 2>/dev/null || rm -rf ~/.pulumi/plugins",
            # Game engines
            ServiceType.UNITY: "rm -rf ~/.config/unity3d/Editor/Cache",
            ServiceType.UNREAL: "rm -rf ~/.config/Epic/UnrealEngine/5.*/DerivedDataCache",
            # Other
            ServiceType.JUPYTER: "jupyter kernelspec uninstall -y $(jupyter kernelspec list | tail -n +2 | awk '{print $1}') 2>/dev/null; rm -rf ~/.local/share/jupyter/runtime",
            ServiceType.THUMBNAILS: "rm -rf ~/.cache/thumbnails/* ~/.thumbnails/*",
            ServiceType.TRASH: "rm -rf ~/.local/share/Trash/* ~/.Trash/*",
            ServiceType.LOGS: "find ~/.cache/log ~/.local/state -name '*.log' -mtime +7 -delete 2>/dev/null; journalctl --vacuum-time=7d 2>/dev/null || true",
            ServiceType.NVIDIA: "rm -rf ~/.cache/nvidia ~/.nv/ComputeCache ~/.cache/mesa_shader_cache",
            ServiceType.UV: "uv cache clean || rm -rf ~/.cache/uv ~/.local/share/uv",
            ServiceType.TORCH: "rm -rf ~/.cache/torch ~/.torch",
            ServiceType.BUN: "rm -rf ~/.bun/install/cache",
            ServiceType.PLAYWRIGHT: "rm -rf ~/.cache/ms-playwright ~/.cache/puppeteer",
            ServiceType.CCACHE: "ccache -C 2>/dev/null || rm -rf ~/.ccache; rm -rf ~/.cache/sccache",
            ServiceType.HELM: "helm cache cleanup 2>/dev/null || rm -rf ~/.cache/helm",
            ServiceType.MINIKUBE: "minikube delete --all 2>/dev/null || rm -rf ~/.minikube",
            ServiceType.STEAM: ServiceCleaner._steam_cleanup_command(path),
            ServiceType.LMSTUDIO: "rm -rf ~/.lmstudio/models/* ~/.cache/lm-studio",
            ServiceType.BRAVE: ServiceCleaner._brave_cleanup_command(path),
            ServiceType.DISCORD: "rm -rf ~/.config/discord/Cache ~/.config/discord/Code Cache ~/.config/discord/GPUCache",
            ServiceType.SLACK: "rm -rf ~/.config/Slack/Cache ~/.config/Slack/Code Cache ~/.config/Slack/Service Worker",
            ServiceType.SPOTIFY: "rm -rf ~/.cache/spotify ~/.config/spotify/Data",
            ServiceType.BAZEL: "rm -rf ~/.cache/bazel",
            ServiceType.GH: "rm -rf ~/.cache/gh",
            ServiceType.ELECTRON: f"rm -rf {shlex.quote(path)}",
            ServiceType.GENERIC_CACHE: f"rm -rf {shlex.quote(path)}",
        }
        return commands.get(service_type, f"rm -rf {path}")

    @staticmethod
    def _chrome_cleanup_command(path: str) -> str:
        """Build a path-aware Chrome cleanup command.

        Chrome keeps cache data both in the dedicated cache directory and
        inside the profile tree. Cleaning only the global cache leaves the
        largest profile caches untouched, so we remove common cache
        directories under the scanned profile path as well.
        """
        expanded_path = os.path.expanduser(path).rstrip("/")
        cache_root = os.path.expanduser("~/.cache/google-chrome").rstrip("/")
        quoted_path = shlex.quote(expanded_path)

        if expanded_path == cache_root or expanded_path.startswith(f"{cache_root}/"):
            return f"rm -rf {quoted_path}"

        cache_dir_names = [
            "Cache",
            "Code Cache",
            "GPUCache",
            "DawnCache",
            "GrShaderCache",
            "ShaderCache",
            "Service Worker",
        ]
        find_expr = " -o ".join(
            f"-name {shlex.quote(name)}" for name in cache_dir_names
        )
        return (
            "rm -rf ~/.cache/google-chrome 2>/dev/null || true; "
            f"find {quoted_path} -type d \\( {find_expr} \\) "
            "-prune -exec rm -rf {} + 2>/dev/null || true"
        )

    @staticmethod
    def _brave_cleanup_command(path: str) -> str:
        expanded_path = os.path.expanduser(path).rstrip("/")
        quoted_path = shlex.quote(expanded_path)
        cache_root = os.path.expanduser("~/.cache/BraveSoftware").rstrip("/")
        if expanded_path == cache_root or expanded_path.startswith(f"{cache_root}/"):
            return f"rm -rf {quoted_path}"
        return (
            "rm -rf ~/.cache/BraveSoftware 2>/dev/null || true; "
            f"rm -rf {quoted_path} 2>/dev/null || true"
        )

    @staticmethod
    def _steam_cleanup_command(path: str) -> str:
        expanded_path = os.path.expanduser(path).rstrip("/")
        quoted_path = shlex.quote(expanded_path)
        if expanded_path.endswith(("shadercache", "appcache")):
            return f"rm -rf {quoted_path}"
        return (
            "rm -rf ~/.local/share/Steam/steamapps/shadercache "
            "~/.local/share/Steam/appcache 2>/dev/null || true"
        )

    @staticmethod
    def get_preview_command(service_type, path: str) -> str:
        """Get preview command for service."""
        from .service_scanner import ServiceType

        previews = {
            # Containers
            ServiceType.DOCKER: "docker system df -v",
            ServiceType.OLLAMA: "ollama list",
            ServiceType.CONTAINERD: "sudo ls -la /var/lib/containerd 2>/dev/null || echo 'Requires sudo access'",
            ServiceType.PODMAN: "podman system df -v || podman images",
            # JS/Node
            ServiceType.NPM: "npm cache ls 2>/dev/null || du -sh ~/.npm",
            ServiceType.YARN: "yarn cache list 2>/dev/null || du -sh ~/.cache/yarn",
            ServiceType.PNPM: "pnpm store status 2>/dev/null || du -sh ~/.pnpm-store",
            # Python
            ServiceType.PIP: "pip cache dir && pip cache info 2>/dev/null || du -sh ~/.cache/pip",
            ServiceType.CONDA: "conda info --envs 2>/dev/null && conda list 2>/dev/null | head -20 || du -sh ~/miniconda3",
            ServiceType.POETRY: "poetry config cache-dir 2>/dev/null || du -sh ~/.cache/pypoetry",
            # Java
            ServiceType.GRADLE: "ls -la ~/.gradle/caches 2>/dev/null | head -20 || du -sh ~/.gradle",
            ServiceType.MAVEN: "du -sh ~/.m2/repository/* 2>/dev/null | sort -hr | head -20",
            # Rust/Go
            ServiceType.CARGO: "ls -la ~/.cargo/registry/cache 2>/dev/null | head -20 || du -sh ~/.cargo",
            ServiceType.GO: "go env GOPATH && du -sh ~/go/pkg 2>/dev/null || echo 'Go modules cache'",
            # Mobile
            ServiceType.FLUTTER: "flutter pub cache list 2>/dev/null | head -20 || du -sh ~/.pub-cache",
            ServiceType.DART: "du -sh ~/.pub-cache 2>/dev/null",
            ServiceType.ANDROID: "du -sh ~/Android/Sdk/* 2>/dev/null | sort -hr | head -10 || du -sh ~/.android",
            # System packages
            ServiceType.SNAP: "snap list --all",
            ServiceType.FLATPAK: "flatpak list --app --runtime",
            ServiceType.APPIMAGE: "ls -la ~/.local/share/AppImage 2>/dev/null || echo 'No AppImage data'",
            ServiceType.APT: "apt-cache stats 2>/dev/null || du -sh /var/cache/apt/archives",
            ServiceType.DNF: "dnf repolist && du -sh /var/cache/dnf 2>/dev/null",
            ServiceType.PACMAN: "pacman -Sc --dry-run 2>/dev/null || du -sh /var/cache/pacman/pkg",
            ServiceType.YUM: "yum repolist && du -sh /var/cache/yum 2>/dev/null",
            ServiceType.ZYPPER: "zypper packages --installed-only 2>/dev/null | head -20 || du -sh /var/cache/zypp",
            # Virtualization
            ServiceType.VAGRANT: "vagrant box list",
            ServiceType.VBOX: "vboxmanage list vms 2>/dev/null || ls -la ~/VirtualBox\\ VMs 2>/dev/null || echo 'No VirtualBox VMs'",
            ServiceType.VMWARE: "ls -la ~/vmware 2>/dev/null || ls -la ~/Virtual\\ Machines 2>/dev/null || echo 'No VMware VMs'",
            # Package managers
            ServiceType.NIX: "nix store gc --dry-run 2>/dev/null || du -sh /nix 2>/dev/null || du -sh ~/.nix-profile",
            ServiceType.BREW: "brew list | wc -l && du -sh ~/homebrew 2>/dev/null || du -sh /opt/homebrew 2>/dev/null || du -sh /usr/local/Homebrew",
            # Browsers
            ServiceType.CHROME: "du -sh ~/.cache/google-chrome 2>/dev/null || du -sh ~/.config/google-chrome",
            ServiceType.FIREFOX: "du -sh ~/.cache/mozilla 2>/dev/null || du -sh ~/.mozilla",
            ServiceType.EDGE: "du -sh ~/.cache/microsoft-edge 2>/dev/null || du -sh ~/.config/microsoft-edge",
            # IDEs
            ServiceType.VSCODE: "code --list-extensions 2>/dev/null | wc -l && du -sh ~/.vscode/extensions 2>/dev/null",
            ServiceType.CURSOR: "du -sh ~/.cursor/extensions 2>/dev/null || du -sh ~/.config/Cursor",
            ServiceType.JETBRAINS: "find ~/.cache/JetBrains -maxdepth 1 -type d 2>/dev/null | wc -l && du -sh ~/.cache/JetBrains 2>/dev/null",
            # Cloud/ML
            ServiceType.HUGGINGFACE: "du -sh ~/.cache/huggingface 2>/dev/null && ls ~/.cache/huggingface/hub 2>/dev/null | head -10",
            ServiceType.AWS: "ls -la ~/.aws/sso/cache 2>/dev/null || du -sh ~/.aws",
            ServiceType.GCLOUD: "gcloud config list 2>/dev/null | head -10 || du -sh ~/.config/gcloud",
            ServiceType.AZURE: "az account list 2>/dev/null | head -5 || du -sh ~/.azure",
            # IaC
            ServiceType.TERRAFORM: "ls ~/.terraform.d/providers 2>/dev/null || du -sh ~/.terraform.d",
            ServiceType.PULUMI: "pulumi plugin ls 2>/dev/null || du -sh ~/.pulumi/plugins",
            # Game engines
            ServiceType.UNITY: "du -sh ~/.config/unity3d 2>/dev/null || du -sh ~/Library/Unity",
            ServiceType.UNREAL: "du -sh ~/.config/Epic 2>/dev/null || du -sh ~/Library/Application\\ Support/Epic",
            # Other
            ServiceType.JUPYTER: "jupyter kernelspec list 2>/dev/null || du -sh ~/.local/share/jupyter",
            ServiceType.THUMBNAILS: "du -sh ~/.cache/thumbnails 2>/dev/null && find ~/.cache/thumbnails -type f | wc -l",
            ServiceType.TRASH: "du -sh ~/.local/share/Trash 2>/dev/null || du -sh ~/.Trash",
            ServiceType.LOGS: "find ~/.cache/log ~/.local/state /var/log ~/.var/log 2>/dev/null -name '*.log' | wc -l && du -sh ~/.cache/log 2>/dev/null || du -sh /var/log 2>/dev/null",
            ServiceType.NVIDIA: "du -sh ~/.cache/nvidia ~/.nv/ComputeCache 2>/dev/null",
            ServiceType.UV: "uv cache dir 2>/dev/null || du -sh ~/.cache/uv",
            ServiceType.TORCH: "du -sh ~/.cache/torch 2>/dev/null",
            ServiceType.BUN: "du -sh ~/.bun/install/cache 2>/dev/null",
            ServiceType.PLAYWRIGHT: "du -sh ~/.cache/ms-playwright ~/.cache/puppeteer 2>/dev/null",
            ServiceType.CCACHE: "ccache -s 2>/dev/null || du -sh ~/.ccache",
            ServiceType.HELM: "helm cache stats 2>/dev/null || du -sh ~/.cache/helm",
            ServiceType.MINIKUBE: "minikube status 2>/dev/null || du -sh ~/.minikube",
            ServiceType.STEAM: "du -sh ~/.local/share/Steam/steamapps/common 2>/dev/null | sort -hr | head -10",
            ServiceType.LMSTUDIO: "du -sh ~/.lmstudio/models 2>/dev/null || ls ~/.lmstudio/models",
            ServiceType.BRAVE: "du -sh ~/.cache/BraveSoftware 2>/dev/null",
            ServiceType.DISCORD: "du -sh ~/.config/discord/Cache 2>/dev/null",
            ServiceType.SLACK: "du -sh ~/.config/Slack/Cache 2>/dev/null",
            ServiceType.SPOTIFY: "du -sh ~/.cache/spotify 2>/dev/null",
            ServiceType.BAZEL: "du -sh ~/.cache/bazel 2>/dev/null",
            ServiceType.GH: "du -sh ~/.cache/gh 2>/dev/null",
        }
        return previews.get(
            service_type, f"du -sh {path} 2>/dev/null && ls -la {path} | head -20"
        )
