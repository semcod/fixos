from pathlib import Path

from click.testing import CliRunner

from fixos.cli import jetbrains_cmd
from fixos.diagnostics.jetbrains_ai import JetBrainsAiControl
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


class FakeAiControl:
    disable_calls = []
    stop_calls = []

    def status(self, *, config_dir=None):
        return {
            "service": "jetbrains-ai-control",
            "read_only": True,
            "plugin_ids": ["com.intellij.ml.llm", "com.qoder"],
            "helpers": [
                {
                    "pid": 200,
                    "ppid": 100,
                    "create_time": 2000.0,
                    "command": ["/opt/Qoder", "start"],
                    "rss_bytes": 1024,
                }
            ],
            "configs": [
                {
                    "directory": "/tmp/JetBrains/PyCharm2026.2",
                    "disabled_plugins_file": "/tmp/JetBrains/PyCharm2026.2/disabled_plugins.txt",
                    "disabled": ["com.qoder"],
                }
            ],
        }

    def disable_plugins(self, config_dir, *, apply):
        self.disable_calls.append((config_dir, apply))
        return {
            "added": ["com.intellij.ml.llm"],
            "changed": apply,
            "dry_run": not apply,
        }

    def stop_qoder_helpers(self, identities, *, apply):
        self.stop_calls.append((identities, apply))
        return {
            "selected": [200],
            "stopped": [200] if apply else [],
            "failed": [],
            "success": True,
            "dry_run": not apply,
        }


def test_ai_status_is_read_only_json(monkeypatch):
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsAiControl", FakeAiControl)

    result = CliRunner().invoke(jetbrains_cmd.jetbrains, ["ai", "--json"])

    assert result.exit_code == 0, result.output
    assert '"read_only": true' in result.output
    assert '"pid": 200' in result.output
    assert '"com.qoder"' in result.output


def test_ai_actions_are_dry_run_without_apply(monkeypatch):
    FakeAiControl.disable_calls = []
    FakeAiControl.stop_calls = []
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsAiControl", FakeAiControl)

    result = CliRunner().invoke(
        jetbrains_cmd.jetbrains,
        ["ai", "--disable-plugins", "--stop-qoder", "--json"],
    )

    assert result.exit_code == 0, result.output
    assert FakeAiControl.disable_calls == [(Path("/tmp/JetBrains/PyCharm2026.2"), False)]
    assert FakeAiControl.stop_calls == [([(200, 2000.0)], False)]
    assert '"dry_run": true' in result.output


def test_ai_apply_confirmation_can_decline(monkeypatch):
    FakeAiControl.disable_calls = []
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsAiControl", FakeAiControl)

    result = CliRunner().invoke(
        jetbrains_cmd.jetbrains,
        ["ai", "--disable-plugins", "--apply"],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Pominięto zmiany" in result.output
    assert FakeAiControl.disable_calls == []


def test_ai_apply_yes_routes_exact_helper_identity(monkeypatch):
    FakeAiControl.disable_calls = []
    FakeAiControl.stop_calls = []
    monkeypatch.setattr(jetbrains_cmd, "JetBrainsAiControl", FakeAiControl)

    result = CliRunner().invoke(
        jetbrains_cmd.jetbrains,
        ["ai", "--disable-plugins", "--stop-qoder", "--apply", "--yes"],
    )

    assert result.exit_code == 0, result.output
    assert FakeAiControl.disable_calls == [(Path("/tmp/JetBrains/PyCharm2026.2"), True)]
    assert FakeAiControl.stop_calls == [([(200, 2000.0)], True)]
    assert "Główna JVM i okna IDE nie są zatrzymywane" in result.output


def test_ai_service_preserves_plugins_and_stops_only_exact_qoder(tmp_path):
    config_root = tmp_path / "JetBrains"
    config_dir = config_root / "PyCharm2026.2"
    config_dir.mkdir(parents=True)
    disabled = config_dir / "disabled_plugins.txt"
    disabled.write_text("unrelated.plugin\ncom.qoder\n", encoding="utf-8")
    ide = _process()
    helper = ProcessRecord(
        pid=200,
        ppid=ide.pid,
        name="Qoder",
        cmdline=("/opt/Qoder", "start"),
        create_time=2000.0,
        username="tester",
    )
    unrelated = ProcessRecord(
        pid=300,
        ppid=1,
        name="Qoder",
        cmdline=("/opt/Qoder", "start"),
        create_time=3000.0,
        username="tester",
    )
    alive = {200}
    terminated = []
    control = JetBrainsAiControl(
        process_provider=lambda: [ide, helper, unrelated],
        config_root=config_root,
        identity_provider=lambda pid: {200: 2000.0, 300: 3000.0}.get(pid),
        rss_provider=lambda pid: 4096,
        terminator=lambda pid: (terminated.append(pid), alive.discard(pid)),
        alive_provider=lambda pid, created: pid in alive,
    )

    status = control.status()
    plugin_result = control.disable_plugins(config_dir, apply=True)
    helper_result = control.stop_qoder_helpers([(200, 2000.0)], apply=True)

    assert [item["pid"] for item in status["helpers"]] == [200]
    assert plugin_result["added"] == ["com.intellij.ml.llm"]
    assert disabled.read_text().splitlines() == [
        "unrelated.plugin",
        "com.qoder",
        "com.intellij.ml.llm",
    ]
    assert terminated == [200]
    assert helper_result["stopped"] == [200]
