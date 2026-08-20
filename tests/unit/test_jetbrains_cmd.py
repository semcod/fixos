from pathlib import Path

from click.testing import CliRunner

from fixos.cli import jetbrains_cmd
from fixos.diagnostics.jetbrains_recovery import (
    EdtThreadState,
    JetBrainsDiagnosis,
    JetBrainsLogSignals,
    JetBrainsMetrics,
    JetBrainsRecoveryResult,
    JvmHeapInfo,
)
from fixos.diagnostics.process_chains import ProcessRecord


def _process(pid: int = 100) -> ProcessRecord:
    return ProcessRecord(
        pid=pid,
        ppid=1,
        name="pycharm",
        cmdline=("/opt/pycharm/bin/pycharm",),
        create_time=1000.0,
        username="tester",
    )


def _diagnosis(pid: int = 100, *, gc_recommended: bool = True) -> JetBrainsDiagnosis:
    return JetBrainsDiagnosis(
        process=_process(pid),
        metrics=JetBrainsMetrics(pid, 1000.0, 150.0, 20.0, 12 * 1024**3, 700),
        log_path=Path("/tmp/idea.log"),
        log_signals=JetBrainsLogSignals(ai_quota_errors=5),
        jcmd_path=Path("/fake/jcmd"),
        heap=JvmHeapInfo(80, 100),
        edt=EdtThreadState("WAITING", "parking", ()),
        severity="warning",
        reason_codes=("high-ide-cpu", "ai-quota-refresh-loop"),
        gc_recommended=gc_recommended,
    )


class FakeRecovery:
    processes = [_process()]
    diagnosis = _diagnosis()
    recover_calls = []

    def find_main_processes(self):
        return list(self.processes)

    def diagnose(self, pid, **kwargs):
        assert pid == self.diagnosis.process.pid
        return self.diagnosis

    def recover(self, diagnosis, *, apply=False):
        self.recover_calls.append((diagnosis.process.pid, apply))
        return JetBrainsRecoveryResult(
            pid=diagnosis.process.pid,
            command=("/fake/jcmd", str(diagnosis.process.pid), "GC.run"),
            dry_run=False,
            executed=True,
            returncode=0,
            before_metrics=diagnosis.metrics,
            after_metrics=diagnosis.metrics,
            before_heap=diagnosis.heap,
            after_heap=diagnosis.heap,
            verification_signals=JetBrainsLogSignals(),
            verified_improvement=True,
        )


def test_doctor_reports_empty_state(monkeypatch):
    FakeRecovery.processes = []
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsRecovery", FakeRecovery)

    result = CliRunner().invoke(jetbrains_cmd.jetbrains, ["doctor"])

    assert result.exit_code == 0
    assert "Nie znaleziono" in result.output


def test_doctor_json_contains_metrics_and_quota_signal(monkeypatch):
    FakeRecovery.processes = [_process()]
    FakeRecovery.diagnosis = _diagnosis()
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsRecovery", FakeRecovery)

    result = CliRunner().invoke(
        jetbrains_cmd.jetbrains,
        ["doctor", "--pid", "100", "--json", "--no-thread-dump"],
    )

    assert result.exit_code == 0, result.output
    assert '"rss_bytes": 12884901888' in result.output
    assert '"ai_quota_errors": 5' in result.output
    assert '"read_only": true' in result.output


def test_apply_gc_requires_exact_pid():
    result = CliRunner().invoke(
        jetbrains_cmd.jetbrains,
        ["doctor", "--apply-gc"],
    )

    assert result.exit_code == 2
    assert "wymaga dokładnego --pid" in result.output


def test_apply_gc_confirmation_can_decline(monkeypatch):
    FakeRecovery.processes = [_process()]
    FakeRecovery.diagnosis = _diagnosis()
    FakeRecovery.recover_calls = []
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsRecovery", FakeRecovery)

    result = CliRunner().invoke(
        jetbrains_cmd.jetbrains,
        ["doctor", "--pid", "100", "--apply-gc"],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Pominięto GC.run" in result.output
    assert FakeRecovery.recover_calls == []


def test_apply_gc_yes_returns_verified_result(monkeypatch):
    FakeRecovery.processes = [_process()]
    FakeRecovery.diagnosis = _diagnosis()
    FakeRecovery.recover_calls = []
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsRecovery", FakeRecovery)

    result = CliRunner().invoke(
        jetbrains_cmd.jetbrains,
        ["doctor", "--pid", "100", "--apply-gc", "--yes", "--json"],
    )

    assert result.exit_code == 0, result.output
    assert '"executed": true' in result.output
    assert '"verified_improvement": true' in result.output
    assert FakeRecovery.recover_calls == [(100, True)]
