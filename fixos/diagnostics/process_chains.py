"""Evidence-led diagnostics for fresh process chains.

The module deliberately separates observation from termination.  A young
process is not a blocker merely because it is young; findings become
actionable only when there is stronger evidence such as an older duplicate,
an uninterruptible task, resource pressure, or a direct file-lock wait.

Termination is dry-run by default and targets individual PIDs from leaves to
root.  It never signals a process group because unrelated applications can
share the group of a desktop session.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import psutil


DISK_SLEEP_STATES = {"D", "disk-sleep", psutil.STATUS_DISK_SLEEP}
PRIVILEGED_ACCOUNTS = {"root", "system", "local service", "network service"}


class ProcessChainSafetyError(RuntimeError):
    """Raised when a requested process-tree action fails a safety check."""


@dataclass(frozen=True, slots=True)
class ProcessRecord:
    """Stable process metadata captured at one point in time."""

    pid: int
    ppid: int
    name: str
    cmdline: tuple[str, ...]
    create_time: float
    status: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    username: str = ""

    def age_seconds(self, now: float) -> float:
        return max(0.0, now - self.create_time)

    @property
    def signature(self) -> tuple[str, tuple[str, ...]]:
        """Conservative signature used to find older exact duplicates."""

        command = self.cmdline or (self.name,)
        return self.name.casefold(), command

    def to_dict(self, *, now: float | None = None) -> dict[str, object]:
        captured_at = time.time() if now is None else now
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "name": self.name,
            "cmdline": list(self.cmdline),
            "create_time": self.create_time,
            "age_seconds": round(self.age_seconds(captured_at), 3),
            "status": self.status,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "username": self.username,
        }


@dataclass(frozen=True, slots=True)
class FileLockWait:
    """One kernel-reported file-lock dependency."""

    waiter_pid: int
    holder_pid: int
    lock_id: str
    resource: str


@dataclass(frozen=True, slots=True)
class ProcessChainFinding:
    """A fresh process subtree and the evidence associated with it."""

    root: ProcessRecord
    members: tuple[ProcessRecord, ...]
    older_duplicate_roots: tuple[ProcessRecord, ...]
    blocking_older_pids: tuple[int, ...]
    score: int
    confidence: str
    reason_codes: tuple[str, ...]
    protected: bool

    @property
    def actionable(self) -> bool:
        return not self.protected and self.confidence in {"likely", "confirmed"}

    def to_dict(self, *, now: float | None = None) -> dict[str, object]:
        captured_at = time.time() if now is None else now
        return {
            "root": self.root.to_dict(now=captured_at),
            "members": [item.to_dict(now=captured_at) for item in self.members],
            "member_pids": [item.pid for item in self.members],
            "older_duplicate_root_pids": [
                item.pid for item in self.older_duplicate_roots
            ],
            "blocking_older_pids": list(self.blocking_older_pids),
            "score": self.score,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "protected": self.protected,
            "actionable": self.actionable,
        }


@dataclass(frozen=True, slots=True)
class TerminationResult:
    """Result of a dry run or an attempted tree termination."""

    root_pid: int
    target_pids: tuple[int, ...]
    terminated_pids: tuple[int, ...]
    surviving_pids: tuple[int, ...]
    escalated_pids: tuple[int, ...]
    errors: tuple[str, ...]
    dry_run: bool

    @property
    def success(self) -> bool:
        return not self.errors and (self.dry_run or not self.surviving_pids)


def collect_processes(*, sample_seconds: float = 0.1) -> list[ProcessRecord]:
    """Collect a best-effort process snapshot using the existing psutil dependency."""

    processes: list[psutil.Process] = []
    attrs = ["pid", "ppid", "name", "cmdline", "create_time", "status", "username"]
    for process in psutil.process_iter(attrs):
        try:
            process.cpu_percent(None)
            processes.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sample_seconds > 0:
        time.sleep(sample_seconds)

    records: list[ProcessRecord] = []
    for process in processes:
        try:
            info = process.as_dict(attrs=attrs)
            records.append(
                ProcessRecord(
                    pid=int(info["pid"]),
                    ppid=int(info.get("ppid") or 0),
                    name=str(info.get("name") or ""),
                    cmdline=tuple(str(arg) for arg in (info.get("cmdline") or ())),
                    create_time=float(info.get("create_time") or 0.0),
                    status=str(info.get("status") or ""),
                    cpu_percent=max(0.0, float(process.cpu_percent(None))),
                    memory_percent=max(0.0, float(process.memory_percent())),
                    username=str(info.get("username") or ""),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return records


def parse_proc_locks(text: str) -> list[FileLockWait]:
    """Parse blocked lock requests from Linux ``/proc/locks`` content.

    A normal line identifies the holder.  A following line with ``->`` and
    the same lock ID identifies a waiter blocked by that holder.
    """

    holders: dict[str, int] = {}
    waits: list[FileLockWait] = []
    for raw_line in text.splitlines():
        fields = raw_line.split()
        if len(fields) < 7:
            continue
        lock_id = fields[0].rstrip(":")
        blocked = fields[1] == "->"
        pid_index = 5 if blocked else 4
        resource_index = 6 if blocked else 5
        try:
            pid = int(fields[pid_index])
        except (IndexError, ValueError):
            continue
        if not blocked:
            holders[lock_id] = pid
            continue
        holder_pid = holders.get(lock_id)
        if holder_pid is None:
            continue
        waits.append(
            FileLockWait(
                waiter_pid=pid,
                holder_pid=holder_pid,
                lock_id=lock_id,
                resource=fields[resource_index],
            )
        )
    return waits


def read_linux_lock_waits(path: Path = Path("/proc/locks")) -> list[FileLockWait]:
    """Read Linux lock dependencies; return no evidence on other/denied systems."""

    try:
        return parse_proc_locks(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return []


def _children_by_parent(records: Iterable[ProcessRecord]) -> dict[int, list[int]]:
    children: dict[int, list[int]] = defaultdict(list)
    for record in records:
        children[record.ppid].append(record.pid)
    return children


def _subtree_pids(
    root_pid: int,
    by_pid: dict[int, ProcessRecord],
    children: dict[int, list[int]],
    *,
    allowed_pids: set[int] | None = None,
) -> list[int]:
    result: list[int] = []
    pending = [root_pid]
    seen: set[int] = set()
    while pending:
        pid = pending.pop()
        if pid in seen or pid not in by_pid:
            continue
        if allowed_pids is not None and pid not in allowed_pids:
            continue
        seen.add(pid)
        result.append(pid)
        pending.extend(children.get(pid, ()))
    return result


def _depths(root_pid: int, children: dict[int, list[int]]) -> dict[int, int]:
    depths = {root_pid: 0}
    pending = [root_pid]
    while pending:
        pid = pending.pop()
        for child_pid in children.get(pid, ()):
            if child_pid in depths:
                continue
            depths[child_pid] = depths[pid] + 1
            pending.append(child_pid)
    return depths


class ProcessChainInspector:
    """List, analyse and explicitly terminate recent process subtrees."""

    def __init__(
        self,
        *,
        snapshot_provider: Callable[[], Sequence[ProcessRecord]] | None = None,
        lock_wait_provider: Callable[[], Sequence[FileLockWait]] | None = None,
        clock: Callable[[], float] = time.time,
        self_pid: int | None = None,
        terminator: Callable[[int, bool], None] | None = None,
        identity_provider: Callable[[int], float | None] | None = None,
        alive_provider: Callable[[int, float], bool] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        allow_privileged: bool = False,
    ) -> None:
        self._snapshot_provider = snapshot_provider or collect_processes
        self._lock_wait_provider = lock_wait_provider or read_linux_lock_waits
        self._clock = clock
        self._self_pid = os.getpid() if self_pid is None else self_pid
        self._terminator = terminator or self._default_terminator
        self._identity_provider = identity_provider or self._default_identity
        self._alive_provider = alive_provider or self._default_alive
        self._sleeper = sleeper
        self._allow_privileged = allow_privileged

    @staticmethod
    def _default_terminator(pid: int, force: bool) -> None:
        process = psutil.Process(pid)
        process.kill() if force else process.terminate()

    @staticmethod
    def _default_identity(pid: int) -> float | None:
        try:
            return psutil.Process(pid).create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None

    @staticmethod
    def _default_alive(pid: int, expected_create_time: float) -> bool:
        try:
            process = psutil.Process(pid)
            return (
                abs(process.create_time() - expected_create_time) < 0.001
                and process.is_running()
                and process.status() != psutil.STATUS_ZOMBIE
            )
        except psutil.AccessDenied:
            return True
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return False

    def snapshot(self) -> list[ProcessRecord]:
        return list(self._snapshot_provider())

    def list_recent(
        self,
        *,
        max_age_seconds: float = 20 * 60,
        limit: int | None = None,
        records: Sequence[ProcessRecord] | None = None,
    ) -> list[ProcessRecord]:
        """Return newest processes first, without classifying them as blockers."""

        now = self._clock()
        snapshot = list(records) if records is not None else self.snapshot()
        recent = [
            record
            for record in snapshot
            if 0 <= record.age_seconds(now) <= max_age_seconds
        ]
        recent.sort(key=lambda item: (item.create_time, item.pid), reverse=True)
        return recent if limit is None else recent[: max(0, limit)]

    def _protected_pids(self, by_pid: dict[int, ProcessRecord]) -> set[int]:
        protected = {0, 1, 2, self._self_pid}
        if not self._allow_privileged:
            protected.update(
                record.pid
                for record in by_pid.values()
                if record.username.casefold() in PRIVILEGED_ACCOUNTS
            )
        pid = self._self_pid
        while pid in by_pid:
            parent = by_pid[pid].ppid
            if parent <= 0 or parent in protected:
                break
            protected.add(parent)
            pid = parent
        return protected

    def find_suspicious_chains(
        self,
        *,
        max_age_seconds: float = 20 * 60,
        records: Sequence[ProcessRecord] | None = None,
        lock_waits: Sequence[FileLockWait] | None = None,
        suspicious_only: bool = True,
    ) -> list[ProcessChainFinding]:
        """Reconstruct fresh trees and attach explainable blocking evidence."""

        snapshot = list(records) if records is not None else self.snapshot()
        by_pid = {record.pid: record for record in snapshot}
        children = _children_by_parent(snapshot)
        now = self._clock()
        recent_pids = {
            record.pid
            for record in snapshot
            if 0 <= record.age_seconds(now) <= max_age_seconds
        }
        roots = [
            by_pid[pid]
            for pid in recent_pids
            if by_pid[pid].ppid not in recent_pids
        ]
        waits = (
            list(lock_waits)
            if lock_waits is not None
            else list(self._lock_wait_provider())
        )
        protected_pids = self._protected_pids(by_pid)
        findings: list[ProcessChainFinding] = []

        for root in roots:
            member_pids = set(
                _subtree_pids(
                    root.pid,
                    by_pid,
                    children,
                    allowed_pids=recent_pids,
                )
            )
            members = tuple(
                sorted(
                    (by_pid[pid] for pid in member_pids),
                    key=lambda item: (item.create_time, item.pid),
                )
            )
            duplicates = tuple(
                sorted(
                    (
                        item
                        for item in snapshot
                        if item.pid not in member_pids
                        and item.create_time < root.create_time
                        and item.signature == root.signature
                    ),
                    key=lambda item: item.create_time,
                    reverse=True,
                )
            )
            blocking_older = sorted(
                {
                    wait.waiter_pid
                    for wait in waits
                    if wait.holder_pid in member_pids
                    and wait.waiter_pid not in member_pids
                    and wait.waiter_pid in by_pid
                    and by_pid[wait.waiter_pid].create_time < root.create_time
                }
            )

            score = 0
            reasons: list[str] = []
            if blocking_older:
                score += 8
                reasons.append("holds-lock-needed-by-older-process")
            if duplicates:
                score += 4
                reasons.append("duplicates-older-process-chain")
            has_disk_sleep = any(
                item.status in DISK_SLEEP_STATES for item in members
            )
            if has_disk_sleep:
                score += 4
                reasons.append("contains-uninterruptible-task")
            has_high_cpu = sum(item.cpu_percent for item in members) >= 100.0
            if has_high_cpu:
                score += 2
                reasons.append("high-cpu-chain")
            has_high_memory = (
                sum(item.memory_percent for item in members) >= 20.0
            )
            if has_high_memory:
                score += 2
                reasons.append("high-memory-chain")
            is_multi_process = len(members) >= 3
            if is_multi_process:
                score += 1
                reasons.append("multi-process-chain")

            if blocking_older:
                confidence = "confirmed"
            elif duplicates and (has_disk_sleep or has_high_cpu or has_high_memory):
                confidence = "likely"
            elif has_disk_sleep or (
                is_multi_process
                and (bool(duplicates) or has_high_cpu or has_high_memory)
            ):
                confidence = "possible"
            else:
                confidence = "informational"

            finding = ProcessChainFinding(
                root=root,
                members=members,
                older_duplicate_roots=duplicates,
                blocking_older_pids=tuple(blocking_older),
                score=score,
                confidence=confidence,
                reason_codes=tuple(reasons),
                protected=bool(member_pids & protected_pids),
            )
            if not suspicious_only or confidence != "informational":
                findings.append(finding)

        findings.sort(
            key=lambda item: (item.score, item.root.create_time, item.root.pid),
            reverse=True,
        )
        return findings

    def terminate_chain(
        self,
        finding: ProcessChainFinding,
        *,
        dry_run: bool = True,
        grace_seconds: float = 3.0,
        escalate: bool = False,
        require_actionable: bool = True,
    ) -> TerminationResult:
        """Terminate one selected tree after identity and ancestry checks.

        ``escalate`` is deliberately opt-in.  When enabled, only surviving PIDs
        whose creation time still matches are force-killed.
        """

        if finding.protected:
            raise ProcessChainSafetyError(
                "selected chain contains FixOS, its ancestor, or a system root"
            )
        if not dry_run and require_actionable and not finding.actionable:
            raise ProcessChainSafetyError(
                "selected chain lacks likely or confirmed blocking evidence"
            )

        snapshot = self.snapshot()
        by_pid = {record.pid: record for record in snapshot}
        current_root = by_pid.get(finding.root.pid)
        if current_root is None:
            raise ProcessChainSafetyError("selected root no longer exists")
        if abs(current_root.create_time - finding.root.create_time) >= 0.001:
            raise ProcessChainSafetyError(
                "selected root PID was reused by a different process"
            )

        children = _children_by_parent(snapshot)
        target_pids = _subtree_pids(current_root.pid, by_pid, children)
        protected = self._protected_pids(by_pid)
        if set(target_pids) & protected:
            raise ProcessChainSafetyError(
                "current tree now contains FixOS, its ancestor, or a system root"
            )
        depths = _depths(current_root.pid, children)
        target_pids.sort(key=lambda pid: (depths.get(pid, 0), pid), reverse=True)
        targets = tuple(target_pids)

        if dry_run:
            return TerminationResult(
                root_pid=current_root.pid,
                target_pids=targets,
                terminated_pids=(),
                surviving_pids=targets,
                escalated_pids=(),
                errors=(),
                dry_run=True,
            )

        errors: list[str] = []
        for pid in targets:
            expected = by_pid[pid].create_time
            if not self._identity_matches(pid, expected):
                errors.append(f"pid {pid}: identity changed before termination")
                continue
            try:
                self._terminator(pid, False)
            except (OSError, psutil.Error) as exc:
                errors.append(f"pid {pid}: {exc}")

        deadline = self._clock() + max(0.0, grace_seconds)
        survivors = self._survivors(targets, by_pid)
        while survivors and self._clock() < deadline:
            self._sleeper(min(0.1, max(0.0, deadline - self._clock())))
            survivors = self._survivors(targets, by_pid)

        escalated: list[int] = []
        if survivors and escalate:
            for pid in survivors:
                expected = by_pid[pid].create_time
                if not self._identity_matches(pid, expected):
                    errors.append(f"pid {pid}: identity changed before escalation")
                    continue
                try:
                    self._terminator(pid, True)
                    escalated.append(pid)
                except (OSError, psutil.Error) as exc:
                    errors.append(f"pid {pid}: escalation failed: {exc}")
            survivors = self._survivors(targets, by_pid)

        survivor_set = set(survivors)
        return TerminationResult(
            root_pid=current_root.pid,
            target_pids=targets,
            terminated_pids=tuple(pid for pid in targets if pid not in survivor_set),
            surviving_pids=tuple(survivors),
            escalated_pids=tuple(escalated),
            errors=tuple(errors),
            dry_run=False,
        )

    def _survivors(
        self,
        target_pids: Sequence[int],
        by_pid: dict[int, ProcessRecord],
    ) -> list[int]:
        return [
            pid
            for pid in target_pids
            if self._alive_provider(pid, by_pid[pid].create_time)
        ]

    def _identity_matches(self, pid: int, expected_create_time: float) -> bool:
        actual = self._identity_provider(pid)
        return actual is not None and abs(actual - expected_create_time) < 0.001
