import json

import pytest
from click.testing import CliRunner

from fixos.cli import anomalies_cmd


def _unexpected_scan(*args, **kwargs):
    pytest.fail("process-only diagnostics entered an unrequested scan")


def test_process_only_json_skips_disk_scans(monkeypatch):
    finding = {"category": "zombie-processes", "evidence": {"parent_pid": 123, "count": 17}}
    monkeypatch.setattr(anomalies_cmd, "scan_all", _unexpected_scan)
    monkeypatch.setattr(anomalies_cmd, "scan_processes", lambda: [finding])

    result = CliRunner().invoke(anomalies_cmd.anomalies, ["--processes-only", "--json"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["schema"] == "fixos.host-anomalies/v1"
    assert report["scan_scope"] == "processes"
    assert report["findings"] == [finding]
    assert report["reclaimable_bytes"] == 0


@pytest.mark.parametrize("removal", [["--remove-safe"], ["--remove", "/tmp/example"]])
def test_process_only_rejects_removal_before_scanning(monkeypatch, removal):
    monkeypatch.setattr(anomalies_cmd, "scan_all", _unexpected_scan)
    monkeypatch.setattr(anomalies_cmd, "scan_processes", _unexpected_scan)

    result = CliRunner().invoke(anomalies_cmd.anomalies, ["--processes-only", *removal])

    assert result.exit_code == 2
    assert "--processes-only" in result.output
