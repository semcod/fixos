"""Diagnose and recover a shared JetBrains JVM without closing IDE windows.

JetBrains opens multiple project windows in one application process.  A
backlog left by a recently closed project can therefore stall older windows.
This module correlates process metrics, ``idea.log`` events and the EDT thread
state.  Its only mutating recovery action is an explicitly requested
``jcmd <pid> GC.run`` against the matching JVM; it never sends a signal, closes
a window, removes a lock, or edits project configuration.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Sequence

import psutil

from .process_chains import ProcessRecord, collect_processes


JETBRAINS_PRODUCTS = {
    "clion": "CLion",
    "datagrip": "DataGrip",
    "goland": "GoLand",
    "idea": "IntelliJIdea",
    "phpstorm": "PhpStorm",
    "pycharm": "PyCharm",
    "rider": "Rider",
    "rubymine": "RubyMine",
    "webstorm": "WebStorm",
}
JETBRAINS_HELPERS = {
    "cef_server",
    "fsnotifier",
    "jetbrains-toolbox",
    "jetbrainsd",
    "stdiomcpserver",
}
LOG_TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")
EDT_GRAB_MS = re.compile(r"(?P<millis>\d+) ms total to grab EDT")
MISSING_WORKDIR = re.compile(
    r"working directory ['\"](?P<path>[^'\"]+)['\"] does not exist",
    re.IGNORECASE,
)
HEAP_KIB = re.compile(
    r"committed (?P<committed>\d+)K, used (?P<used>\d+)K",
    re.IGNORECASE,
)


class JetBrainsRecoverySafetyError(RuntimeError):
    """Raised when a recovery request cannot be proven safe and applicable."""


@dataclass(frozen=True, slots=True)
class JetBrainsMetrics:
    pid: int
    create_time: float
    cpu_percent: float
    memory_percent: float
    rss_bytes: int
    thread_count: int


@dataclass(frozen=True, slots=True)
class JvmHeapInfo:
    used_bytes: int
    committed_bytes: int

    @property
    def used_ratio(self) -> float:
        if self.committed_bytes <= 0:
            return 0.0
        return self.used_bytes / self.committed_bytes


@dataclass(frozen=True, slots=True)
class EdtThreadState:
    java_state: str
    detail: str
    top_frames: tuple[str, ...]

    @property
    def contended(self) -> bool:
        stack = "\n".join(self.top_frames)
        return self.java_state == "BLOCKED" or any(
            marker in stack
            for marker in ("WriteIntentLock", "ReadMostlyRWLock", "runIntendedWriteAction")
        )


@dataclass(frozen=True, slots=True)
class JetBrainsLogSignals:
    write_action_waits: int = 0
    edt_grab_warnings: int = 0
    max_edt_grab_ms: int = 0
    project_disposals: int = 0
    working_directory_errors: int = 0
    git_stash_refresh_failures: int = 0
    ai_quota_errors: int = 0
    missing_working_directories: tuple[str, ...] = ()

    @property
    def has_stall_evidence(self) -> bool:
        return (
            self.write_action_waits >= 10
            or self.max_edt_grab_ms >= 2_000
            or self.working_directory_errors >= 3
        )


@dataclass(frozen=True, slots=True)
class JetBrainsDiagnosis:
    process: ProcessRecord
    metrics: JetBrainsMetrics
    log_path: Path | None
    log_signals: JetBrainsLogSignals
    jcmd_path: Path | None
    heap: JvmHeapInfo | None
    edt: EdtThreadState | None
    severity: str
    reason_codes: tuple[str, ...]
    gc_recommended: bool
    diagnostic_errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class JetBrainsRecoveryResult:
    pid: int
    command: tuple[str, ...]
    dry_run: bool
    executed: bool
    returncode: int | None
    before_metrics: JetBrainsMetrics
    after_metrics: JetBrainsMetrics | None
    before_heap: JvmHeapInfo | None
    after_heap: JvmHeapInfo | None
    verification_signals: JetBrainsLogSignals
    verified_improvement: bool
    errors: tuple[str, ...] = ()


def is_main_jetbrains_process(process: ProcessRecord) -> bool:
    """Return true only for a main IDE process, never a helper/server."""

    tokens = (process.name, *process.cmdline)
    normalized = " ".join(tokens).casefold()
    if any(helper in normalized for helper in JETBRAINS_HELPERS):
        return False
    return any(product in normalized for product in JETBRAINS_PRODUCTS)


def analyze_idea_log(
    text: str,
    *,
    since_timestamp: float | None = None,
) -> JetBrainsLogSignals:
    """Extract bounded, explainable stall signals from JetBrains log text."""

    write_waits = 0
    edt_warnings = 0
    max_edt_ms = 0
    disposals = 0
    workdir_errors = 0
    stash_failures = 0
    quota_errors = 0
    missing_paths: set[str] = set()
    include_continuation = since_timestamp is None

    for line in text.splitlines():
        timestamp_match = LOG_TIMESTAMP.match(line)
        if timestamp_match:
            try:
                line_time = datetime.strptime(
                    timestamp_match.group(1), "%Y-%m-%d %H:%M:%S,%f"
                ).timestamp()
                include_continuation = (
                    since_timestamp is None or line_time >= since_timestamp
                )
            except ValueError:
                include_continuation = since_timestamp is None
        if not include_continuation:
            continue

        lowered = line.casefold()
        if "write-action is pending" in lowered:
            write_waits += 1
        edt_match = EDT_GRAB_MS.search(line)
        if edt_match:
            edt_warnings += 1
            max_edt_ms = max(max_edt_ms, int(edt_match.group("millis")))
        if "project is being disposed" in lowered:
            disposals += 1
        missing_match = MISSING_WORKDIR.search(line)
        if missing_match:
            workdir_errors += 1
            missing_paths.add(missing_match.group("path"))
        if "gitstashtacker" in lowered or "gitstashtracker" in lowered:
            stash_failures += 1
        if "quotamanager2impl" in lowered and (
            "resultdoesnotmatchconditionexception" in lowered
            or "quota refill state is: error" in lowered
        ):
            quota_errors += 1

    return JetBrainsLogSignals(
        write_action_waits=write_waits,
        edt_grab_warnings=edt_warnings,
        max_edt_grab_ms=max_edt_ms,
        project_disposals=disposals,
        working_directory_errors=workdir_errors,
        git_stash_refresh_failures=stash_failures,
        ai_quota_errors=quota_errors,
        missing_working_directories=tuple(sorted(missing_paths)),
    )


def parse_heap_info(text: str) -> JvmHeapInfo | None:
    match = HEAP_KIB.search(text)
    if not match:
        return None
    return JvmHeapInfo(
        used_bytes=int(match.group("used")) * 1024,
        committed_bytes=int(match.group("committed")) * 1024,
    )


def parse_edt_thread(text: str) -> EdtThreadState | None:
    """Extract the AWT event-dispatch thread from a ``Thread.print`` result."""

    start = re.search(r'^"AWT-EventQueue-\d+"[^\n]*$', text, re.MULTILINE)
    if not start:
        return None
    remainder = text[start.start() :]
    next_thread = re.search(r'\n\n"[^\n]+"', remainder)
    block = remainder[: next_thread.start()] if next_thread else remainder
    state_match = re.search(
        r"java\.lang\.Thread\.State:\s+(?P<state>[A-Z_]+)(?:\s+\((?P<detail>[^)]+)\))?",
        block,
    )
    if not state_match:
        return None
    frames = tuple(
        line.strip()
        for line in block.splitlines()
        if line.lstrip().startswith("at ")
    )
    return EdtThreadState(
        java_state=state_match.group("state"),
        detail=state_match.group("detail") or "",
        top_frames=frames[:8],
    )


def read_log_tail(path: Path, *, max_bytes: int = 2_000_000) -> str:
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, 2)
            handle.seek(max(0, size - max_bytes))
            return handle.read(max_bytes).decode("utf-8", errors="replace")
    except OSError:
        return ""


def read_log_since(path: Path, offset: int, *, max_bytes: int = 2_000_000) -> str:
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, 2)
            start = offset if 0 <= offset <= size else max(0, size - max_bytes)
            handle.seek(start)
            return handle.read(max_bytes).decode("utf-8", errors="replace")
    except OSError:
        return ""


def collect_jetbrains_metrics(
    pid: int,
    *,
    sample_seconds: float = 0.25,
) -> JetBrainsMetrics:
    process = psutil.Process(pid)
    create_time = process.create_time()
    process.cpu_percent(None)
    if sample_seconds > 0:
        time.sleep(sample_seconds)
    memory = process.memory_info()
    return JetBrainsMetrics(
        pid=pid,
        create_time=create_time,
        cpu_percent=max(0.0, process.cpu_percent(None)),
        memory_percent=max(0.0, process.memory_percent()),
        rss_bytes=max(0, int(memory.rss)),
        thread_count=max(0, process.num_threads()),
    )


class JetBrainsRecovery:
    """Correlate JetBrains evidence and optionally run a bounded JVM GC."""

    def __init__(
        self,
        *,
        process_provider: Callable[[], Sequence[ProcessRecord]] | None = None,
        metrics_provider: Callable[[int], JetBrainsMetrics] | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
        jcmd_finder: Callable[[ProcessRecord], Path | None] | None = None,
        log_finder: Callable[[ProcessRecord], Path | None] | None = None,
    ) -> None:
        self._process_provider = process_provider or collect_processes
        self._metrics_provider = metrics_provider or collect_jetbrains_metrics
        self._runner = runner or subprocess.run
        self._clock = clock
        self._sleeper = sleeper
        self._jcmd_finder = jcmd_finder or self._discover_jcmd
        self._log_finder = log_finder or self._discover_log

    def find_main_processes(
        self,
        records: Sequence[ProcessRecord] | None = None,
    ) -> list[ProcessRecord]:
        snapshot = list(records) if records is not None else list(self._process_provider())
        result = [item for item in snapshot if is_main_jetbrains_process(item)]
        result.sort(key=lambda item: (item.create_time, item.pid), reverse=True)
        return result

    @staticmethod
    def _product_prefix(process: ProcessRecord) -> str | None:
        normalized = " ".join((process.name, *process.cmdline)).casefold()
        for marker, prefix in JETBRAINS_PRODUCTS.items():
            if marker in normalized:
                return prefix
        return None

    def _discover_log(self, process: ProcessRecord) -> Path | None:
        prefix = self._product_prefix(process)
        if prefix is None:
            return None
        root = Path.home() / ".cache" / "JetBrains"
        try:
            candidates = list(root.glob(f"{prefix}*/log/idea.log"))
            return max(candidates, key=lambda path: path.stat().st_mtime)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _discover_jcmd(process: ProcessRecord) -> Path | None:
        candidates: list[Path] = []
        if process.cmdline:
            launcher = Path(process.cmdline[0])
            if launcher.parent.name == "bin":
                candidates.append(launcher.parent.parent / "jbr" / "bin" / "jcmd")
        try:
            executable = Path(psutil.Process(process.pid).exe())
            candidates.append(executable.with_name("jcmd"))
        except (psutil.Error, OSError):
            pass
        for candidate in candidates:
            try:
                if candidate.is_file() and candidate.stat().st_mode & 0o111:
                    return candidate
            except OSError:
                continue
        return None

    def _run_jcmd(
        self,
        jcmd: Path,
        pid: int,
        command: str,
        *,
        timeout: float = 20.0,
    ) -> subprocess.CompletedProcess[str]:
        return self._runner(
            [str(jcmd), str(pid), command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def diagnose(
        self,
        pid: int,
        *,
        log_path: Path | None = None,
        lookback_seconds: float = 10 * 60,
        capture_thread_dump: bool = True,
    ) -> JetBrainsDiagnosis:
        processes = {item.pid: item for item in self._process_provider()}
        process = processes.get(pid)
        if process is None:
            raise JetBrainsRecoverySafetyError("selected IDE process no longer exists")
        if not is_main_jetbrains_process(process):
            raise JetBrainsRecoverySafetyError(
                "selected PID is not a main JetBrains IDE process"
            )

        metrics = self._metrics_provider(pid)
        if abs(metrics.create_time - process.create_time) >= 0.001:
            raise JetBrainsRecoverySafetyError(
                "selected IDE PID was reused by a different process"
            )
        selected_log = log_path or self._log_finder(process)
        log_text = read_log_tail(selected_log) if selected_log else ""
        signals = analyze_idea_log(
            log_text,
            since_timestamp=self._clock() - max(0.0, lookback_seconds),
        )
        jcmd = self._jcmd_finder(process)
        heap: JvmHeapInfo | None = None
        edt: EdtThreadState | None = None
        errors: list[str] = []
        if jcmd is None:
            errors.append("matching jcmd executable was not found")
        else:
            try:
                heap_result = self._run_jcmd(jcmd, pid, "GC.heap_info")
                if heap_result.returncode == 0:
                    heap = parse_heap_info(heap_result.stdout)
                else:
                    errors.append(f"GC.heap_info failed: {heap_result.stderr.strip()}")
                if capture_thread_dump:
                    thread_result = self._run_jcmd(jcmd, pid, "Thread.print")
                    if thread_result.returncode == 0:
                        edt = parse_edt_thread(thread_result.stdout)
                    else:
                        errors.append(
                            f"Thread.print failed: {thread_result.stderr.strip()}"
                        )
            except (OSError, subprocess.SubprocessError) as exc:
                errors.append(f"jcmd diagnostic failed: {exc}")

        reasons: list[str] = []
        if signals.write_action_waits >= 10:
            reasons.append("repeated-write-action-waits")
        if signals.max_edt_grab_ms >= 2_000:
            reasons.append("slow-edt-access")
        if signals.project_disposals and signals.write_action_waits:
            reasons.append("post-project-disposal-backlog")
        if signals.working_directory_errors >= 3:
            reasons.append("repeated-missing-working-directory")
        if signals.git_stash_refresh_failures >= 3:
            reasons.append("git-stash-refresh-loop")
        if signals.ai_quota_errors >= 3:
            reasons.append("ai-quota-refresh-loop")
        if metrics.cpu_percent >= 100.0:
            reasons.append("high-ide-cpu")
        if metrics.thread_count >= 600:
            reasons.append("high-ide-thread-count")
        if edt and edt.contended:
            reasons.append("edt-lock-contention")

        heap_pressure = bool(heap and heap.used_ratio >= 0.75)
        if heap_pressure:
            reasons.append("high-jvm-heap-usage")
        elif metrics.memory_percent >= 25.0:
            reasons.append("high-process-memory")

        if edt and edt.contended:
            severity = "critical"
        elif (
            signals.write_action_waits >= 10
            and metrics.cpu_percent >= 100.0
            and signals.max_edt_grab_ms >= 2_000
        ):
            severity = "high"
        elif (
            signals.has_stall_evidence
            or signals.ai_quota_errors >= 3
            or metrics.cpu_percent >= 100.0
        ):
            severity = "warning"
        else:
            severity = "normal"
        gc_recommended = heap_pressure and (
            signals.has_stall_evidence or bool(edt and edt.contended)
        )

        return JetBrainsDiagnosis(
            process=process,
            metrics=metrics,
            log_path=selected_log,
            log_signals=signals,
            jcmd_path=jcmd,
            heap=heap,
            edt=edt,
            severity=severity,
            reason_codes=tuple(reasons),
            gc_recommended=gc_recommended,
            diagnostic_errors=tuple(errors),
        )

    def recover(
        self,
        diagnosis: JetBrainsDiagnosis,
        *,
        apply: bool = False,
        verification_seconds: float = 3.0,
    ) -> JetBrainsRecoveryResult:
        """Optionally run ``GC.run`` and verify evidence without closing the IDE."""

        if diagnosis.jcmd_path is None:
            raise JetBrainsRecoverySafetyError("matching jcmd executable is unavailable")
        command = (
            str(diagnosis.jcmd_path),
            str(diagnosis.process.pid),
            "GC.run",
        )
        empty_signals = JetBrainsLogSignals()
        if not apply:
            return JetBrainsRecoveryResult(
                pid=diagnosis.process.pid,
                command=command,
                dry_run=True,
                executed=False,
                returncode=None,
                before_metrics=diagnosis.metrics,
                after_metrics=None,
                before_heap=diagnosis.heap,
                after_heap=None,
                verification_signals=empty_signals,
                verified_improvement=False,
            )
        if not diagnosis.gc_recommended:
            raise JetBrainsRecoverySafetyError(
                "GC.run is not justified by current heap and stall evidence"
            )

        current_jcmd = self._jcmd_finder(diagnosis.process)
        if current_jcmd is None or current_jcmd.absolute() != diagnosis.jcmd_path.absolute():
            raise JetBrainsRecoverySafetyError(
                "matching jcmd executable changed before recovery"
            )

        current = self._metrics_provider(diagnosis.process.pid)
        if abs(current.create_time - diagnosis.process.create_time) >= 0.001:
            raise JetBrainsRecoverySafetyError(
                "selected IDE PID was reused before recovery"
            )
        log_offset = 0
        if diagnosis.log_path:
            try:
                log_offset = diagnosis.log_path.stat().st_size
            except OSError:
                pass

        errors: list[str] = []
        try:
            result = self._run_jcmd(
                diagnosis.jcmd_path,
                diagnosis.process.pid,
                "GC.run",
                timeout=60.0,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"GC.run failed: {exc}")
            returncode: int | None = None
        else:
            returncode = result.returncode
            if result.returncode != 0:
                errors.append(f"GC.run failed: {result.stderr.strip()}")

        self._sleeper(max(0.0, verification_seconds))
        after_metrics: JetBrainsMetrics | None = None
        after_heap: JvmHeapInfo | None = None
        try:
            after_metrics = self._metrics_provider(diagnosis.process.pid)
            if abs(after_metrics.create_time - diagnosis.process.create_time) >= 0.001:
                errors.append("IDE PID identity changed during verification")
                after_metrics = None
            else:
                heap_result = self._run_jcmd(
                    diagnosis.jcmd_path,
                    diagnosis.process.pid,
                    "GC.heap_info",
                )
                if heap_result.returncode == 0:
                    after_heap = parse_heap_info(heap_result.stdout)
        except (OSError, psutil.Error, subprocess.SubprocessError) as exc:
            errors.append(f"post-recovery verification failed: {exc}")

        new_log = (
            read_log_since(diagnosis.log_path, log_offset)
            if diagnosis.log_path
            else ""
        )
        verification_signals = analyze_idea_log(new_log)
        cpu_improved = bool(
            after_metrics
            and after_metrics.cpu_percent
            <= max(100.0, diagnosis.metrics.cpu_percent * 0.75)
        )
        heap_improved = bool(
            diagnosis.heap
            and after_heap
            and after_heap.used_ratio <= diagnosis.heap.used_ratio - 0.05
        )
        stall_stopped = (
            verification_signals.write_action_waits == 0
            and verification_signals.max_edt_grab_ms < 2_000
        )
        verified = (
            returncode == 0
            and not errors
            and stall_stopped
            and (cpu_improved or heap_improved)
        )
        return JetBrainsRecoveryResult(
            pid=diagnosis.process.pid,
            command=command,
            dry_run=False,
            executed=True,
            returncode=returncode,
            before_metrics=diagnosis.metrics,
            after_metrics=after_metrics,
            before_heap=diagnosis.heap,
            after_heap=after_heap,
            verification_signals=verification_signals,
            verified_improvement=verified,
            errors=tuple(errors),
        )
