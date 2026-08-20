"""Tests for JetBrains diagnosis and window-preserving JVM recovery."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from fixos.diagnostics.jetbrains_recovery import (
    EdtThreadState,
    JetBrainsDiagnosis,
    JetBrainsLogSignals,
    JetBrainsMetrics,
    JetBrainsRecovery,
    JetBrainsRecoverySafetyError,
    JvmHeapInfo,
    analyze_idea_log,
    is_main_jetbrains_process,
    parse_edt_thread,
    parse_heap_info,
)
from fixos.diagnostics.process_chains import ProcessRecord


NOW = 1_787_208_000.0


def _process(
    pid: int = 100,
    command: tuple[str, ...] = ("/opt/pycharm/bin/pycharm",),
    *,
    create_time: float = NOW - 3600,
) -> ProcessRecord:
    return ProcessRecord(
        pid=pid,
        ppid=10,
        name=Path(command[0]).name,
        cmdline=command,
        create_time=create_time,
        status="running",
        username="tester",
    )


def _metrics(
    *,
    cpu: float = 200.0,
    memory: float = 20.0,
    threads: int = 800,
    create_time: float = NOW - 3600,
) -> JetBrainsMetrics:
    return JetBrainsMetrics(
        pid=100,
        create_time=create_time,
        cpu_percent=cpu,
        memory_percent=memory,
        rss_bytes=12 * 1024**3,
        thread_count=threads,
    )


def _completed(command, stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def test_main_ide_detection_excludes_mcp_and_native_helpers():
    assert is_main_jetbrains_process(_process()) is True
    assert (
        is_main_jetbrains_process(
            _process(command=("/opt/pycharm/bin/pycharm", "stdioMcpServer"))
        )
        is False
    )
    assert (
        is_main_jetbrains_process(
            _process(command=("/opt/pycharm/bin/fsnotifier",))
        )
        is False
    )
    assert (
        is_main_jetbrains_process(
            _process(command=("/bin/bash", "--rcfile", "/opt/pycharm/bash.rc"))
        )
        is False
    )
    assert (
        is_main_jetbrains_process(
            _process(command=("/bin/bash", "-lc", "fixos jetbrains doctor pycharm"))
        )
        is False
    )


def test_log_analysis_correlates_write_waits_edt_disposal_and_stale_directory():
    lines = [
        "2026-08-20 08:27:47,281 INFO - Project x is removed. Project is being disposed.",
        *[
            f"2026-08-20 08:27:{48 + index:02d},000 INFO - write-action is pending"
            for index in range(10)
        ],
        "2026-08-20 08:28:00,000 WARN - 7687 ms total to grab EDT 12 times",
        *[
            "2026-08-20 08:28:01,000 WARN - Cannot start a process, the working "
            "directory '/work/deleted' does not exist"
            for _ in range(3)
        ],
        *["\tat git4idea.stash.GitStashTracker.scheduleRefresh(x.kt:70)" for _ in range(3)],
    ]

    signals = analyze_idea_log("\n".join(lines))

    assert signals.write_action_waits == 10
    assert signals.max_edt_grab_ms == 7687
    assert signals.project_disposals == 1
    assert signals.working_directory_errors == 3
    assert signals.git_stash_refresh_failures == 3
    assert signals.missing_working_directories == ("/work/deleted",)
    assert signals.has_stall_evidence is True


def test_log_analysis_ignores_events_before_lookback():
    signals = analyze_idea_log(
        "2026-08-20 08:00:00,000 INFO - write-action is pending\n"
        "2026-08-20 08:30:00,000 INFO - write-action is pending",
        since_timestamp=datetime_timestamp("2026-08-20 08:15:00,000"),
    )

    assert signals.write_action_waits == 1


def test_log_analysis_reports_ai_quota_loop_without_stall_evidence():
    signals = analyze_idea_log(
        "\n".join(
            "2026-08-20 08:30:00,000 INFO - #c.i.m.l.c.q.QuotaManager2Impl - "
            "New quota refill state is: Error(exception="
            "ResultDoesNotMatchConditionException)"
            for _ in range(4)
        )
    )

    assert signals.ai_quota_errors == 4
    assert signals.has_stall_evidence is False


def datetime_timestamp(value: str) -> float:
    from datetime import datetime

    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S,%f").timestamp()


def test_heap_info_parser_distinguishes_reporting_from_gc_action():
    heap = parse_heap_info(
        "garbage-first heap total reserved 8192000K, committed 8192000K, "
        "used 6144000K"
    )

    assert heap == JvmHeapInfo(
        used_bytes=6144000 * 1024,
        committed_bytes=8192000 * 1024,
    )
    assert heap.used_ratio == 0.75


def test_edt_parser_detects_write_intent_lock_contention():
    thread_dump = '''"AWT-EventQueue-0" #51 prio=6
   java.lang.Thread.State: WAITING (parking)
        at com.intellij.openapi.application.impl.WriteIntentLock.acquire(WriteIntentLock.kt:1)
        at com.intellij.openapi.application.impl.ApplicationImpl.runIntendedWriteAction(ApplicationImpl.kt:2)

"worker" #52
   java.lang.Thread.State: RUNNABLE
'''

    edt = parse_edt_thread(thread_dump)

    assert edt is not None
    assert edt.java_state == "WAITING"
    assert edt.contended is True


def test_diagnosis_recommends_gc_only_with_heap_and_stall_evidence(tmp_path):
    process = _process()
    log = tmp_path / "idea.log"
    log.write_text(
        "\n".join(
            f"2026-08-20 08:00:{index:02d},000 INFO - write-action is pending"
            for index in range(10)
        ),
        encoding="utf-8",
    )
    commands: list[list[str]] = []

    def runner(command, **kwargs):
        commands.append(command)
        if command[-1] == "GC.heap_info":
            return _completed(
                command,
                "committed 100000K, used 80000K",
            )
        return _completed(
            command,
            '"AWT-EventQueue-0"\n   java.lang.Thread.State: WAITING (parking)\n',
        )

    recovery = JetBrainsRecovery(
        process_provider=lambda: [process],
        metrics_provider=lambda pid: _metrics(),
        runner=runner,
        clock=lambda: datetime_timestamp("2026-08-20 08:01:00,000"),
        jcmd_finder=lambda item: Path("/fake/jcmd"),
        log_finder=lambda item: log,
    )

    diagnosis = recovery.diagnose(100, lookback_seconds=120)

    assert diagnosis.severity == "warning"
    assert diagnosis.gc_recommended is True
    assert "repeated-write-action-waits" in diagnosis.reason_codes
    assert "high-jvm-heap-usage" in diagnosis.reason_codes
    assert [command[-1] for command in commands] == ["GC.heap_info", "Thread.print"]


def test_high_cpu_without_heap_pressure_does_not_justify_gc(tmp_path):
    process = _process()
    log = tmp_path / "idea.log"
    log.write_text(
        "\n".join(
            f"2026-08-20 08:00:{index:02d},000 INFO - write-action is pending"
            for index in range(10)
        ),
        encoding="utf-8",
    )

    def runner(command, **kwargs):
        return _completed(command, "committed 100000K, used 50000K")

    diagnosis = JetBrainsRecovery(
        process_provider=lambda: [process],
        metrics_provider=lambda pid: _metrics(cpu=500.0, memory=30.0),
        runner=runner,
        clock=lambda: datetime_timestamp("2026-08-20 08:01:00,000"),
        jcmd_finder=lambda item: Path("/fake/jcmd"),
        log_finder=lambda item: log,
    ).diagnose(100, lookback_seconds=120, capture_thread_dump=False)

    assert diagnosis.gc_recommended is False
    assert diagnosis.severity == "warning"
    assert "high-process-memory" in diagnosis.reason_codes


def test_quota_loop_is_warning_but_does_not_justify_gc(tmp_path):
    process = _process()
    log = tmp_path / "idea.log"
    log.write_text(
        "\n".join(
            "2026-08-20 08:00:30,000 INFO - #c.i.m.l.c.q.QuotaManager2Impl - "
            "New quota refill state is: Error(exception="
            "ResultDoesNotMatchConditionException)"
            for _ in range(3)
        ),
        encoding="utf-8",
    )

    def runner(command, **kwargs):
        return _completed(command, "committed 100000K, used 50000K")

    diagnosis = JetBrainsRecovery(
        process_provider=lambda: [process],
        metrics_provider=lambda pid: _metrics(cpu=10.0, memory=10.0, threads=100),
        runner=runner,
        clock=lambda: datetime_timestamp("2026-08-20 08:01:00,000"),
        jcmd_finder=lambda item: Path("/fake/jcmd"),
        log_finder=lambda item: log,
    ).diagnose(100, lookback_seconds=120, capture_thread_dump=False)

    assert diagnosis.severity == "warning"
    assert "ai-quota-refresh-loop" in diagnosis.reason_codes
    assert diagnosis.gc_recommended is False


def _diagnosis(*, recommended: bool = True, log_path: Path | None = None):
    return JetBrainsDiagnosis(
        process=_process(),
        metrics=_metrics(cpu=300.0),
        log_path=log_path,
        log_signals=JetBrainsLogSignals(write_action_waits=20),
        jcmd_path=Path("/fake/jcmd"),
        heap=JvmHeapInfo(used_bytes=80, committed_bytes=100),
        edt=EdtThreadState("WAITING", "parking", ()),
        severity="high",
        reason_codes=("repeated-write-action-waits",),
        gc_recommended=recommended,
    )


def test_recovery_is_dry_run_by_default_and_never_executes_command():
    calls = []
    recovery = JetBrainsRecovery(runner=lambda *args, **kwargs: calls.append(args))

    result = recovery.recover(_diagnosis())

    assert result.command == ("/fake/jcmd", "100", "GC.run")
    assert result.dry_run is True
    assert result.executed is False
    assert calls == []


def test_recovery_refuses_pid_reuse_before_gc():
    recovery = JetBrainsRecovery(
        metrics_provider=lambda pid: _metrics(create_time=NOW - 1),
        jcmd_finder=lambda process: Path("/fake/jcmd"),
    )

    with pytest.raises(JetBrainsRecoverySafetyError, match="PID was reused"):
        recovery.recover(_diagnosis(), apply=True)


def test_recovery_refuses_gc_without_memory_recommendation():
    recovery = JetBrainsRecovery()

    with pytest.raises(JetBrainsRecoverySafetyError, match="not justified"):
        recovery.recover(_diagnosis(recommended=False), apply=True)


def test_recovery_refuses_jcmd_that_no_longer_matches_selected_jvm():
    recovery = JetBrainsRecovery(
        jcmd_finder=lambda process: Path("/different/jcmd"),
    )

    with pytest.raises(JetBrainsRecoverySafetyError, match="jcmd executable changed"):
        recovery.recover(_diagnosis(), apply=True)


def test_recovery_runs_only_gc_and_verifies_cpu_heap_and_new_log(tmp_path):
    log = tmp_path / "idea.log"
    log.write_text("before\n", encoding="utf-8")
    metrics = iter([_metrics(cpu=300.0), _metrics(cpu=100.0)])
    commands: list[list[str]] = []

    def runner(command, **kwargs):
        commands.append(command)
        if command[-1] == "GC.run":
            return _completed(command, "Command executed successfully")
        return _completed(command, "committed 100K, used 50K")

    recovery = JetBrainsRecovery(
        metrics_provider=lambda pid: next(metrics),
        runner=runner,
        sleeper=lambda seconds: None,
        jcmd_finder=lambda process: Path("/fake/jcmd"),
    )

    result = recovery.recover(
        _diagnosis(log_path=log),
        apply=True,
        verification_seconds=0,
    )

    assert [command[-1] for command in commands] == ["GC.run", "GC.heap_info"]
    assert result.executed is True
    assert result.returncode == 0
    assert result.verified_improvement is True
    assert result.errors == ()


def test_failed_gc_never_claims_verified_recovery():
    metrics = iter([_metrics(cpu=300.0), _metrics(cpu=100.0)])

    def runner(command, **kwargs):
        if command[-1] == "GC.run":
            return _completed(command, returncode=1, stderr="attach failed")
        return _completed(command, "committed 100K, used 50K")

    result = JetBrainsRecovery(
        metrics_provider=lambda pid: next(metrics),
        runner=runner,
        sleeper=lambda seconds: None,
        jcmd_finder=lambda process: Path("/fake/jcmd"),
    ).recover(_diagnosis(), apply=True, verification_seconds=0)

    assert result.verified_improvement is False
    assert result.errors == ("GC.run failed: attach failed",)
