import json

from click.testing import CliRunner

from fixos.cli import quick_cmd


def _snapshot():
    return {
        "$schema": "fixos-quick-snapshot-v1",
        "generated_at": "2026-07-23T10:00:00+02:00",
        "duration_ms": 120,
        "mode": "heuristic-local",
        "context": {
            "distribution": "Test Linux",
            "profile": "developer",
            "tech_stack": ["python"],
        },
        "resources": {
            "cpu": {"percent": 10},
            "memory": {"percent": 20},
            "disk": {"percent": 30, "free_bytes": 1024**3},
            "top_processes": [
                {
                    "pid": 202,
                    "name": "pycharm",
                    "cpu_percent": 325.5,
                    "memory_percent": 21.2,
                }
            ],
        },
        "safe_reclaim": {
            "estimated_max_bytes": 1024**3,
            "measurement_complete": True,
            "items": [],
        },
        "review": [],
        "growth": {
            "status": "baseline_created",
            "message": "Utworzono punkt odniesienia.",
        },
        "alerts": [],
    }


def test_quick_json_is_machine_readable(monkeypatch):
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda **kwargs: _snapshot(),
    )

    result = CliRunner().invoke(quick_cmd.quick, ["--json", "--no-save"])

    assert result.exit_code == 0
    assert json.loads(result.output)["mode"] == "heuristic-local"


def test_quick_deep_json_contains_both_stages(monkeypatch):
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda **kwargs: _snapshot(),
    )
    monkeypatch.setattr(
        quick_cmd,
        "_run_deep_analysis",
        lambda: {"services_found": 3},
    )

    result = CliRunner().invoke(quick_cmd.quick, ["--json", "--deep"])
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["quick"]["mode"] == "heuristic-local"
    assert payload["deep_cleanup_plan"]["services_found"] == 3


def test_quick_offers_deep_scan_only_after_fast_result(monkeypatch):
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda **kwargs: _snapshot(),
    )
    monkeypatch.setattr(quick_cmd, "_is_interactive_terminal", lambda: True)
    deep_called = []
    monkeypatch.setattr(
        quick_cmd,
        "_run_deep_analysis",
        lambda: deep_called.append(True),
    )

    result = CliRunner().invoke(quick_cmd.quick, [], input="n\n")

    assert result.exit_code == 0
    assert "Wynik w 120 ms" in result.output
    assert "Najbardziej obciążające procesy teraz" in result.output
    assert "pycharm (PID 202): CPU 325.5% · RAM 21.2%" in result.output
    assert "Uruchomić teraz analizę głęboką?" in result.output
    assert deep_called == []


def test_processes_are_shown_without_cpu_or_memory_alerts(monkeypatch):
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda **kwargs: _snapshot(),
    )

    result = CliRunner().invoke(quick_cmd.quick, ["--no-save"])

    assert result.exit_code == 0
    assert "Najbardziej obciążające procesy teraz" in result.output
