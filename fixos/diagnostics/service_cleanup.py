"""
Service Cleanup for fixOS
Handles planning and execution of service data cleanup operations.
"""

import os
import re
import shlex
import subprocess
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Dict, Any, List
from ..constants import (
    DEFAULT_COMMAND_TIMEOUT,
)

# Unused Docker images older than this many days (``fixos cleanup --docker-old``).
DEFAULT_DOCKER_OLD_UNUSED_DAYS = 30
# Ollama models not modified for this many days (``fixos cleanup --ollama-old``).
DEFAULT_OLLAMA_OLD_UNUSED_DAYS = 90


class ServiceCleaner:
    """Plans and executes cleanup of service data."""

    def __init__(self, scanner):
        """Initialize with a ServiceDataScanner instance."""
        self.scanner = scanner

    @staticmethod
    def docker_old_unused_until_hours(days: int = DEFAULT_DOCKER_OLD_UNUSED_DAYS) -> int:
        """Convert a positive day count to Docker ``until=<Nh>`` hours."""
        days_int = int(days)
        if days_int < 1:
            raise ValueError("days must be >= 1")
        return days_int * 24

    @staticmethod
    def get_docker_old_unused_command(
        days: int = DEFAULT_DOCKER_OLD_UNUSED_DAYS,
    ) -> str:
        """Bounded prune: unused images (and old build cache) older than N days.

        - ``image prune -a`` only removes images not referenced by any container
        - ``until=<Nh>`` keeps recent unused images
        - never touches volumes or running containers
        """
        hours = ServiceCleaner.docker_old_unused_until_hours(days)
        return (
            f"docker image prune -a --force --filter until={hours}h && "
            f"docker builder prune --force --filter until={hours}h"
        )

    @staticmethod
    def _ollama_base_url() -> str:
        host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
        if "://" not in host:
            host = f"http://{host}"
        return host.rstrip("/")

    @staticmethod
    def _parse_ollama_modified_at(value: str) -> datetime:
        """Parse Ollama RFC3339 timestamps (may include >6 fractional digits)."""
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        match = re.match(
            r"^(?P<head>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
            r"(?:\.(?P<frac>\d+))?"
            r"(?P<tz>[+-]\d{2}:\d{2})?$",
            text,
        )
        if not match:
            raise ValueError(f"unrecognized ollama timestamp: {value}")
        frac = (match.group("frac") or "0")[:6].ljust(6, "0")
        tz = match.group("tz") or "+00:00"
        dt = datetime.fromisoformat(f"{match.group('head')}.{frac}{tz}")
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _ollama_api_get(path: str) -> Dict[str, Any]:
        url = f"{ServiceCleaner._ollama_base_url()}{path}"
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def list_ollama_models() -> List[Dict[str, Any]]:
        """Return installed Ollama models with name/size/modified_at (UTC)."""
        payload = ServiceCleaner._ollama_api_get("/api/tags")
        models: List[Dict[str, Any]] = []
        for item in payload.get("models") or []:
            name = item.get("name") or item.get("model")
            modified = item.get("modified_at")
            if not name or not modified:
                continue
            models.append(
                {
                    "name": name,
                    "size_bytes": int(item.get("size") or 0),
                    "modified_at": modified,
                    "modified_at_utc": ServiceCleaner._parse_ollama_modified_at(
                        modified
                    ).isoformat(),
                }
            )
        return models

    @staticmethod
    def list_running_ollama_models() -> set[str]:
        """Names of models currently loaded in memory (must not be deleted)."""
        try:
            payload = ServiceCleaner._ollama_api_get("/api/ps")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return set()
        running: set[str] = set()
        for item in payload.get("models") or []:
            name = item.get("name") or item.get("model")
            if name:
                running.add(name)
        return running

    @staticmethod
    def select_old_ollama_models(
        models: List[Dict[str, Any]],
        days: int = DEFAULT_OLLAMA_OLD_UNUSED_DAYS,
        *,
        now: datetime | None = None,
        running: set[str] | None = None,
    ) -> List[Dict[str, Any]]:
        """Filter models whose modified_at is older than N days; skip running ones."""
        days_int = int(days)
        if days_int < 1:
            raise ValueError("days must be >= 1")
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days_int)
        skip = running or set()
        selected: List[Dict[str, Any]] = []
        for model in models:
            name = model["name"]
            if name in skip:
                continue
            modified = ServiceCleaner._parse_ollama_modified_at(model["modified_at"])
            if modified <= cutoff:
                entry = dict(model)
                entry["age_days"] = (cutoff + timedelta(days=days_int) - modified).days
                selected.append(entry)
        return selected

    def cleanup_ollama_old_unused(
        self,
        days: int = DEFAULT_OLLAMA_OLD_UNUSED_DAYS,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Remove Ollama models not modified for more than N days (skip running)."""
        days_int = int(days)
        if days_int < 1:
            raise ValueError("days must be >= 1")

        result: Dict[str, Any] = {
            "service": "ollama-old",
            "dry_run": dry_run,
            "success": False,
            "space_freed_gb": 0,
            "output": "",
            "error": "",
            "command": "",
            "days": days_int,
            "models": [],
            "skipped_running": [],
        }

        try:
            installed = self.list_ollama_models()
            running = self.list_running_ollama_models()
            selected = self.select_old_ollama_models(
                installed, days=days_int, running=running
            )
            skipped = sorted(
                {
                    model["name"]
                    for model in installed
                    if model["name"] in running
                }
            )
            result["skipped_running"] = skipped
            result["models"] = [
                {
                    "name": model["name"],
                    "size_gb": round(model["size_bytes"] / (1024**3), 3),
                    "modified_at": model["modified_at"],
                    "age_days": model.get("age_days"),
                }
                for model in selected
            ]
            estimated_gb = round(
                sum(model["size_bytes"] for model in selected) / (1024**3), 3
            )
            result["estimated_max_gb"] = estimated_gb
            commands = [f"ollama rm {shlex.quote(model['name'])}" for model in selected]
            result["command"] = " && ".join(commands) if commands else "(brak modeli)"

            if not selected:
                result["success"] = True
                result["output"] = (
                    f"Brak modeli Ollama starszych niż {days_int} dni"
                    + (
                        f" (pominięto uruchomione: {', '.join(skipped)})"
                        if skipped
                        else ""
                    )
                )
                return result

            if dry_run:
                result["success"] = True
                result["space_freed_gb"] = estimated_gb
                lines = [
                    f"[DRY RUN] Would remove {len(selected)} model(s) older than "
                    f"{days_int} days:",
                ]
                for model in result["models"]:
                    lines.append(
                        f"  - {model['name']} ({model['size_gb']:.2f} GB, "
                        f"modified {model['modified_at']})"
                    )
                if skipped:
                    lines.append(
                        "  Kept running: " + ", ".join(skipped)
                    )
                result["output"] = "\n".join(lines)
                return result

            outputs: List[str] = []
            errors: List[str] = []
            freed_bytes = 0
            ok = True
            for model in selected:
                proc = subprocess.run(
                    ["ollama", "rm", model["name"]],
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_COMMAND_TIMEOUT,
                )
                if proc.stdout:
                    outputs.append(proc.stdout.strip())
                if proc.returncode != 0:
                    ok = False
                    errors.append(
                        proc.stderr.strip() or f"ollama rm {model['name']} failed"
                    )
                else:
                    freed_bytes += int(model["size_bytes"])

            result["success"] = ok
            result["output"] = "\n".join(line for line in outputs if line)
            result["error"] = "\n".join(errors)
            result["space_freed_gb"] = round(freed_bytes / (1024**3), 3)
        except Exception as exc:
            result["error"] = str(exc)

        return result

    def cleanup_docker_old_unused(
        self,
        days: int = DEFAULT_DOCKER_OLD_UNUSED_DAYS,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Remove unused Docker images (and rebuildable build cache) older than N days."""
        from .service_scanner import ServiceType

        command = self.get_docker_old_unused_command(days)
        hours = self.docker_old_unused_until_hours(days)
        result: Dict[str, Any] = {
            "service": "docker-old",
            "dry_run": dry_run,
            "success": False,
            "space_freed_gb": 0,
            "output": "",
            "error": "",
            "command": command,
            "days": int(days),
            "until_hours": hours,
        }

        images_reclaimable = 0.0
        build_cache_reclaimable = 0.0
        try:
            services = self.scanner.scan_service(ServiceType.DOCKER)
            if services:
                usage = (services[0].details or {}).get("usage") or {}
                images_reclaimable = float(
                    (usage.get("Images") or {}).get("reclaimable_gb", 0.0)
                )
                build_cache_reclaimable = float(
                    (usage.get("Build Cache") or {}).get("reclaimable_gb", 0.0)
                )
        except Exception:
            pass

        estimated_gb = round(images_reclaimable + build_cache_reclaimable, 3)
        result["estimated_max_gb"] = estimated_gb

        if dry_run:
            result["success"] = True
            result["space_freed_gb"] = estimated_gb
            result["output"] = (
                f"[DRY RUN] Would execute: {command}\n"
                f"  Scope: unused images + build cache older than {int(days)} days "
                f"({hours}h). Volumes and in-use images are kept."
            )
            return result

        try:
            measure = getattr(self.scanner, "measure_service_size_mb", None)
            before_mb = None
            if callable(measure):
                before_mb = measure(ServiceType.DOCKER, "/var/lib/docker", refresh=True)

            cleanup_result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=DEFAULT_COMMAND_TIMEOUT,
            )
            result["returncode"] = cleanup_result.returncode
            result["output"] = cleanup_result.stdout
            result["error"] = cleanup_result.stderr
            result["success"] = cleanup_result.returncode == 0

            if callable(measure) and before_mb is not None:
                after_mb = measure(ServiceType.DOCKER, "/var/lib/docker", refresh=True)
                result["space_freed_gb"] = round(max(0.0, (before_mb - after_mb) / 1024), 3)
            elif result["success"]:
                # Daemon may not expose path size to non-root; keep estimate as hint.
                result["space_freed_gb"] = 0
        except Exception as exc:
            result["error"] = str(exc)

        return result

    def build_safe_age_actions(
        self, selected_services: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        """Bounded age-based cleanups treated as safe (option [1] in interactive cleanup).

        Includes:
        - Ollama models not modified for ``DEFAULT_OLLAMA_OLD_UNUSED_DAYS``
        - Unused Docker images older than ``DEFAULT_DOCKER_OLD_UNUSED_DAYS``
        """
        allow = {item.strip() for item in (selected_services or []) if item.strip()}

        def allowed(*keys: str) -> bool:
            return not allow or any(key in allow for key in keys)

        actions: List[Dict[str, Any]] = []

        if allowed("ollama", "ollama-old"):
            try:
                installed = self.list_ollama_models()
                running = self.list_running_ollama_models()
                selected = self.select_old_ollama_models(
                    installed,
                    days=DEFAULT_OLLAMA_OLD_UNUSED_DAYS,
                    running=running,
                )
            except Exception:
                selected = []
            if selected:
                size_bytes = sum(int(model["size_bytes"]) for model in selected)
                size_gb = round(size_bytes / (1024**3), 3)
                commands = [
                    f"ollama rm {shlex.quote(model['name'])}" for model in selected
                ]
                actions.append(
                    {
                        "service_type": "ollama-old",
                        "cleanup_kind": "ollama-old",
                        "name": (
                            f"Ollama (modele >{DEFAULT_OLLAMA_OLD_UNUSED_DAYS} dni)"
                        ),
                        "path": "",
                        "size_mb": round(size_bytes / (1024**2), 1),
                        "size_gb": size_gb,
                        "description": (
                            "Modele Ollama niezmieniane od "
                            f"{DEFAULT_OLLAMA_OLD_UNUSED_DAYS}+ dni "
                            "(pomija uruchomione)"
                        ),
                        "can_cleanup": True,
                        "cleanup_command": " && ".join(commands),
                        "preview_command": "ollama list",
                        "safe_to_cleanup": True,
                        "risk_level": "safe",
                        "impact": "low",
                        "items_count": len(selected),
                        "details": {
                            "days": DEFAULT_OLLAMA_OLD_UNUSED_DAYS,
                            "models": [model["name"] for model in selected],
                        },
                        "days": DEFAULT_OLLAMA_OLD_UNUSED_DAYS,
                    }
                )

        if allowed("docker", "docker-old"):
            estimated_gb = 0.0
            try:
                from .service_scanner import ServiceType

                docker_services = self.scanner.scan_service(ServiceType.DOCKER)
                if docker_services:
                    usage = (docker_services[0].details or {}).get("usage") or {}
                    estimated_gb = float(
                        (usage.get("Images") or {}).get("reclaimable_gb", 0.0)
                    ) + float(
                        (usage.get("Build Cache") or {}).get("reclaimable_gb", 0.0)
                    )
            except Exception:
                estimated_gb = 0.0
            if estimated_gb > 0:
                command = self.get_docker_old_unused_command(
                    DEFAULT_DOCKER_OLD_UNUSED_DAYS
                )
                actions.append(
                    {
                        "service_type": "docker-old",
                        "cleanup_kind": "docker-old",
                        "name": (
                            f"Docker (nieużywane obrazy >"
                            f"{DEFAULT_DOCKER_OLD_UNUSED_DAYS} dni)"
                        ),
                        "path": "/var/lib/docker",
                        "size_mb": round(estimated_gb * 1024, 1),
                        "size_gb": round(estimated_gb, 3),
                        "description": (
                            "Nieużywane obrazy Docker i stary build cache "
                            f"(>{DEFAULT_DOCKER_OLD_UNUSED_DAYS} dni); bez wolumenów"
                        ),
                        "can_cleanup": True,
                        "cleanup_command": command,
                        "preview_command": "docker system df",
                        "safe_to_cleanup": True,
                        "risk_level": "safe",
                        "impact": "low",
                        "items_count": 0,
                        "details": {
                            "days": DEFAULT_DOCKER_OLD_UNUSED_DAYS,
                            "estimated_max_gb": round(estimated_gb, 3),
                        },
                        "days": DEFAULT_DOCKER_OLD_UNUSED_DAYS,
                    }
                )

        return actions

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

        age_actions = self.build_safe_age_actions(selected_services)
        safe_dicts = [self._service_to_dict(s) for s in safe_services]
        # Age-bounded actions first so option [1] shows them prominently.
        safe_to_cleanup = age_actions + safe_dicts
        service_dicts = age_actions + [self._service_to_dict(s) for s in services]

        plan = {
            "threshold_mb": self.scanner.threshold_mb,
            "services_found": len(service_dicts),
            "total_size_gb": round(
                total_size_gb + sum(item["size_gb"] for item in age_actions), 2
            ),
            "safe_cleanup_gb": round(sum(item["size_gb"] for item in safe_to_cleanup), 2),
            "requires_review_gb": round(sum(s.size_gb for s in review_services), 2),
            "dangerous_gb": round(sum(s.size_gb for s in dangerous_services), 2),
            "manager_reported_reclaimable_gb": round(
                sum(float(s.details.get("reclaimable_size_gb", 0.0)) for s in services),
                2,
            ),
            "services": service_dicts,
            "safe_to_cleanup": safe_to_cleanup,
            "requires_review": [self._service_to_dict(s) for s in review_services],
            "dangerous": [self._service_to_dict(s) for s in dangerous_services],
        }

        return plan

    def cleanup_service(
        self,
        service_type: str,
        dry_run: bool = False,
        planned_service: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Execute cleanup for a specific service or exact planned entry.

        One service type can have entries in multiple risk tiers (for example
        VS Code cache and VS Code extensions).  Re-scanning and blindly taking
        the largest entry could therefore execute a different cleanup than the
        one selected in the CLI.  ``planned_service`` pins execution to the
        displayed path, command and risk entry.
        """
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
            if planned_service is not None:
                if planned_service.get("service_type") != service_type:
                    result["error"] = "Selected cleanup entry does not match service"
                    return result
                service = SimpleNamespace(
                    service_type=service_enum,
                    name=planned_service.get("name", service_type),
                    path=planned_service.get("path", ""),
                    size_gb=float(planned_service.get("size_gb", 0)),
                    can_cleanup=bool(planned_service.get("can_cleanup")),
                    cleanup_command=planned_service.get("cleanup_command", ""),
                    preview_command=planned_service.get("preview_command", ""),
                    details=planned_service.get("details") or {},
                    risk_level=planned_service.get("risk_level", "review"),
                )
            else:
                services = self.scanner.scan_service(service_enum)
                if not services:
                    result["error"] = f"No {service_type} data found above threshold"
                    return result
                service = services[0]  # Backward-compatible single-service mode.
            initial_size = service.size_gb

            protected_bulk_blocked = (
                getattr(service, "risk_level", "review") == "dangerous"
                and not self._is_allowed_protected_cleanup(service)
            )
            if (
                protected_bulk_blocked
                or not service.can_cleanup
                or not service.cleanup_command.strip()
            ):
                if dry_run:
                    preview = getattr(service, "preview_command", "")
                    result["success"] = True
                    result["requires_item_selection"] = True
                    result["output"] = (
                        "[DRY RUN] Zbiorcze czyszczenie jest wyłączone. "
                        f"Bezpieczny podgląd: {preview or 'brak komendy podglądu'}"
                    )
                    return result
                result["error"] = (
                    f"{service.name}: wybierz konkretne elementy do usunięcia; "
                    "zbiorcze czyszczenie jest wyłączone, aby chronić dane"
                )
                return result

            if dry_run:
                estimated_gb = self._estimated_cleanup_gb(service)
                result["success"] = True
                result["output"] = f"[DRY RUN] Would execute: {service.cleanup_command}"
                result["space_freed_gb"] = estimated_gb
                result["estimated_max_gb"] = estimated_gb
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
            measure = getattr(self.scanner, "measure_service_size_mb", None)
            planned_paths = service.details.get("paths") or [service.path]
            if callable(measure):
                new_size_mb = sum(
                    measure(service_enum, path, refresh=True) for path in planned_paths
                )
            else:
                new_size_mb = sum(
                    self.scanner._get_path_size_mb(path) for path in planned_paths
                )
            new_size_gb = new_size_mb / 1024
            freed_gb = max(0, initial_size - new_size_gb)

            result["success"] = cleanup_result.returncode == 0
            result["output"] = cleanup_result.stdout
            result["error"] = cleanup_result.stderr
            result["returncode"] = cleanup_result.returncode
            result["space_freed_gb"] = round(freed_gb, 3)
            result["initial_size_gb"] = initial_size
            result["remaining_size_gb"] = round(new_size_gb, 3)

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def _is_allowed_protected_cleanup(service) -> bool:
        """Allow only the exact bounded Docker build-cache operation."""
        from .service_scanner import ServiceType

        return (
            service.service_type == ServiceType.DOCKER
            and service.cleanup_command
            == "docker builder prune --force --filter until=168h"
        )

    @staticmethod
    def _estimated_cleanup_gb(service) -> float:
        """Best available upper bound for a dry-run cleanup.

        A Docker service mixes active data, images, volumes and build cache.
        The targeted fixOS command only prunes old build cache, so reporting
        the whole Docker size as reclaimable would be dangerously misleading.
        """
        from .service_scanner import ServiceType

        if service.service_type == ServiceType.DOCKER:
            build_cache = service.details.get("usage", {}).get("Build Cache", {})
            return round(float(build_cache.get("reclaimable_gb", 0.0)), 3)
        return round(float(service.size_gb), 3)

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
                    "🐳 DOCKER — najpierw odzyskiwalne dane:",
                    "  docker system df",
                    "  # Pokazuje osobno SIZE i RECLAIMABLE",
                    "",
                    "  fixos cleanup -c docker --dry-run",
                    "  # Domyślnie: tylko cache buildów >7 dni",
                    "",
                    "  fixos cleanup --docker-old --days 30 --dry-run",
                    "  # Nieużywane obrazy (+ cache) starsze niż 30 dni",
                    "",
                    "  docker image prune -f",
                    "  # Usuwa tylko niepodpięte (dangling) obrazy",
                    "",
                    "⚠️  Wolumeny mogą zawierać bazy i pliki użytkownika.",
                    "    fixOS nigdy nie usuwa ich zbiorczo.",
                ]
            )

        elif service_type == ServiceType.OLLAMA:
            hints.extend(
                [
                    "🤖 OLLAMA CLEANUP:",
                    "  ollama list",
                    "  # See installed models",
                    "",
                    "  fixos cleanup --ollama-old --days 90 --dry-run",
                    "  # Modele niezmieniane od 90+ dni (pomija uruchomione)",
                    "",
                    "  ollama rm <model_name>",
                    "  # Remove specific model",
                    "",
                    "💡 Models can be 5-50 GB each",
                ]
            )

        elif service_type == ServiceType.JETBRAINS:
            hints.extend(
                [
                    "🧠 JETBRAINS CACHE:",
                    "  pgrep -af 'idea|pycharm|webstorm|jetbrains'",
                    "  # Najpierw zamknij IDE; fixOS odmówi czyszczenia, gdy działa",
                    "",
                    "  du -h --max-depth=2 ~/.cache/JetBrains | sort -h | tail -20",
                    "  # Pokazuje indeksy, runtime agentów i cache Toolbox",
                    "",
                    "💡 Ustawienia i projekty nie są w ~/.cache/JetBrains.",
                    "   Cache zostanie odbudowany, ale pierwsze uruchomienie IDE potrwa dłużej.",
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
            ServiceType.DOCKER: "Docker data (active and reclaimable, measured by daemon)",
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
            ServiceType.POETRY: "Poetry package cache",
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
        """Get a bounded cleanup command for a scanned service path.

        Protected data never gets a bulk-delete command.  Docker is the only
        exception because its command is deliberately limited to rebuildable
        build cache older than seven days; it does not touch images, running
        containers or volumes.
        """
        from .service_scanner import ServiceType

        protected_without_bulk_cleanup = {
            ServiceType.CONTAINERD,
            ServiceType.PODMAN,
            ServiceType.OLLAMA,
            ServiceType.LMSTUDIO,
            ServiceType.HUGGINGFACE,
            ServiceType.JUPYTER,
            ServiceType.MINIKUBE,
            ServiceType.APPIMAGE,
            ServiceType.VBOX,
            ServiceType.VMWARE,
        }
        if service_type in protected_without_bulk_cleanup:
            return ""

        if service_type in (ServiceType.VSCODE, ServiceType.CURSOR):
            if ServiceCleaner.get_risk_level(service_type, path) == "dangerous":
                return ""

        if service_type == ServiceType.STEAM:
            if ServiceCleaner.get_risk_level(service_type, path) == "dangerous":
                return ""

        commands = {
            # Containers
            ServiceType.DOCKER: "docker builder prune --force --filter until=168h",
            # JS/Node
            ServiceType.NPM: (
                "npm cache clean --force 2>/dev/null || true; "
                "rm -rf ~/.npm/_npx ~/.npm/_prebuilds"
            ),
            ServiceType.YARN: "yarn cache clean --all",
            ServiceType.PNPM: "pnpm store prune",
            # Python
            ServiceType.PIP: "pip cache purge || rm -rf ~/.cache/pip/*",
            ServiceType.CONDA: "conda clean --all -y",
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
            ServiceType.APT: "sudo apt-get clean && sudo apt-get autoclean",
            ServiceType.DNF: "sudo dnf clean all",
            ServiceType.PACMAN: "sudo pacman -Scc --noconfirm",
            ServiceType.YUM: "sudo yum clean all",
            ServiceType.ZYPPER: "sudo zypper clean --all",
            # Virtualization
            ServiceType.VAGRANT: "vagrant box prune --force",
            # Package managers
            ServiceType.NIX: "nix-collect-garbage -d || nix store gc",
            ServiceType.BREW: "brew cleanup --prune=all && brew autoremove",
            # Browsers
            ServiceType.CHROME: ServiceCleaner._chrome_cleanup_command(path),
            ServiceType.FIREFOX: "rm -rf ~/.cache/mozilla ~/.mozilla/firefox/*/cache2",
            ServiceType.EDGE: "rm -rf ~/.cache/microsoft-edge",
            # IDEs
            ServiceType.VSCODE: "rm -rf ~/.config/Code/Cache ~/.config/Code/CachedData",
            ServiceType.CURSOR: "rm -rf ~/.config/Cursor/Cache ~/.config/Cursor/CachedData",
            ServiceType.JETBRAINS: (
                "if pgrep -f 'idea|pycharm|webstorm|jetbrains' >/dev/null; "
                "then echo 'Zamknij wszystkie IDE JetBrains przed czyszczeniem' >&2; "
                "exit 2; else find ~/.cache/JetBrains -mindepth 1 -maxdepth 1 "
                "-exec rm -rf -- {} +; fi"
            ),
            # Cloud/ML
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
            ServiceType.THUMBNAILS: "rm -rf ~/.cache/thumbnails/* ~/.thumbnails/*",
            ServiceType.TRASH: "rm -rf ~/.local/share/Trash/* ~/.Trash/*",
            ServiceType.LOGS: "find ~/.cache/log ~/.local/state -name '*.log' -mtime +7 -delete 2>/dev/null; journalctl --vacuum-time=7d 2>/dev/null || true",
            ServiceType.NVIDIA: "rm -rf ~/.cache/nvidia ~/.nv/ComputeCache ~/.cache/mesa_shader_cache",
            ServiceType.UV: "uv cache clean",
            ServiceType.TORCH: "rm -rf ~/.cache/torch ~/.torch",
            ServiceType.BUN: "rm -rf ~/.bun/install/cache",
            ServiceType.PLAYWRIGHT: "rm -rf ~/.cache/ms-playwright ~/.cache/puppeteer",
            ServiceType.CCACHE: "ccache -C 2>/dev/null || rm -rf ~/.ccache; rm -rf ~/.cache/sccache",
            ServiceType.HELM: "helm cache cleanup 2>/dev/null || rm -rf ~/.cache/helm",
            ServiceType.STEAM: ServiceCleaner._steam_cleanup_command(path),
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
            ServiceType.NPM: (
                "npm cache ls 2>/dev/null; "
                "du -sh ~/.npm/_cacache ~/.npm/_npx ~/.npm/_prebuilds 2>/dev/null"
            ),
            ServiceType.YARN: "yarn cache list 2>/dev/null || du -sh ~/.cache/yarn",
            ServiceType.PNPM: (
                "pnpm store status 2>/dev/null || "
                "du -sh ~/.pnpm-store ~/.local/share/pnpm/store 2>/dev/null"
            ),
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
