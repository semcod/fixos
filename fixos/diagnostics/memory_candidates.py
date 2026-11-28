"""Evidence-led detection and opt-in closure of idle high-memory GUI apps.

Scanning is read-only and ranks processes by ``RSS + VmSwap`` alongside CPU
idle time and process age. Termination reuses ``OrphanedWorkloadCleaner`` PID,
``create_time``, container-cgroup, and ancestry protections and never runs unless
explicitly requested by the caller.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from fixos.diagnostics.orphaned_workloads import OrphanedWorkloadCleaner
from fixos.diagnostics.process_chains import ProcessRecord

DEFAULT_MIN_APP_AGE_HOURS = 1.0
DEFAULT_MIN_IDLE_HOURS = 1.0
DEFAULT_MAX_IDLE_CPU_PERCENT = 1.0
DEFAULT_MIN_CANDIDATE_MEMORY_BYTES = 256 * 1024 * 1024

_VMSWAP_PATTERN = re.compile(r"^VmSwap:\s*(\d+)\s*kB\b", re.IGNORECASE | re.MULTILINE)
_INTERPRETER_NAMES = frozenset(
    {"python", "python3", "node", "nodejs", "ruby", "bash", "sh", "zsh", "fish"}
)

IDLE_GUI_APP_ALLOWLIST: frozenset[str] = frozenset(
    {
        "baobab",
        "filelight",
        "qdirstat",
        "gnome-system-monitor",
        "plasma-systemmonitor",
        "gnome-logs",
        "eog",
        "eom",
        "loupe",
        "gwenview",
        "gthumb",
        "ristretto",
        "feh",
        "sxiv",
        "nsxiv",
        "viewnior",
        "nomacs",
        "evince",
        "papers",
        "okular",
        "zathura",
        "atril",
        "xreader",
        "mupdf",
        "qpdfview",
        "vlc",
        "totem",
        "mpv",
        "celluloid",
        "gnome-calculator",
        "kcalc",
        "gnome-font-viewer",
        "gnome-characters",
    }
)

PROTECTED_AGENT_AND_SERVICE_NAMES: frozenset[str] = frozenset(
    {
        "codex",
        "claude",
        "gemini",
        "aider",
        "cline",
        "cursor",
        "cursor-agent",
        "antigravity",
        "opencode",
        "droid",
        "windsurf",
        "goose",
        "ollama",
        "llama-server",
        "vllm",
        "subactor",
        "onedev",
        "heyasa",
        "fixos",
        "pycharm",
        "code",
        "idea",
        "systemd",
        "dbus-daemon",
        "sshd",
        "dockerd",
        "containerd",
        "postgres",
        "mysqld",
        "redis-server",
        "nginx",
        "pipewire",
        "wireplumber",
        "pulseaudio",
        "gnome-shell",
        "kwin",
        "mutter",
        "xorg",
        "xwayland",
        "bash",
        "zsh",
        "fish",
        "tmux",
        "screen",
    }
)


def parse_proc_status_vmswap_bytes(text: str) -> int:
    """Parse the Linux ``/proc/<pid>/status`` ``VmSwap`` value in bytes."""
    if not text:
        return 0
    match = _VMSWAP_PATTERN.search(text)
    if not match:
        return 0
    try:
        return max(0, int(match.group(1)) * 1024)
    except ValueError:
        return 0


def read_process_vmswap_bytes(pid: int) -> int:
    """Read Linux ``/proc/<pid>/status`` ``VmSwap`` safely across platforms."""
    try:
        status_text = Path(f"/proc/{pid}/status").read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return 0
    return parse_proc_status_vmswap_bytes(status_text)


def read_process_cpu_time_seconds(pid: int) -> float | None:
    """Return cumulative user + system CPU seconds for ``pid``, or ``None``."""
    try:
        times = psutil.Process(pid).cpu_times()
        return max(0.0, float(times.user) + float(times.system))
    except (psutil.Error, OSError, AttributeError, TypeError, ValueError):
        return None


def capture_memory_snapshot() -> dict[str, int | float]:
    """Capture host RAM and swap totals in bytes without raising on OS errors."""
    try:
        memory = psutil.virtual_memory()
        ram_total = int(memory.total)
        ram_available = int(memory.available)
        ram_used = int(memory.used)
        ram_percent = float(memory.percent)
    except (psutil.Error, OSError, AttributeError):
        ram_total = 0
        ram_available = 0
        ram_used = 0
        ram_percent = 0.0

    try:
        swap = psutil.swap_memory()
        swap_total = int(swap.total)
        swap_used = int(swap.used)
        swap_percent = float(swap.percent)
    except (psutil.Error, OSError, AttributeError):
        swap_total = 0
        swap_used = 0
        swap_percent = 0.0

    return {
        "ram_total_bytes": ram_total,
        "ram_available_bytes": ram_available,
        "ram_used_bytes": ram_used,
        "ram_percent": round(ram_percent, 1),
        "swap_total_bytes": swap_total,
        "swap_used_bytes": swap_used,
        "swap_percent": round(swap_percent, 1),
    }


def has_critical_memory_pressure(snapshot: dict[str, Any] | None) -> bool:
    """Return True when the quick snapshot reports critical RAM or swap pressure."""
    if not isinstance(snapshot, dict) or not snapshot:
        return False

    for alert in snapshot.get("alerts") or ():
        if (
            isinstance(alert, dict)
            and alert.get("resource") in {"memory", "swap"}
            and alert.get("severity") == "critical"
        ):
            return True

    resources = snapshot.get("resources")
    if not isinstance(resources, dict):
        return False
    context = snapshot.get("context") or {}
    thresholds = context.get("thresholds") if isinstance(context, dict) else {}
    thresholds = thresholds if isinstance(thresholds, dict) else {}

    memory = resources.get("memory") or {}
    if isinstance(memory, dict):
        mem_critical = float(thresholds.get("memory_usage_critical", 90))
        if float(memory.get("percent") or 0.0) >= mem_critical:
            return True

    swap = resources.get("swap") or {}
    if isinstance(swap, dict):
        swap_total = int(swap.get("total_bytes") or 0)
        swap_critical = float(thresholds.get("swap_usage_critical", 90))
        if swap_total > 0 and float(swap.get("percent") or 0.0) >= swap_critical:
            return True

    return False


class IdleMemoryCandidateCleaner(OrphanedWorkloadCleaner):
    """Rank processes by RSS + VmSwap and safely close opted-in idle GUI apps."""

    def __init__(
        self,
        *,
        vmswap_provider: Callable[[int], int] | None = None,
        cpu_time_provider: Callable[[int], float | None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._vmswap_provider = vmswap_provider or read_process_vmswap_bytes
        self._cpu_time_provider = cpu_time_provider or read_process_cpu_time_seconds

    @staticmethod
    def _executable_name(record: ProcessRecord) -> str:
        raw = Path(record.cmdline[0]).name if record.cmdline else record.name
        return raw.casefold().removesuffix(".exe")

    @staticmethod
    def _is_system_service_cgroup(value: str | None) -> bool:
        return bool(value and "/system.slice/" in value.casefold())

    @classmethod
    def _is_protected_executable_or_wrapper(cls, record: ProcessRecord) -> bool:
        proc_name = record.name.casefold().removesuffix(".exe")
        exe_name = cls._executable_name(record)
        if (
            proc_name in PROTECTED_AGENT_AND_SERVICE_NAMES
            or exe_name in PROTECTED_AGENT_AND_SERVICE_NAMES
        ):
            return True

        base_exe = exe_name.rstrip("0123456789.")
        if (exe_name in _INTERPRETER_NAMES or base_exe in {"python", "node"}) and record.cmdline:
            args = record.cmdline[1:]
            for idx, arg in enumerate(args):
                if arg == "-m" and idx + 1 < len(args):
                    mod = args[idx + 1].split(".", 1)[0].casefold()
                    if mod in PROTECTED_AGENT_AND_SERVICE_NAMES:
                        return True
                    break
                if arg.startswith("-"):
                    continue
                script_name = Path(arg).name.casefold()
                for suffix in (".py", ".mjs", ".cjs", ".js"):
                    if script_name.endswith(suffix):
                        script_name = script_name[: -len(suffix)]
                        break
                if script_name in PROTECTED_AGENT_AND_SERVICE_NAMES:
                    return True
                break
        return False

    def _protected_pids(self, by_pid: dict[int, ProcessRecord]) -> set[int]:
        protected = super()._protected_pids(by_pid)
        for record in by_pid.values():
            if self._is_ide_agent(record, by_pid):
                protected.add(record.pid)
                continue
            if self._is_protected_executable_or_wrapper(record):
                protected.add(record.pid)
                continue
            if self._is_system_service_cgroup(self._cgroup_provider(record.pid)):
                protected.add(record.pid)
        return protected

    @classmethod
    def _has_allowlisted_ancestor(
        cls, record: ProcessRecord, by_pid: dict[int, ProcessRecord]
    ) -> bool:
        seen = {record.pid}
        parent_pid = record.ppid
        while parent_pid in by_pid and parent_pid not in seen:
            seen.add(parent_pid)
            parent = by_pid[parent_pid]
            if cls._executable_name(parent) in IDLE_GUI_APP_ALLOWLIST:
                return True
            parent_pid = parent.ppid
        return False

    def scan_memory(
        self,
        *,
        top_limit: int = 5,
        min_age_hours: float = DEFAULT_MIN_APP_AGE_HOURS,
        min_idle_hours: float = DEFAULT_MIN_IDLE_HOURS,
        max_cpu_percent: float = DEFAULT_MAX_IDLE_CPU_PERCENT,
        min_memory_bytes: int = DEFAULT_MIN_CANDIDATE_MEMORY_BYTES,
    ) -> dict[str, Any]:
        """Return processes ranked by RSS + VmSwap and idle GUI opt-in candidates."""
        if top_limit < 1:
            raise ValueError("top_limit must be >= 1")
        if min_age_hours < 0 or min_idle_hours < 0 or max_cpu_percent < 0:
            raise ValueError("idle scan thresholds must be non-negative")
        if min_memory_bytes < 0:
            raise ValueError("min_memory_bytes must be non-negative")

        records = list(self._process_provider())
        by_pid = {record.pid: record for record in records}
        children = self._children(records)
        protected = self._protected_pids(by_pid)
        now_epoch = self._now().astimezone(timezone.utc).timestamp()

        per_pid_rss: dict[int, int] = {}
        per_pid_swap: dict[int, int] = {}
        per_pid_cpu_time: dict[int, float | None] = {}
        ranked_entries: list[dict[str, Any]] = []

        for record in records:
            rss_bytes = max(0, int(self._rss_provider(record.pid)))
            vmswap_bytes = max(0, int(self._vmswap_provider(record.pid)))
            total_bytes = rss_bytes + vmswap_bytes
            cpu_time = self._cpu_time_provider(record.pid)
            age_seconds = max(0.0, now_epoch - record.create_time)
            idle_seconds = (
                0.0
                if record.cpu_percent > max_cpu_percent
                else max(0.0, age_seconds - (cpu_time or 0.0))
            )
            per_pid_rss[record.pid] = rss_bytes
            per_pid_swap[record.pid] = vmswap_bytes
            per_pid_cpu_time[record.pid] = cpu_time

            exe_name = self._executable_name(record)
            ranked_entries.append(
                {
                    "pid": record.pid,
                    "name": record.name,
                    "executable": exe_name,
                    "command": list(record.cmdline) if record.cmdline else [record.name],
                    "create_time": record.create_time,
                    "rss_bytes": rss_bytes,
                    "vmswap_bytes": vmswap_bytes,
                    "total_memory_bytes": total_bytes,
                    "cpu_percent": round(record.cpu_percent, 1),
                    "cpu_time_seconds": round(cpu_time, 1)
                    if cpu_time is not None
                    else None,
                    "age_hours": round(age_seconds / 3600, 1),
                    "idle_hours": round(idle_seconds / 3600, 1),
                    "idle": record.cpu_percent <= max_cpu_percent,
                    "protected": record.pid in protected,
                    "allowlisted_gui_app": exe_name in IDLE_GUI_APP_ALLOWLIST,
                }
            )

        ranked_entries.sort(
            key=lambda item: (
                -item["total_memory_bytes"],
                -item["vmswap_bytes"],
                -item["age_hours"],
                item["pid"],
            )
        )

        candidates: list[dict[str, Any]] = []
        rejected_gui_apps: list[dict[str, Any]] = []

        for record in records:
            exe_name = self._executable_name(record)
            if exe_name not in IDLE_GUI_APP_ALLOWLIST:
                continue
            if self._has_allowlisted_ancestor(record, by_pid):
                continue

            members = self._tree(record.pid, children)
            member_set = set(members)
            rss_bytes = sum(per_pid_rss.get(pid, 0) for pid in members)
            vmswap_bytes = sum(per_pid_swap.get(pid, 0) for pid in members)
            total_memory_bytes = rss_bytes + vmswap_bytes

            tree_cpu_percent = max(
                (by_pid[pid].cpu_percent for pid in members if pid in by_pid),
                default=record.cpu_percent,
            )
            member_cpu_times = [
                per_pid_cpu_time[pid]
                for pid in members
                if per_pid_cpu_time.get(pid) is not None
            ]
            tree_cpu_time = sum(member_cpu_times) if member_cpu_times else None

            age_seconds = max(0.0, now_epoch - record.create_time)
            age_hours = age_seconds / 3600
            idle_seconds = (
                0.0
                if tree_cpu_percent > max_cpu_percent
                else max(0.0, age_seconds - (tree_cpu_time or 0.0))
            )
            idle_hours = idle_seconds / 3600

            containerized = any(
                self._is_container_cgroup(self._cgroup_provider(pid)) for pid in members
            )
            is_protected = bool(member_set & protected) or containerized

            reasons: list[str] = []
            if containerized:
                reasons.append("containerized-process")
            if member_set & protected:
                reasons.append("protected-process-or-ancestry")
            if tree_cpu_percent > max_cpu_percent:
                reasons.append("cpu-active")
            if age_hours < min_age_hours:
                reasons.append("process-too-young")
            if idle_hours < min_idle_hours:
                reasons.append("insufficient-idle-time")
            if total_memory_bytes < min_memory_bytes:
                reasons.append("below-memory-threshold")

            is_candidate = not reasons
            if is_candidate:
                reasons.append("idle-long-running-gui-app")

            started_at = datetime.fromtimestamp(
                record.create_time, tz=timezone.utc
            ).isoformat()
            entry = {
                "kind": "idle-gui-app",
                "root_pid": record.pid,
                "create_time": record.create_time,
                "started_at": started_at,
                "name": record.name,
                "executable": exe_name,
                "command": list(record.cmdline) if record.cmdline else [record.name],
                "member_pids": list(members),
                "process_count": len(members),
                "rss_bytes": rss_bytes,
                "vmswap_bytes": vmswap_bytes,
                "total_memory_bytes": total_memory_bytes,
                "reclaimable_memory_bytes": total_memory_bytes,
                "cpu_percent": round(tree_cpu_percent, 1),
                "cpu_time_seconds": round(tree_cpu_time, 1)
                if tree_cpu_time is not None
                else None,
                "age_hours": round(age_hours, 1),
                "idle_hours": round(idle_hours, 1),
                "containerized": containerized,
                "protected": is_protected,
                "candidate": is_candidate,
                "reason": "idle-long-running-gui-app" if is_candidate else reasons[0],
                "reasons": reasons,
            }
            if is_candidate:
                candidates.append(entry)
            else:
                rejected_gui_apps.append(entry)

        candidates.sort(
            key=lambda item: (
                -item["total_memory_bytes"],
                -item["vmswap_bytes"],
                -item["age_hours"],
                item["root_pid"],
            )
        )
        estimated_reclaimable = sum(
            item["reclaimable_memory_bytes"] for item in candidates
        )
        return {
            "service": "idle-memory-candidates",
            "read_only": True,
            "top_processes": ranked_entries[:top_limit],
            "candidates": candidates,
            "rejected_gui_apps": rejected_gui_apps,
            "estimated_reclaimable_bytes": estimated_reclaimable,
        }

    def close_candidates(
        self,
        *,
        process_identities: Collection[tuple[int, float]] = (),
        apply: bool = False,
        grace_seconds: float = 3.0,
        force: bool = False,
        min_age_hours: float = DEFAULT_MIN_APP_AGE_HOURS,
        min_idle_hours: float = DEFAULT_MIN_IDLE_HOURS,
        max_cpu_percent: float = DEFAULT_MAX_IDLE_CPU_PERCENT,
        min_memory_bytes: int = DEFAULT_MIN_CANDIDATE_MEMORY_BYTES,
    ) -> dict[str, Any]:
        """Revalidate and close only exact opted-in idle GUI candidates."""
        if grace_seconds < 0:
            raise ValueError("grace_seconds must be non-negative")

        scan = self.scan_memory(
            min_age_hours=min_age_hours,
            min_idle_hours=min_idle_hours,
            max_cpu_percent=max_cpu_percent,
            min_memory_bytes=min_memory_bytes,
        )
        by_pid = {int(item["root_pid"]): item for item in scan["candidates"]}

        planned: list[dict[str, Any]] = []
        closed: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        for raw_pid, raw_create_time in sorted(
            {(int(pid), float(ct)) for pid, ct in process_identities}
        ):
            candidate = by_pid.get(raw_pid)
            if (
                candidate is None
                or abs(float(candidate["create_time"]) - raw_create_time) >= 0.001
            ):
                failed.append(
                    {
                        "kind": "idle-gui-app",
                        "root_pid": raw_pid,
                        "create_time": raw_create_time,
                        "error": "not an eligible idle candidate in the fresh scan",
                    }
                )
                continue
            if not apply:
                planned.append(candidate)
                continue
            changed = self._apply_process(
                candidate,
                grace_seconds=grace_seconds,
                force=force,
            )
            (closed if changed.get("success") else failed).append(changed)

        return {
            "service": "idle-memory-candidates",
            "dry_run": not apply,
            "planned": planned,
            "closed": closed,
            "failed": failed,
            "success": not failed,
        }
