"""Report executed actions accurately and keep every autonomous dry-run inert."""

import json
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from fixos.agent.autonomous_session import AgentReport, AutonomousSession, FixAction
from fixos.cli.main import cli
from fixos.config import FixOsConfig


def config():
    return FixOsConfig(
        provider="gemini",
        api_key="",
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        agent_mode="autonomous",
        session_timeout=30,
        show_anonymized_data=False,
        enable_web_search=False,
    )


@pytest.fixture
def session_factory(monkeypatch):
    monkeypatch.setattr(AutonomousSession, "_setup_timeout", lambda self: None)
    monkeypatch.setattr(AutonomousSession, "_clear_timeout", lambda self: None)
    monkeypatch.setattr("fixos.agent.autonomous_session.time.sleep", lambda _: None)

    def make(*, use_llm=False, dry_run=False, diagnostics=None):
        session = AutonomousSession(
            diagnostics=diagnostics
            if diagnostics is not None
            else {
                "_run_plugins": False,
                "system": {
                    "findings": [
                        {
                            "title": "Repair candidate",
                            "severity": "warning",
                            "command": "printf test",
                        }
                    ]
                },
            },
            config=config(),
            show_data=False,
            max_fixes=3,
            auto_confirm=True,
            use_llm=use_llm,
            dry_run=dry_run,
        )
        session._execute_command = Mock(return_value=(True, "completed"))
        if use_llm:
            session.llm = SimpleNamespace(
                chat=Mock(
                    side_effect=[
                        json.dumps(
                            {
                                "action": "EXEC",
                                "command": "printf test",
                                "reason": "Repair candidate",
                            }
                        ),
                        json.dumps({"action": "DONE"}),
                    ]
                )
            )
        return session

    return make


def test_empty_queue_does_not_claim_unactionable_problems_were_fixed(
    session_factory, capsys
):
    session = session_factory(
        diagnostics={
            "_run_plugins": False,
            "quick": {
                "findings": [{"title": "Disk critically full", "severity": "critical"}]
            },
        }
    )
    report = session.run()
    output = capsys.readouterr().out
    assert report.fixes_applied == []
    session._execute_command.assert_not_called()
    assert "wszystkie problemy naprawione" not in output
    assert re.search(r"Udane operacje:\s*0", output)


@pytest.mark.parametrize("use_llm", [False, True])
def test_dry_run_never_executes_commands_in_either_mode(
    session_factory, capsys, use_llm
):
    session = session_factory(use_llm=use_llm, dry_run=True)
    report = session.run()
    session._execute_command.assert_not_called()
    assert len(report.fixes_applied) == 1
    assert report.fixes_applied[0].result == "[DRY-RUN]"
    output = capsys.readouterr().out
    assert "wszystkie problemy naprawione" not in output
    assert re.search(r"Udane operacje:\s*0", output)
    assert re.search(r"Symulacje:\s*1", output)


@pytest.mark.parametrize("success", [False, True])
@pytest.mark.parametrize("use_llm", [False, True])
def test_real_attempts_are_counted_by_outcome(session_factory, capsys, success, use_llm):
    session = session_factory(use_llm=use_llm)
    session._execute_command.return_value = (success, "command output")
    report = session.run()
    session._execute_command.assert_called_once_with("printf test")
    assert report.fixes_applied[0].success is success
    output = capsys.readouterr().out
    assert "wszystkie problemy naprawione" not in output
    assert re.search(rf"Udane operacje:\s*{int(success)}", output)
    if not success:
        assert re.search(r"Nieudane operacje:\s*1", output)


def test_mixed_report_separates_execution_simulation_and_unknown_outcomes():
    actions = [
        FixAction("success", "success", result="ok", success=True),
        FixAction("failed", "failed", result="error", success=False),
        FixAction("planned", "planned", result="[DRY-RUN]", success=True),
        FixAction("unknown", "unknown"),
    ]
    report = AgentReport(fixes_applied=actions)
    output = report.summary()
    assert re.search(r"Udane operacje:\s*1", output)
    assert re.search(r"Nieudane operacje:\s*1", output)
    assert re.search(r"Symulacje:\s*1", output)
    assert "Naprawiono:" not in output
    assert "🧪 `planned`" in output
    assert "❔ `unknown`" in output
    assert report.fixes_applied == actions


@pytest.mark.parametrize("machine_output", [False, True])
def test_auto_labels_attempts_as_actions_and_preserves_legacy_json_field(
    monkeypatch, machine_output
):
    monkeypatch.setattr(FixOsConfig, "load", lambda **kwargs: config())
    monkeypatch.setattr("fixos.diagnostics.quick_snapshot.collect_quick_snapshot", dict)
    monkeypatch.setattr(
        "fixos.cli.quick_cmd.render_quick_snapshot", lambda *a, **k: None
    )
    report = AgentReport(
        fixes_applied=[FixAction("failed", "failed", result="error", success=False)]
    )
    monkeypatch.setattr(
        "fixos.cli.fix_cmd.run_autonomous_session", lambda **kwargs: report
    )
    args = ["auto", "--no-disc", "--no-banner"]
    if machine_output:
        args.append("--json")
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    if machine_output:
        assert json.loads(result.stdout)["fixes_applied"] == 1
    else:
        assert re.search(r"Akcje agenta\s*:\s*1", result.stdout)
        assert "Naprawy agenta" not in result.stdout
