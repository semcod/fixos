"""Bezpieczne zwalnianie nieużywanych sieci Docker i kontrola puli adresowej."""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from collections.abc import Collection
from datetime import datetime, timezone
from typing import Any, Callable

from fixos.constants import DEFAULT_COMMAND_TIMEOUT


PROTECTED_DOCKER_NETWORKS = frozenset({"bridge", "host", "none"})


class DockerNetworkCleaner:
    """Usuwa wyłącznie sieci bez endpointów i testuje pulę adresową.

    Kandydaci pochodzą z filtra Dockera ``dangling=true``. Każda sieć jest
    dodatkowo sprawdzana przez ``docker network inspect``; sieci wbudowane i
    sieci z endpointami są zawsze pomijane. Jeśli w trakcie operacji pojawi się
    endpoint, sam daemon odrzuci ``docker network rm``.
    """

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._runner = runner or subprocess.run
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return self._runner(
            command,
            capture_output=True,
            text=True,
            timeout=DEFAULT_COMMAND_TIMEOUT,
        )

    @staticmethod
    def _parse_created(value: str) -> datetime:
        """Parsuj czas Dockera, także z nanosekundową częścią ułamkową."""
        normalized = value.strip().replace("Z", "+00:00")
        normalized = re.sub(r"(\.\d{6})\d+", r"\1", normalized)
        created = datetime.fromisoformat(normalized)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created.astimezone(timezone.utc)

    def list_unused(
        self,
        min_age_days: int = 0,
        *,
        compose_projects: Collection[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Zwróć niestandardowe sieci bez endpointów.

        Gdy przekazano ``compose_projects``, uwzględniane są wyłącznie
        sieci z dokładnie pasującą etykietą projektu Docker Compose.
        Brak etykiety nie jest zgadywany po nazwie sieci.
        """
        if min_age_days < 0:
            raise ValueError("days must be >= 0")
        requested_projects = (
            {str(name) for name in compose_projects}
            if compose_projects is not None
            else None
        )

        try:
            listed = self._run(
                ["docker", "network", "ls", "--filter", "dangling=true", "--quiet"]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"docker network ls unavailable: {exc}") from exc
        if listed.returncode != 0:
            message = (listed.stderr or listed.stdout).strip()
            raise RuntimeError(message or "docker network ls failed")

        network_ids = [
            item.strip() for item in listed.stdout.splitlines() if item.strip()
        ]
        if not network_ids:
            return []

        try:
            inspected = self._run(["docker", "network", "inspect", *network_ids])
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"docker network inspect unavailable: {exc}") from exc
        if inspected.returncode != 0:
            message = (inspected.stderr or inspected.stdout).strip()
            raise RuntimeError(message or "docker network inspect failed")

        try:
            payload = json.loads(inspected.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("docker network inspect returned invalid JSON") from exc

        now = self._now().astimezone(timezone.utc)
        candidates: list[dict[str, Any]] = []
        for network in payload:
            name = str(network.get("Name") or "")
            network_id = str(network.get("Id") or "")
            containers = network.get("Containers") or {}
            if not network_id or name in PROTECTED_DOCKER_NETWORKS or containers:
                continue

            labels = network.get("Labels") or {}
            if not isinstance(labels, dict):
                labels = {}
            compose_project = str(labels.get("com.docker.compose.project") or "")
            if (
                requested_projects is not None
                and compose_project not in requested_projects
            ):
                continue

            ipam = network.get("IPAM") or {}
            ipam_configs = (ipam.get("Config") or []) if isinstance(ipam, dict) else []
            subnets = [
                str(config.get("Subnet"))
                for config in ipam_configs
                if isinstance(config, dict) and config.get("Subnet")
            ]

            created_text = str(network.get("Created") or "")
            try:
                created = self._parse_created(created_text)
            except (TypeError, ValueError):
                continue
            age_days = max(0.0, (now - created).total_seconds() / 86400)
            if age_days < min_age_days:
                continue

            candidates.append(
                {
                    "id": network_id,
                    "short_id": network_id[:12],
                    "name": name,
                    "driver": str(network.get("Driver") or ""),
                    "scope": str(network.get("Scope") or ""),
                    "compose_project": compose_project or None,
                    "subnets": subnets,
                    "created": created.isoformat(),
                    "age_days": round(age_days, 1),
                }
            )

        return sorted(candidates, key=lambda item: (item["created"], item["name"]))

    def probe_address_pool(self) -> dict[str, Any]:
        """Utwórz i usuń tymczasową sieć, potwierdzając dostępność puli."""
        name = f"fixos-address-pool-probe-{uuid.uuid4().hex[:12]}"
        try:
            created = self._run(
                [
                    "docker",
                    "network",
                    "create",
                    "--label",
                    "dev.fixos.cleanup-probe=true",
                    name,
                ]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "available": False,
                "probe": name,
                "removed": False,
                "error": str(exc),
            }
        if created.returncode != 0:
            return {
                "available": False,
                "probe": name,
                "removed": False,
                "error": (created.stderr or created.stdout).strip(),
            }

        try:
            removed = self._run(["docker", "network", "rm", name])
        except (OSError, subprocess.SubprocessError) as exc:
            return {
                "available": False,
                "probe": name,
                "removed": False,
                "error": str(exc),
            }
        return {
            "available": removed.returncode == 0,
            "probe": name,
            "removed": removed.returncode == 0,
            "error": ""
            if removed.returncode == 0
            else (removed.stderr or removed.stdout).strip(),
        }

    def cleanup(
        self,
        *,
        min_age_days: int = 0,
        dry_run: bool = False,
        verify_pool: bool = True,
        compose_projects: Collection[str] | None = None,
        network_ids: Collection[str] | None = None,
    ) -> dict[str, Any]:
        """Usuń dokładnie wykryte sieci i opcjonalnie sprawdź pulę adresową."""
        result: dict[str, Any] = {
            "service": "docker-networks",
            "dry_run": dry_run,
            "success": False,
            "min_age_days": int(min_age_days),
            "compose_projects": (
                sorted({str(name) for name in compose_projects})
                if compose_projects is not None
                else None
            ),
            "requested_network_ids": (
                sorted({str(network_id) for network_id in network_ids})
                if network_ids is not None
                else None
            ),
            "candidates": [],
            "removed": [],
            "failed": [],
            "recovered_network_slots": 0,
            "pool_probe": {
                "available": None,
                "removed": None,
                "error": "skipped in dry-run" if dry_run else "not requested",
            },
        }

        try:
            if compose_projects is None:
                candidates = self.list_unused(min_age_days=min_age_days)
            else:
                candidates = self.list_unused(
                    min_age_days=min_age_days,
                    compose_projects=compose_projects,
                )
        except (RuntimeError, ValueError) as exc:
            result["error"] = str(exc)
            return result
        if network_ids is not None:
            requested_ids = {str(network_id) for network_id in network_ids}
            candidates = [
                network for network in candidates if network["id"] in requested_ids
            ]
        result["candidates"] = candidates

        if dry_run:
            result["success"] = True
            return result

        for network in candidates:
            try:
                removed = self._run(["docker", "network", "rm", network["id"]])
            except (OSError, subprocess.SubprocessError) as exc:
                result["failed"].append({**network, "error": str(exc)})
                continue
            if removed.returncode == 0:
                result["removed"].append(network)
            else:
                result["failed"].append(
                    {
                        **network,
                        "error": (removed.stderr or removed.stdout).strip(),
                    }
                )

        result["recovered_network_slots"] = len(result["removed"])
        if verify_pool:
            result["pool_probe"] = self.probe_address_pool()

        probe_ok = not verify_pool or result["pool_probe"]["available"] is True
        result["success"] = not result["failed"] and probe_ok
        return result
