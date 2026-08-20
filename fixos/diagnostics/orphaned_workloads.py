"""Evidence-led cleanup for workloads whose development project disappeared.

Scanning is always read-only. Applying a selection can only disable Docker
restart policies, stop exact containers, or terminate exact process trees after
PID identity and ancestry checks. It never removes Docker objects, volumes,
images, networks, project directories, or files.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from fixos.constants import DEFAULT_COMMAND_TIMEOUT
from fixos.diagnostics.process_chains import ProcessRecord, collect_processes


COMPOSE_WORKING_DIR_LABEL = "com.docker.compose.project.working_dir"
STARTUP_RESTART_POLICIES = frozenset({"always", "unless-stopped"})
TERMINAL_CONTAINER_STATES = frozenset({"created", "dead", "exited", "removing"})
DEFAULT_ORPHANED_PROJECT_DAYS = 3
DEFAULT_STALE_PROCESS_HOURS = 12
CONTAINER_CGROUP_PATTERN = re.compile(
    r"(?:^|/)(?:docker|libpod|cri-containerd)[-/][0-9a-f]{12,64}"
    r"(?:\.scope)?(?:/|$)",
    re.IGNORECASE,
)


class OrphanedWorkloadSafetyError(RuntimeError):
    """Raised when an exact cleanup target no longer satisfies safety checks."""


class OrphanedWorkloadCleaner:
    """Find and explicitly clean missing-project Docker and process workloads."""

    def __init__(
        self,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        process_provider: Callable[[], Sequence[ProcessRecord]] | None = None,
        connection_provider: Callable[[], Iterable[Any]] | None = None,
        cgroup_provider: Callable[[int], str | None] | None = None,
        cwd_provider: Callable[[int], str | None] | None = None,
        rss_provider: Callable[[int], int] | None = None,
        identity_provider: Callable[[int], float | None] | None = None,
        terminator: Callable[[int, bool], None] | None = None,
        alive_provider: Callable[[int, float], bool] | None = None,
        path_exists: Callable[[str], bool] = os.path.isdir,
        now: Callable[[], datetime] | None = None,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
        self_pid: int | None = None,
    ) -> None:
        self._runner = runner or subprocess.run
        self._process_provider = process_provider or collect_processes
        self._connection_provider = connection_provider or self._connections
        self._cgroup_provider = cgroup_provider or self._process_cgroup
        self._cwd_provider = cwd_provider or self._process_cwd
        self._rss_provider = rss_provider or self._process_rss
        self._identity_provider = identity_provider or self._process_identity
        self._terminator = terminator or self._terminate
        self._alive_provider = alive_provider or self._is_alive
        self._path_exists = path_exists
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._clock = clock
        self._sleeper = sleeper
        self._self_pid = os.getpid() if self_pid is None else self_pid

    @staticmethod
    def _connections() -> Iterable[Any]:
        try:
            return psutil.net_connections(kind="tcp")
        except (OSError, psutil.Error):
            return ()

    @staticmethod
    def _process_cwd(pid: int) -> str | None:
        try:
            return psutil.Process(pid).cwd()
        except (psutil.Error, OSError):
            return None

    @staticmethod
    def _process_cgroup(pid: int) -> str | None:
        try:
            return Path(f"/proc/{pid}/cgroup").read_text(
                encoding="utf-8", errors="replace"
            )
        except (OSError, ValueError):
            return None

    @staticmethod
    def _is_container_cgroup(value: str | None) -> bool:
        if not value:
            return False
        normalized = value.casefold()
        return "/kubepods" in normalized or bool(
            CONTAINER_CGROUP_PATTERN.search(normalized)
        )

    @staticmethod
    def _process_rss(pid: int) -> int:
        try:
            return int(psutil.Process(pid).memory_info().rss)
        except (psutil.Error, OSError):
            return 0

    @staticmethod
    def _process_identity(pid: int) -> float | None:
        try:
            return psutil.Process(pid).create_time()
        except (psutil.Error, OSError):
            return None

    @staticmethod
    def _terminate(pid: int, force: bool) -> None:
        process = psutil.Process(pid)
        process.kill() if force else process.terminate()

    @staticmethod
    def _is_alive(pid: int, expected_create_time: float) -> bool:
        try:
            process = psutil.Process(pid)
            return (
                abs(process.create_time() - expected_create_time) < 0.001
                and process.is_running()
                and process.status() != psutil.STATUS_ZOMBIE
            )
        except psutil.AccessDenied:
            return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            return False

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
        if "." in normalized:
            prefix, suffix = normalized.split(".", 1)
            zone_index = max(suffix.find("+"), suffix.find("-"))
            zone = suffix[zone_index:] if zone_index >= 0 else ""
            fraction = suffix[:zone_index] if zone_index >= 0 else suffix
            normalized = f"{prefix}.{fraction[:6]}{zone}"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _list_containers(self) -> list[dict[str, Any]]:
        try:
            listed = self._run(
                ["docker", "container", "ls", "--all", "--quiet", "--no-trunc"]
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"docker container ls unavailable: {exc}") from exc
        if listed.returncode != 0:
            raise RuntimeError(self._error(listed, "docker container ls failed"))
        container_ids = [line for line in listed.stdout.splitlines() if line]
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
            raise RuntimeError("docker inspect returned a non-list payload")
        return [item for item in payload if isinstance(item, dict)]

    def _scan_docker(self, min_age_days: int) -> list[dict[str, Any]]:
        now = self._now().astimezone(timezone.utc)
        records: list[dict[str, Any]] = []
        for container in self._list_containers():
            container_id = str(container.get("Id") or "")
            if not container_id:
                continue
            config = container.get("Config") or {}
            labels = config.get("Labels") or {} if isinstance(config, dict) else {}
            working_dir = str(labels.get(COMPOSE_WORKING_DIR_LABEL) or "")
            host_config = container.get("HostConfig") or {}
            restart = host_config.get("RestartPolicy") or {}
            policy = str(restart.get("Name") or "no").lower()
            state = container.get("State") or {}
            status = str(state.get("Status") or "unknown")
            created = self._parse_time(container.get("Created"))
            age_days = (
                max(0.0, (now - created).total_seconds() / 86400)
                if created
                else None
            )
            absolute = bool(working_dir) and Path(working_dir).is_absolute()
            safe_path = absolute and Path(working_dir) != Path("/")
            missing = safe_path and not self._path_exists(working_dir)
            reasons: list[str] = []
            if policy not in STARTUP_RESTART_POLICIES:
                reasons.append("restart-policy-not-startup-enabled")
            if not working_dir:
                reasons.append("compose-working-directory-unavailable")
            elif not safe_path:
                reasons.append("compose-working-directory-unsafe")
            elif not missing:
                reasons.append("compose-working-directory-exists")
            if age_days is None:
                reasons.append("container-age-unavailable")
            elif age_days < min_age_days:
                reasons.append("container-too-young")
            candidate = (
                policy in STARTUP_RESTART_POLICIES
                and missing
                and age_days is not None
                and age_days >= min_age_days
            )
            if candidate:
                reasons.append("compose-working-directory-missing")
            records.append(
                {
                    "kind": "docker",
                    "id": container_id,
                    "short_id": container_id[:12],
                    "name": str(container.get("Name") or "").lstrip("/"),
                    "compose_project": str(labels.get("com.docker.compose.project") or ""),
                    "working_dir": working_dir or None,
                    "created": created.isoformat() if created else None,
                    "age_days": round(age_days, 1) if age_days is not None else None,
                    "status": status,
                    "active": status not in TERMINAL_CONTAINER_STATES,
                    "restart_policy": policy,
                    "candidate": candidate,
                    "reasons": reasons,
                }
            )
        return sorted(records, key=lambda item: (not item["candidate"], item["name"]))

    @staticmethod
    def _children(records: Sequence[ProcessRecord]) -> dict[int, list[int]]:
        children: dict[int, list[int]] = defaultdict(list)
        for record in records:
            children[record.ppid].append(record.pid)
        return children

    @staticmethod
    def _tree(root_pid: int, children: dict[int, list[int]]) -> tuple[int, ...]:
        found: list[int] = []
        pending = [root_pid]
        seen: set[int] = set()
        while pending:
            pid = pending.pop()
            if pid in seen:
                continue
            seen.add(pid)
            found.append(pid)
            pending.extend(children.get(pid, ()))
        return tuple(found)

    @staticmethod
    def _command(record: ProcessRecord) -> str:
        return " ".join(record.cmdline or (record.name,))

    @classmethod
    def _is_ide_agent(cls, record: ProcessRecord, by_pid: dict[int, ProcessRecord]) -> bool:
        command = cls._command(record).casefold()
        parent = by_pid.get(record.ppid)
        parent_command = cls._command(parent).casefold() if parent else ""
        return "cursor-agent" in command and " acp" in command and "pycharm" in parent_command

    @staticmethod
    def _is_dev_server(record: ProcessRecord) -> bool:
        command = record.cmdline or (record.name,)
        executable = Path(command[0]).name.casefold() if command else ""
        if executable == "php" and "-S" in command:
            return True
        if executable == "node":
            return any("server" in Path(arg).name.casefold() and arg.endswith(".mjs") for arg in command[1:])
        return False

    def _protected_pids(self, by_pid: dict[int, ProcessRecord]) -> set[int]:
        protected = {0, 1, 2, self._self_pid}
        protected.update(
            record.pid
            for record in by_pid.values()
            if record.username.casefold() in {"root", "system", "local service", "network service"}
        )
        pid = self._self_pid
        while pid in by_pid:
            parent = by_pid[pid].ppid
            if parent <= 0 or parent in protected:
                break
            protected.add(parent)
            pid = parent
        for record in by_pid.values():
            command = self._command(record).casefold()
            if ("/bin/pycharm" in command and "stdiomcpserver" not in command) or Path(
                (record.cmdline or (record.name,))[0]
            ).name.casefold() == "codex":
                protected.add(record.pid)
        return protected

    @staticmethod
    def _connection_evidence(
        connections: Iterable[Any], member_pids: set[int]
    ) -> tuple[int, list[int]]:
        established = 0
        ports: set[int] = set()
        for connection in connections:
            if getattr(connection, "pid", None) not in member_pids:
                continue
            status = str(getattr(connection, "status", "")).upper()
            if status == "ESTABLISHED":
                established += 1
            if status == "LISTEN":
                local = getattr(connection, "laddr", None)
                port = getattr(local, "port", None)
                if port is None and isinstance(local, tuple) and len(local) >= 2:
                    port = local[1]
                if isinstance(port, int):
                    ports.add(port)
        return established, sorted(ports)

    def _scan_processes(self, min_process_hours: float) -> list[dict[str, Any]]:
        records = list(self._process_provider())
        by_pid = {record.pid: record for record in records}
        children = self._children(records)
        protected = self._protected_pids(by_pid)
        now_epoch = self._now().astimezone(timezone.utc).timestamp()
        connections = list(self._connection_provider())
        containerized_pids = {
            record.pid
            for record in records
            if self._is_container_cgroup(self._cgroup_provider(record.pid))
        }
        candidates: list[dict[str, Any]] = []
        ide_member_pids: set[int] = set()

        roots: list[tuple[str, ProcessRecord]] = []
        for record in records:
            age_hours = max(0.0, now_epoch - record.create_time) / 3600
            if age_hours < min_process_hours:
                continue
            if self._is_ide_agent(record, by_pid):
                roots.append(("ide-agent", record))

        for kind, root in roots:
            members = self._tree(root.pid, children)
            member_set = set(members)
            ide_member_pids.update(member_set)
            established, ports = self._connection_evidence(connections, member_set)
            candidates.append(
                self._process_record(
                    kind,
                    root,
                    members,
                    by_pid,
                    protected,
                    containerized_pids,
                    established,
                    ports,
                    now_epoch,
                )
            )

        for record in records:
            age_hours = max(0.0, now_epoch - record.create_time) / 3600
            if (
                age_hours < min_process_hours
                or record.pid in ide_member_pids
                or not self._is_dev_server(record)
            ):
                continue
            members = self._tree(record.pid, children)
            member_set = set(members)
            established, ports = self._connection_evidence(connections, member_set)
            if established:
                continue
            candidates.append(
                self._process_record(
                    "dev-server",
                    record,
                    members,
                    by_pid,
                    protected,
                    containerized_pids,
                    established,
                    ports,
                    now_epoch,
                )
            )

        return sorted(candidates, key=lambda item: (item["kind"], -item["age_hours"]))

    def _process_record(
        self,
        kind: str,
        root: ProcessRecord,
        members: tuple[int, ...],
        by_pid: dict[int, ProcessRecord],
        protected: set[int],
        containerized_pids: set[int],
        established: int,
        ports: list[int],
        now_epoch: float,
    ) -> dict[str, Any]:
        member_set = set(members)
        containerized = bool(member_set & containerized_pids)
        is_protected = bool(member_set & protected) or containerized
        return {
            "kind": kind,
            "root_pid": root.pid,
            "create_time": root.create_time,
            "name": root.name,
            "command": list(root.cmdline),
            "cwd": self._cwd_provider(root.pid),
            "age_hours": round(max(0.0, now_epoch - root.create_time) / 3600, 1),
            "member_pids": list(members),
            "process_count": len(members),
            "memory_mb": round(
                sum(self._rss_provider(pid) for pid in members) / 1024 / 1024,
                1,
            ),
            "established_connections": established,
            "listen_ports": ports,
            "containerized": containerized,
            "protected": is_protected,
            "candidate": not is_protected,
            "reason": "containerized-process"
            if containerized
            else (
                "stale-pycharm-agent-tree"
                if kind == "ide-agent"
                else "client-free-development-server"
            ),
        }

    def scan(
        self,
        *,
        min_age_days: int = DEFAULT_ORPHANED_PROJECT_DAYS,
        min_process_hours: float = DEFAULT_STALE_PROCESS_HOURS,
    ) -> dict[str, Any]:
        """Return exact orphan evidence without changing Docker or processes."""
        if min_age_days < 1:
            raise ValueError("min_age_days must be >= 1")
        if min_process_hours < 1:
            raise ValueError("min_process_hours must be >= 1")
        docker = self._scan_docker(min_age_days)
        processes = self._scan_processes(min_process_hours)
        return {
            "service": "orphaned-projects",
            "read_only": True,
            "min_age_days": min_age_days,
            "min_process_hours": min_process_hours,
            "docker": docker,
            "processes": processes,
            "docker_candidates": [item for item in docker if item["candidate"]],
            "process_candidates": [item for item in processes if item["candidate"]],
            "protected_processes": [item for item in processes if item["protected"]],
        }

    def _verify_container(self, container_id: str) -> dict[str, Any]:
        inspected = self._run(["docker", "inspect", container_id])
        if inspected.returncode != 0:
            return {"verified": False, "error": self._error(inspected, "docker inspect failed")}
        try:
            item = json.loads(inspected.stdout)[0]
            policy = str(item["HostConfig"]["RestartPolicy"]["Name"] or "no").lower()
            status = str(item["State"]["Status"])
        except (IndexError, KeyError, TypeError, json.JSONDecodeError):
            return {"verified": False, "error": "invalid verification payload"}
        return {"verified": True, "restart_policy": policy, "status": status}

    def _apply_docker(self, candidate: dict[str, Any], stop_timeout: int) -> dict[str, Any]:
        container_id = candidate["id"]
        updated = self._run(["docker", "update", "--restart=no", container_id])
        if updated.returncode != 0:
            return {**candidate, "error": self._error(updated, "docker update failed")}
        if candidate["active"]:
            stopped = self._run(
                ["docker", "stop", "--time", str(stop_timeout), container_id]
            )
            if stopped.returncode != 0:
                return {
                    **candidate,
                    "restart_disabled": True,
                    "error": self._error(stopped, "docker stop failed"),
                }
        verification = self._verify_container(container_id)
        state_ok = not candidate["active"] or verification.get("status") in {"dead", "exited"}
        if not verification.get("verified") or verification.get("restart_policy") != "no" or not state_ok:
            return {**candidate, **verification, "error": "post-action verification failed"}
        return {**candidate, **verification}

    @staticmethod
    def _depths(root_pid: int, children: dict[int, list[int]]) -> dict[int, int]:
        depths = {root_pid: 0}
        pending = [root_pid]
        while pending:
            pid = pending.pop()
            for child in children.get(pid, ()):
                if child in depths:
                    continue
                depths[child] = depths[pid] + 1
                pending.append(child)
        return depths

    def _apply_process(
        self,
        candidate: dict[str, Any],
        *,
        grace_seconds: float,
        force: bool,
    ) -> dict[str, Any]:
        root_pid = int(candidate["root_pid"])
        expected_root = float(candidate["create_time"])
        actual_root = self._identity_provider(root_pid)
        if actual_root is None or abs(actual_root - expected_root) >= 0.001:
            return {**candidate, "error": "root PID identity changed"}
        records = list(self._process_provider())
        by_pid = {record.pid: record for record in records}
        root = by_pid.get(root_pid)
        if root is None or abs(root.create_time - expected_root) >= 0.001:
            return {**candidate, "error": "selected root no longer exists"}
        children = self._children(records)
        members = list(self._tree(root_pid, children))
        containerized = [
            pid
            for pid in members
            if self._is_container_cgroup(self._cgroup_provider(pid))
        ]
        if containerized:
            return {
                **candidate,
                "containerized_pids": containerized,
                "error": "current tree intersects a container runtime",
            }
        protected = self._protected_pids(by_pid)
        if set(members) & protected:
            return {**candidate, "error": "current tree intersects protected processes"}
        depths = self._depths(root_pid, children)
        members.sort(key=lambda pid: (depths.get(pid, 0), pid), reverse=True)
        errors: list[str] = []
        for pid in members:
            expected = by_pid[pid].create_time
            actual = self._identity_provider(pid)
            if actual is None or abs(actual - expected) >= 0.001:
                errors.append(f"pid {pid}: identity changed")
                continue
            try:
                self._terminator(pid, False)
            except (OSError, psutil.Error) as exc:
                errors.append(f"pid {pid}: {exc}")
        deadline = self._clock() + max(0.0, grace_seconds)
        survivors = [pid for pid in members if self._alive_provider(pid, by_pid[pid].create_time)]
        while survivors and self._clock() < deadline:
            self._sleeper(min(0.1, max(0.0, deadline - self._clock())))
            survivors = [pid for pid in members if self._alive_provider(pid, by_pid[pid].create_time)]
        escalated: list[int] = []
        if survivors and force:
            for pid in survivors:
                expected = by_pid[pid].create_time
                actual = self._identity_provider(pid)
                if actual is None or abs(actual - expected) >= 0.001:
                    errors.append(f"pid {pid}: identity changed before escalation")
                    continue
                try:
                    self._terminator(pid, True)
                    escalated.append(pid)
                except (OSError, psutil.Error) as exc:
                    errors.append(f"pid {pid}: escalation failed: {exc}")
            survivors = [pid for pid in members if self._alive_provider(pid, by_pid[pid].create_time)]
        return {
            **candidate,
            "target_pids": members,
            "surviving_pids": survivors,
            "escalated_pids": escalated,
            "errors": errors,
            "success": not survivors and not errors,
        }

    def cleanup(
        self,
        *,
        docker_ids: Collection[str] = (),
        process_identities: Collection[tuple[int, float]] = (),
        min_age_days: int = DEFAULT_ORPHANED_PROJECT_DAYS,
        min_process_hours: float = DEFAULT_STALE_PROCESS_HOURS,
        apply: bool = False,
        force_processes: bool = False,
        stop_timeout_seconds: int = 10,
        grace_seconds: float = 3.0,
    ) -> dict[str, Any]:
        """Revalidate and apply only exact selected orphan candidates."""
        if stop_timeout_seconds < 1 or grace_seconds < 0:
            raise ValueError("cleanup timeouts are invalid")
        scan = self.scan(
            min_age_days=min_age_days,
            min_process_hours=min_process_hours,
        )
        docker_candidates = {item["id"]: item for item in scan["docker_candidates"]}
        process_candidates = {
            (int(item["root_pid"]), float(item["create_time"])): item
            for item in scan["process_candidates"]
        }
        result: dict[str, Any] = {
            "service": "orphaned-projects",
            "dry_run": not apply,
            "docker_changed": [],
            "processes_changed": [],
            "failed": [],
        }
        for container_id in sorted(set(docker_ids)):
            candidate = docker_candidates.get(container_id)
            if candidate is None:
                result["failed"].append(
                    {"kind": "docker", "id": container_id, "error": "not an exact candidate in the fresh scan"}
                )
            elif apply:
                changed = self._apply_docker(candidate, stop_timeout_seconds)
                (result["failed"] if changed.get("error") else result["docker_changed"]).append(changed)
        for identity in sorted(set(process_identities)):
            candidate = process_candidates.get((int(identity[0]), float(identity[1])))
            if candidate is None:
                result["failed"].append(
                    {"kind": "process", "root_pid": identity[0], "error": "not an exact candidate in the fresh scan"}
                )
            elif apply:
                changed = self._apply_process(
                    candidate,
                    grace_seconds=grace_seconds,
                    force=force_processes,
                )
                (result["processes_changed"] if changed.get("success") else result["failed"]).append(changed)
        result["success"] = not result["failed"]
        return result
