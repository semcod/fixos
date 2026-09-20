"""Conservative optimization of stale Docker startup workloads.

The module deliberately separates evidence gathering from mutation.  Container
age is reported, but never makes a container actionable on its own.  A stale
candidate must have an auto-start restart policy and map unambiguously to a
clean Git repository whose latest commit is older than the requested limit.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Collection, Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from fixos.constants import DEFAULT_COMMAND_TIMEOUT

STARTUP_RESTART_POLICIES = frozenset({"always", "unless-stopped"})
COMPOSE_WORKING_DIR_LABEL = "com.docker.compose.project.working_dir"
TERMINAL_CONTAINER_STATES = frozenset({"created", "dead", "exited", "removing"})
DEFAULT_DOCKER_STALE_SERVICE_DAYS = 3

_SIZE_UNITS = {
    "B": 1,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
    "TIB": 1024**4,
}


def _parse_docker_percent(value: object) -> float | None:
    """Parse ``docker stats`` percentage strings like ``"0.52%"``."""
    if value is None:
        return None
    text = str(value).strip().rstrip("%")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_docker_size(value: object) -> int | None:
    """Parse ``docker`` human sizes (``"45.6MiB"``, ``"1.2GB"``, ``"0B"``)."""
    if value is None:
        return None
    text = str(value).strip().upper().replace(" ", "")
    for unit, multiplier in sorted(
        _SIZE_UNITS.items(), key=lambda item: -len(item[0])
    ):
        if text.endswith(unit):
            try:
                return int(float(text[: -len(unit)]) * multiplier)
            except ValueError:
                return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_docker_mem_usage(value: object) -> tuple[int | None, int | None]:
    """Split ``"45.6MiB / 1.5GiB"`` into (used, limit) byte counts."""
    if value is None:
        return None, None
    parts = str(value).split("/")
    used = _parse_docker_size(parts[0])
    limit = _parse_docker_size(parts[1]) if len(parts) > 1 else None
    return used, limit


class DockerStartupOptimizer:
    """Find and explicitly disable stale repository-backed Docker autostart.

    ``scan`` is read-only. ``optimize`` is also a dry run unless ``apply=True``
    and accepts only full IDs that were classified as candidates by a fresh
    scan.  The only possible Docker mutations are ``docker update
    --restart=no`` and, with another explicit opt-in, ``docker stop``.
    """

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        process_iter: Callable[[], Iterable[Any]] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._runner = runner or subprocess.run
        self._process_iter = process_iter or self._default_process_iter
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._git_root_cache: dict[str, str | None] = {}
        self._git_activity_cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _default_process_iter() -> Iterable[Any]:
        return psutil.process_iter(
            ["pid", "ppid", "create_time", "cmdline", "name"]
        )

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return self._runner(
            command,
            capture_output=True,
            text=True,
            timeout=DEFAULT_COMMAND_TIMEOUT,
        )

    @staticmethod
    def _error(completed: subprocess.CompletedProcess[str], fallback: str) -> str:
        return (completed.stderr or completed.stdout).strip() or fallback

    @staticmethod
    def _parse_time(value: object) -> datetime | None:
        if not value or str(value).startswith("0001-01-01"):
            return None
        normalized = str(value).strip().replace("Z", "+00:00")
        normalized = re.sub(r"(\.\d{6})\d+", r"\1", normalized)
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _list_inspected(self) -> list[dict[str, Any]]:
        try:
            listed = self._run(
                ["docker", "container", "ls", "--all", "--quiet", "--no-trunc"]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"docker container ls unavailable: {exc}") from exc
        if listed.returncode != 0:
            raise RuntimeError(self._error(listed, "docker container ls failed"))

        container_ids = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
        if not container_ids:
            return []
        try:
            inspected = self._run(["docker", "inspect", *container_ids])
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"docker inspect unavailable: {exc}") from exc
        if inspected.returncode != 0:
            raise RuntimeError(self._error(inspected, "docker inspect failed"))
        try:
            payload = json.loads(inspected.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("docker inspect returned invalid JSON") from exc
        if not isinstance(payload, list):
            raise TypeError("docker inspect returned a non-list payload")
        return [item for item in payload if isinstance(item, dict)]

    def _git_root(self, candidate: str) -> str | None:
        if candidate in self._git_root_cache:
            return self._git_root_cache[candidate]
        path = Path(candidate).expanduser()
        if not path.is_absolute() or path == Path("/"):
            self._git_root_cache[candidate] = None
            return None
        try:
            completed = self._run(
                ["git", "-C", os.fspath(path), "rev-parse", "--show-toplevel"]
            )
        except (OSError, subprocess.SubprocessError):
            self._git_root_cache[candidate] = None
            return None
        if completed.returncode != 0:
            self._git_root_cache[candidate] = None
            return None
        root = completed.stdout.strip()
        if not root or not Path(root).is_absolute() or Path(root) == Path("/"):
            self._git_root_cache[candidate] = None
            return None
        resolved = os.fspath(Path(root).resolve(strict=False))
        self._git_root_cache[candidate] = resolved
        return resolved

    def _repository_evidence(self, container: dict[str, Any]) -> dict[str, Any]:
        config = container.get("Config") or {}
        labels = config.get("Labels") or {} if isinstance(config, dict) else {}
        if not isinstance(labels, dict):
            labels = {}

        paths: list[tuple[str, str]] = []
        working_dir = labels.get(COMPOSE_WORKING_DIR_LABEL)
        if working_dir:
            paths.append(("compose-label", str(working_dir)))
        for mount in container.get("Mounts") or []:
            if not isinstance(mount, dict) or str(mount.get("Type")) != "bind":
                continue
            source = mount.get("Source")
            if source:
                paths.append(("bind-mount", str(source)))

        roots: dict[str, set[str]] = {}
        for source, path in paths:
            root = self._git_root(path)
            if root:
                roots.setdefault(root, set()).add(source)

        if not roots:
            return {
                "repository": None,
                "repository_sources": [],
                "repository_state": "not-found",
            }
        if len(roots) > 1:
            return {
                "repository": None,
                "repository_sources": [],
                "repository_state": "ambiguous",
                "repository_candidates": sorted(roots),
            }
        repository, sources = next(iter(roots.items()))
        return {
            "repository": repository,
            "repository_sources": sorted(sources),
            "repository_state": "confirmed",
        }

    def _git_activity(self, repository: str) -> dict[str, Any]:
        if repository in self._git_activity_cache:
            return self._git_activity_cache[repository]
        try:
            status = self._run(
                [
                    "git",
                    "-C",
                    repository,
                    "status",
                    "--porcelain",
                    "--untracked-files=normal",
                ]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            result = {"state": "error", "error": str(exc)}
            self._git_activity_cache[repository] = result
            return result
        if status.returncode != 0:
            result = {
                "state": "error",
                "error": self._error(status, "git status failed"),
            }
            self._git_activity_cache[repository] = result
            return result
        if status.stdout.strip():
            result = {"state": "dirty", "last_commit": None}
            self._git_activity_cache[repository] = result
            return result

        try:
            latest = self._run(
                ["git", "-C", repository, "log", "-1", "--format=%ct"]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            result = {"state": "error", "error": str(exc)}
            self._git_activity_cache[repository] = result
            return result
        if latest.returncode != 0 or not latest.stdout.strip().isdigit():
            result = {
                "state": "error",
                "error": self._error(latest, "git history unavailable"),
            }
            self._git_activity_cache[repository] = result
            return result
        committed = datetime.fromtimestamp(int(latest.stdout.strip()), timezone.utc)
        result = {"state": "clean", "last_commit": committed}
        self._git_activity_cache[repository] = result
        return result

    @staticmethod
    def _docker_exec_container(cmdline: Sequence[str]) -> str | None:
        if len(cmdline) < 3 or Path(cmdline[0]).name != "docker" or cmdline[1] != "exec":
            return None
        options_without_value = {
            "-d",
            "--detach",
            "-i",
            "--interactive",
            "-t",
            "--tty",
            "--privileged",
        }
        options_with_value = {
            "-e",
            "--env",
            "--env-file",
            "--detach-keys",
            "-u",
            "--user",
            "-w",
            "--workdir",
        }
        index = 2
        while index < len(cmdline):
            token = cmdline[index]
            if token in options_without_value or re.fullmatch(r"-[dit]+", token):
                index += 1
                continue
            if token in options_with_value:
                index += 2
                continue
            if token.startswith("--") and "=" in token:
                index += 1
                continue
            if token.startswith("-"):
                return None
            return token
        return None

    def _docker_exec_helpers(self) -> tuple[list[dict[str, Any]], str | None]:
        helpers: list[dict[str, Any]] = []
        now_epoch = self._now().astimezone(timezone.utc).timestamp()
        try:
            processes = self._process_iter()
            for process in processes:
                try:
                    info = process.info
                    cmdline = list(info.get("cmdline") or [])
                    container_ref = self._docker_exec_container(cmdline)
                    if not container_ref:
                        continue
                    created = float(info.get("create_time") or 0.0)
                    helpers.append(
                        {
                            "pid": int(info["pid"]),
                            "ppid": int(info.get("ppid") or 0),
                            "created": datetime.fromtimestamp(
                                created, timezone.utc
                            ).isoformat()
                            if created
                            else None,
                            "age_seconds": round(max(0.0, now_epoch - created), 1)
                            if created
                            else None,
                            "container_ref": container_ref,
                            "command": cmdline,
                        }
                    )
                except (KeyError, TypeError, ValueError, psutil.Error):
                    continue
        except (OSError, psutil.Error) as exc:
            return [], str(exc)
        return sorted(helpers, key=lambda item: item["pid"]), None

    @staticmethod
    def _matching_helpers(
        helpers: list[dict[str, Any]], container_id: str, name: str
    ) -> list[dict[str, Any]]:
        matches = []
        for helper in helpers:
            reference = helper["container_ref"]
            if reference == name or (
                len(reference) >= 12 and container_id.startswith(reference)
            ):
                matches.append(helper)
        return matches

    def _live_stats(
        self, container_ids: Collection[str]
    ) -> tuple[dict[str, dict[str, Any]], str | None]:
        """Collect instantaneous CPU/memory usage for running containers."""
        stats: dict[str, dict[str, Any]] = {}
        ids = [cid for cid in dict.fromkeys(container_ids) if cid]
        if not ids:
            return stats, None
        try:
            completed = self._run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{json .}}",
                    *ids,
                ]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return stats, str(exc)
        if completed.returncode != 0:
            return stats, self._error(completed, "docker stats failed")
        for line in completed.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            container_ref = str(row.get("Container") or row.get("ID") or "")
            used, limit = _parse_docker_mem_usage(row.get("MemUsage"))
            stats[container_ref] = {
                "cpu_percent": _parse_docker_percent(row.get("CPUPerc")),
                "memory_bytes": used,
                "memory_limit_bytes": limit,
                "memory_percent": _parse_docker_percent(row.get("MemPerc")),
            }
        return stats, None

    def _disk_footprint(
        self, candidates: list[dict[str, Any]], inspected: list[dict[str, Any]]
    ) -> tuple[dict[str, dict[str, Any]], str | None]:
        """Collect writable-layer and image sizes for stale candidates.

        ``disk_reclaimable_bytes`` counts the container's writable layer plus
        the image size only when no other container references that image.
        """
        footprint: dict[str, dict[str, Any]] = {}
        ids = [item["id"] for item in candidates]
        if not ids:
            return footprint, None

        image_usage: dict[str, int] = {}
        for container in inspected:
            image_id = str(container.get("Image") or "")
            if image_id:
                image_usage[image_id] = image_usage.get(image_id, 0) + 1

        try:
            sized = self._run(["docker", "inspect", "--size", *ids])
        except (OSError, subprocess.SubprocessError) as exc:
            return footprint, str(exc)
        if sized.returncode != 0:
            return footprint, self._error(sized, "docker inspect --size failed")
        try:
            sized_payload = json.loads(sized.stdout)
        except json.JSONDecodeError:
            return footprint, "docker inspect --size returned invalid JSON"

        image_ids = sorted(
            {
                str(item.get("Image") or "")
                for item in sized_payload
                if isinstance(item, dict) and item.get("Image")
            }
        )
        image_sizes: dict[str, int] = {}
        if image_ids:
            try:
                images = self._run(["docker", "image", "inspect", *image_ids])
            except (OSError, subprocess.SubprocessError) as exc:
                return footprint, str(exc)
            if images.returncode == 0:
                try:
                    for image in json.loads(images.stdout):
                        image_id = str(image.get("Id") or "")
                        size = image.get("Size")
                        if image_id and isinstance(size, (int, float)):
                            image_sizes[image_id] = int(size)
                except json.JSONDecodeError:
                    pass

        for item in sized_payload:
            if not isinstance(item, dict):
                continue
            container_id = str(item.get("Id") or "")
            image_id = str(item.get("Image") or "")
            size_rw = item.get("SizeRw")
            size_rootfs = item.get("SizeRootFs")
            image_size = image_sizes.get(image_id)
            shared = bool(image_id) and image_usage.get(image_id, 0) > 1
            reclaimable = 0
            if isinstance(size_rw, (int, float)):
                reclaimable += int(size_rw)
            if not shared and image_size is not None:
                reclaimable += image_size
            footprint[container_id] = {
                "size_rw_bytes": int(size_rw)
                if isinstance(size_rw, (int, float))
                else None,
                "size_rootfs_bytes": int(size_rootfs)
                if isinstance(size_rootfs, (int, float))
                else None,
                "image_id": image_id or None,
                "image_size_bytes": image_size,
                "image_shared": shared,
                "disk_reclaimable_bytes": reclaimable,
            }
        return footprint, None

    def scan(
        self, min_inactive_days: int = DEFAULT_DOCKER_STALE_SERVICE_DAYS
    ) -> dict[str, Any]:
        """Return evidence and stale candidates without changing Docker state."""
        if min_inactive_days < 1:
            raise ValueError("min_inactive_days must be >= 1")
        self._git_root_cache = {}
        self._git_activity_cache = {}
        inspected = self._list_inspected()
        helpers, helper_error = self._docker_exec_helpers()
        now = self._now().astimezone(timezone.utc)
        records: list[dict[str, Any]] = []

        for container in inspected:
            container_id = str(container.get("Id") or "")
            if not container_id:
                continue
            name = str(container.get("Name") or "").lstrip("/")
            host_config = container.get("HostConfig") or {}
            restart = host_config.get("RestartPolicy") or {}
            policy = str(restart.get("Name") or "no").lower()
            state = container.get("State") or {}
            status = str(state.get("Status") or "unknown")
            active = status not in TERMINAL_CONTAINER_STATES
            created = self._parse_time(container.get("Created"))
            started = self._parse_time(state.get("StartedAt"))
            repository = self._repository_evidence(container)
            git = (
                self._git_activity(repository["repository"])
                if repository["repository"] and policy in STARTUP_RESTART_POLICIES
                else {"state": "not-evaluated", "last_commit": None}
            )

            reasons: list[str] = []
            candidate = True
            if policy not in STARTUP_RESTART_POLICIES:
                candidate = False
                reasons.append("restart-policy-not-startup-enabled")
            repository_state = repository["repository_state"]
            if repository_state != "confirmed":
                candidate = False
                reasons.append(f"repository-{repository_state}")
            if policy in STARTUP_RESTART_POLICIES:
                if git["state"] == "dirty":
                    candidate = False
                    reasons.append("repository-dirty")
                elif git["state"] != "clean":
                    candidate = False
                    reasons.append("git-activity-unavailable")

            last_commit = git.get("last_commit")
            inactivity_days: float | None = None
            if isinstance(last_commit, datetime):
                inactivity_days = max(
                    0.0, (now - last_commit).total_seconds() / 86400
                )
                if inactivity_days < min_inactive_days:
                    candidate = False
                    reasons.append("repository-active")
            elif policy in STARTUP_RESTART_POLICIES:
                candidate = False
            if candidate:
                reasons.append("repository-inactive")

            matching_helpers = self._matching_helpers(helpers, container_id, name)
            records.append(
                {
                    "id": container_id,
                    "short_id": container_id[:12],
                    "name": name,
                    "status": status,
                    "running": status == "running",
                    "active": active,
                    "restart_policy": policy,
                    "created": created.isoformat() if created else None,
                    "started": started.isoformat() if started else None,
                    **repository,
                    "git_state": git["state"],
                    "git_error": git.get("error"),
                    "last_commit": last_commit.isoformat()
                    if isinstance(last_commit, datetime)
                    else None,
                    "inactivity_days": round(inactivity_days, 1)
                    if inactivity_days is not None
                    else None,
                    "docker_exec_helpers": matching_helpers,
                    "candidate": candidate,
                    "reasons": reasons,
                }
            )

        records.sort(key=lambda item: (not item["candidate"], item["name"]))
        candidates = [item for item in records if item["candidate"]]

        stats, stats_error = self._live_stats(
            item["id"] for item in candidates if item["running"]
        )
        footprint, footprint_error = self._disk_footprint(candidates, inspected)
        for item in candidates:
            live = stats.get(item["id"]) or stats.get(item["short_id"]) or {}
            disk = footprint.get(item["id"]) or {}
            item["resources"] = {
                "collected": bool(live or disk),
                "cpu_percent": live.get("cpu_percent"),
                "memory_bytes": live.get("memory_bytes"),
                "memory_limit_bytes": live.get("memory_limit_bytes"),
                "memory_percent": live.get("memory_percent"),
                "size_rw_bytes": disk.get("size_rw_bytes"),
                "size_rootfs_bytes": disk.get("size_rootfs_bytes"),
                "image_id": disk.get("image_id"),
                "image_size_bytes": disk.get("image_size_bytes"),
                "image_shared": disk.get("image_shared"),
                "disk_reclaimable_bytes": disk.get("disk_reclaimable_bytes"),
            }
        for item in records:
            item.setdefault("resources", None)

        def _sum(field: str, *, running_only: bool = False) -> float | None:
            values = [
                (item["resources"] or {}).get(field)
                for item in candidates
                if not running_only or item["running"]
            ]
            present = [value for value in values if isinstance(value, (int, float))]
            return sum(present) if present else None

        return {
            "service": "docker-startup",
            "read_only": True,
            "min_inactive_days": min_inactive_days,
            "containers": records,
            "candidates": candidates,
            "potential_savings": {
                "candidates": len(candidates),
                "running_candidates": sum(
                    1 for item in candidates if item["running"]
                ),
                "memory_bytes": _sum("memory_bytes", running_only=True),
                "cpu_percent": _sum("cpu_percent", running_only=True),
                "disk_bytes": _sum("disk_reclaimable_bytes"),
            },
            "stats_error": stats_error,
            "disk_footprint_error": footprint_error,
            "docker_exec_helper_count": len(helpers),
            "unmatched_docker_exec_helpers": [
                helper
                for helper in helpers
                if not any(
                    helper in record["docker_exec_helpers"] for record in records
                )
            ],
            "helper_scan_error": helper_error,
        }

    def _verify(self, container_id: str) -> dict[str, Any]:
        try:
            inspected = self._run(["docker", "inspect", container_id])
        except (OSError, subprocess.SubprocessError) as exc:
            return {"verified": False, "error": str(exc)}
        if inspected.returncode != 0:
            return {
                "verified": False,
                "error": self._error(inspected, "docker inspect failed"),
            }
        try:
            container = json.loads(inspected.stdout)[0]
            policy = container["HostConfig"]["RestartPolicy"]["Name"] or "no"
            status = container["State"]["Status"]
        except (IndexError, KeyError, TypeError, json.JSONDecodeError):
            return {"verified": False, "error": "invalid verification payload"}
        return {
            "verified": True,
            "restart_policy": str(policy).lower(),
            "status": str(status),
        }

    def optimize(
        self,
        container_ids: Collection[str],
        *,
        min_inactive_days: int = DEFAULT_DOCKER_STALE_SERVICE_DAYS,
        apply: bool = False,
        stop_running: bool = False,
        remove_containers: bool = False,
        remove_images: bool = False,
        stop_timeout_seconds: int = 10,
    ) -> dict[str, Any]:
        """Disable exact stale candidates and optionally stop/remove them.

        Removal is opt-in per call: ``remove_containers`` runs ``docker rm``
        after the container is stopped (never on a still-active container),
        and ``remove_images`` additionally runs ``docker rmi`` for images that
        the fresh scan did not mark as shared with other containers.
        A fresh scan revalidates repository state immediately before any
        mutation.
        """
        if stop_timeout_seconds < 1:
            raise ValueError("stop_timeout_seconds must be >= 1")
        if remove_images and not remove_containers:
            raise ValueError("remove_images requires remove_containers")
        selected = sorted({str(item) for item in container_ids})
        scan = self.scan(min_inactive_days=min_inactive_days)
        candidates = {item["id"]: item for item in scan["candidates"]}
        result: dict[str, Any] = {
            "service": "docker-startup",
            "dry_run": not apply,
            "stop_running": stop_running,
            "remove_containers": remove_containers,
            "remove_images": remove_images,
            "selected": selected,
            "planned": [],
            "changed": [],
            "failed": [],
            "success": False,
        }

        for container_id in selected:
            candidate = candidates.get(container_id)
            if candidate is None:
                result["failed"].append(
                    {
                        "id": container_id,
                        "error": "not an exact stale candidate in the fresh scan",
                    }
                )
                continue
            plan = {
                "id": container_id,
                "name": candidate["name"],
                "repository": candidate["repository"],
                "restart_policy": "no",
                "stop": bool(stop_running and candidate["active"]),
                "remove": bool(remove_containers),
                "remove_image": bool(
                    remove_images
                    and (candidate.get("resources") or {}).get("image_id")
                    and not (candidate.get("resources") or {}).get("image_shared")
                ),
                "expected_helper_exits": [
                    helper["pid"] for helper in candidate["docker_exec_helpers"]
                ]
                if stop_running
                else [],
            }
            result["planned"].append(plan)
            if not apply:
                continue

            try:
                updated = self._run(
                    ["docker", "update", "--restart=no", container_id]
                )
            except (OSError, subprocess.SubprocessError) as exc:
                result["failed"].append({**plan, "error": str(exc)})
                continue
            if updated.returncode != 0:
                result["failed"].append(
                    {
                        **plan,
                        "error": self._error(updated, "docker update failed"),
                    }
                )
                continue

            if plan["stop"]:
                try:
                    stopped = self._run(
                        [
                            "docker",
                            "stop",
                            "--time",
                            str(stop_timeout_seconds),
                            container_id,
                        ]
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    result["failed"].append(
                        {**plan, "restart_disabled": True, "error": str(exc)}
                    )
                    continue
                if stopped.returncode != 0:
                    result["failed"].append(
                        {
                            **plan,
                            "restart_disabled": True,
                            "error": self._error(stopped, "docker stop failed"),
                        }
                    )
                    continue

            verification = self._verify(container_id)
            policy_ok = verification.get("restart_policy") == "no"
            state_ok = not plan["stop"] or verification.get("status") in {
                "dead",
                "exited",
            }
            if not verification["verified"] or not policy_ok or not state_ok:
                result["failed"].append(
                    {**plan, "error": "post-action verification failed", **verification}
                )
                continue
            changed = {**plan, **verification}
            if plan["remove"]:
                self._apply_removal(candidate, changed)
            result["changed"].append(changed)

        result["success"] = not result["failed"]
        return result

    def _apply_removal(
        self, candidate: dict[str, Any], changed: dict[str, Any]
    ) -> None:
        """Run ``docker rm``/``docker rmi`` for an already verified change.

        Never removes a container that is still active, and never removes an
        image the scan marked as shared with another container.
        """
        container_id = changed["id"]
        changed["removed"] = False
        changed["image_removed"] = None
        if str(changed.get("status") or "") not in TERMINAL_CONTAINER_STATES:
            changed["remove_error"] = (
                "container still running; removal requires stop"
            )
            return
        try:
            removed = self._run(["docker", "rm", container_id])
        except (OSError, subprocess.SubprocessError) as exc:
            changed["remove_error"] = str(exc)
            return
        if removed.returncode != 0:
            changed["remove_error"] = self._error(removed, "docker rm failed")
            return
        changed["removed"] = True
        changed["status"] = "removed"

        resources = candidate.get("resources") or {}
        image_id = resources.get("image_id")
        if not changed["remove_image"] or not image_id:
            return
        try:
            rmi = self._run(["docker", "rmi", image_id])
        except (OSError, subprocess.SubprocessError) as exc:
            changed["image_error"] = str(exc)
            return
        if rmi.returncode == 0:
            changed["image_removed"] = True
        else:
            changed["image_removed"] = False
            changed["image_error"] = self._error(rmi, "docker rmi failed")
