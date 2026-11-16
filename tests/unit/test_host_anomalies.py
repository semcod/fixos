"""Tests for host anomaly detection."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from click.testing import CliRunner

from fixos.diagnostics import host_anomalies as ha

OLD = time.time() - 30 * 86400
MIB = 1024 * 1024


def _write(path: Path, size: int = 10, when: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    if when is not None:
        os.utime(path, (when, when))
    return path


def _du_runner(sizes: dict[Path, int]):
    def run(command):
        if command[0] != "du":
            return ""
        root = Path(command[-1])
        return "".join(
            f"{size}\t{path}\n"
            for path, size in sizes.items()
            if path == root or root in path.parents
        )

    return run


def test_restart_loop_reports_looping_unit_and_ignores_stable_ones():
    system = (
        "Id=k3s.service\nNRestarts=16881\nActiveState=activating\n"
        "SubState=auto-restart\n\n"
        "Id=cron.service\nNRestarts=0\nActiveState=active\nSubState=running\n\n"
        "Id=journald.service\nNRestarts=60\nActiveState=active\nSubState=running\n"
    )
    user = "Id=tunnel.service\nNRestarts=704\nActiveState=active\nSubState=running\n"

    def run(command):
        return user if "--user" in command else system

    found = ha.scan_restart_loops(run=run)

    assert [f["subject"] for f in found] == ["k3s.service", "tunnel.service"]
    assert found[0]["severity"] == "high"
    assert "systemctl disable --now k3s.service" in found[0]["suggested_commands"]
    assert found[1]["severity"] == "medium"
    assert (
        "systemctl --user disable --now tunnel.service"
        in (found[1]["suggested_commands"])
    )


def test_container_logs_flag_missing_rotation_and_large_logs(tmp_path):
    daemon = tmp_path / "daemon.json"
    daemon.write_text(json.dumps({"default-address-pools": []}))
    root = tmp_path / "containers"
    big = _write(root / ("a" * 64) / ("a" * 64 + "-json.log"), 3 * MIB)
    _write(root / ("b" * 64) / ("b" * 64 + "-json.log"), 10)

    found = ha.scan_container_logs(
        containers_root=root, daemon_json=daemon, min_bytes=MIB
    )

    assert found[0]["subject"] == str(daemon)
    assert found[0]["evidence"]["rotation_configured"] is False
    assert [f["subject"] for f in found[1:]] == [str(big)]


def test_container_logs_accept_configured_rotation(tmp_path):
    daemon = tmp_path / "daemon.json"
    daemon.write_text(json.dumps({"log-opts": {"max-size": "50m"}}))
    root = tmp_path / "containers"
    _write(root / ("a" * 64) / ("a" * 64 + "-json.log"), 3 * MIB)

    found = ha.scan_container_logs(
        containers_root=root, daemon_json=daemon, min_bytes=MIB
    )

    assert [f["severity"] for f in found] == ["low"]


def test_stale_state_reports_topmost_stale_directory_only(tmp_path):
    state = tmp_path / ".local/state"
    backups = state / "codex/run-1/backups"
    _write(backups / "a.tar", when=OLD)
    _write(backups / "deep/b.tar", when=OLD)
    _write(state / "codex/run-1/notes.txt")  # recent sibling keeps run-1 live
    _write(state / "subactor/diagnostics/checkpoint.sqlite3")  # live store
    sizes = {
        state: 40,
        state / "codex": 20,
        state / "codex/run-1": 20,
        backups: 18,
        backups / "deep": 9,
        state / "subactor": 20,
        state / "subactor/diagnostics": 20,
    }

    found = ha.scan_stale_state(
        tmp_path, run=_du_runner(sizes), min_bytes=10, min_age_days=14
    )

    assert [f["subject"] for f in found] == [str(backups)]
    assert found[0]["severity"] == "review" and found[0]["removable"] is True


def test_stale_state_never_offers_protected_directories(tmp_path):
    secret = tmp_path / ".local/share/keys/.ssh"
    _write(secret / "id", when=OLD)
    sizes = {tmp_path / ".local/share/keys": 50, secret: 50}

    found = ha.scan_stale_state(
        tmp_path, run=_du_runner(sizes), min_bytes=10, min_age_days=14
    )

    assert str(secret) not in [f["subject"] for f in found]


def test_ide_index_is_safe_only_when_ide_is_not_running(tmp_path):
    index = tmp_path / ".cache/JetBrains/PyCharm2026.3/index"
    _write(index / "stubs.bin")
    proc = tmp_path / "proc"
    _write(proc / "100/cmdline", 1).write_bytes(b"/usr/bin/bash\0-c\0true")
    run = _du_runner({index: 50})

    idle = ha.scan_ide_indexes(tmp_path, run=run, proc=proc, min_bytes=10)
    _write(proc / "200/cmdline", 1).write_bytes(
        b"java\0-Didea.paths.selector=PyCharm2026.3"
    )
    busy = ha.scan_ide_indexes(tmp_path, run=run, proc=proc, min_bytes=10)

    assert idle[0]["severity"] == "safe" and idle[0]["removable"] is True
    assert busy[0]["severity"] == "protected" and busy[0]["removable"] is False


def _stat(pid: int, comm: str, state: str, parent: int, start_ticks: int) -> str:
    rest = [state, str(parent)] + ["0"] * 17 + [str(start_ticks)] + ["0"] * 10
    return f"{pid} ({comm}) " + " ".join(rest)


def test_processes_report_zombies_per_parent_and_idle_groups(tmp_path):
    proc = tmp_path / "proc"
    for pid in range(1000, 1012):
        _write(proc / str(pid) / "stat").write_text(_stat(pid, "python", "Z", 15, 0))
    for pid in range(2000, 2060):
        _write(proc / str(pid) / "stat").write_text(
            _stat(pid, "mime helper", "S", 16, 0)
        )
        (proc / str(pid) / "cmdline").write_bytes(b"mime-helper\0--launch\0URL")
    for pid in range(4000, 4090):  # daemons sharing a name, one per port
        _write(proc / str(pid) / "stat").write_text(_stat(pid, "proxy", "S", 17, 0))
        (proc / str(pid) / "cmdline").write_bytes(b"proxy\0-port\0%d" % pid)
    _write(proc / "3000" / "stat").write_text(_stat(3000, "fresh", "S", 1, 99_000_000))

    found = ha.scan_processes(proc=proc, uptime=1_000_000.0, ticks=100)

    by_category = {f["category"]: f for f in found}
    assert by_category["zombie-processes"]["evidence"] == {
        "parent_pid": 15,
        "count": 12,
    }
    assert by_category["idle-process-group"]["subject"] == "mime helper"
    assert by_category["idle-process-group"]["evidence"]["count"] == 60
    assert (
        "pgrep -a -x mime helper"
        in (by_category["idle-process-group"]["suggested_commands"][0])
    )
    assert len(found) == 2


def test_remove_paths_deletes_only_current_removable_findings(tmp_path):
    home = tmp_path
    wanted = home / ".local/state/tool/backups"
    other = home / ".local/state/tool/live"
    _write(wanted / "a.bin")
    _write(other / "b.bin")
    findings = [
        ha._finding("stale-state", "review", wanted, "x", size_bytes=7),
        ha._finding("ide-index", "protected", other, "x", size_bytes=3),
    ]

    receipt = ha.remove_paths(
        [wanted, other, Path("/etc")],
        findings,
        home=home,
        receipt_dir=home / "receipts",
    )

    assert not wanted.exists() and other.exists()
    assert [item["path"] for item in receipt["removed"]] == [str(wanted)]
    assert {item["reason"] for item in receipt["refused"]} == {
        "not_a_current_removable_finding"
    }
    assert receipt["freed_bytes"] == 7
    assert json.loads(Path(receipt["receipt_path"]).read_text())["schema"] == (
        ha.RECEIPT_SCHEMA
    )


def test_remove_paths_refuses_symlink_and_paths_outside_home(tmp_path):
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    _write(outside / "data.bin")
    link = home / ".local/state/link"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    findings = [
        ha._finding("stale-state", "review", link, "x", size_bytes=1),
        ha._finding("stale-state", "review", outside, "x", size_bytes=1),
    ]

    receipt = ha.remove_paths([link, outside], findings, home=home)

    assert outside.exists() and (outside / "data.bin").exists()
    assert [item["reason"] for item in receipt["refused"]] == [
        "not_a_plain_directory",
        "outside_home",
    ]


def test_cli_reports_and_dry_run_removes_nothing(tmp_path, monkeypatch):
    from fixos.cli import anomalies_cmd

    target = tmp_path / ".cache/JetBrains/PyCharm2026.3/index"
    _write(target / "stubs.bin")
    finding = ha._finding("ide-index", "safe", target, "Indeks", size_bytes=5)
    monkeypatch.setattr(
        anomalies_cmd,
        "scan_all",
        lambda **_: {
            "schema": ha.SCHEMA,
            "findings": [finding],
            "reclaimable_bytes": 5,
        },
    )

    result = CliRunner().invoke(
        anomalies_cmd.anomalies, ["--remove-safe", "--dry-run", "--json"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["would_remove"] == [str(target)]
    assert target.exists()


def test_remove_paths_removes_trees_with_read_only_directories(tmp_path):
    home = tmp_path
    target = home / ".local/state/tool/copied-store"
    _write(target / "locked/deep/data.bin")
    for directory in (target / "locked/deep", target / "locked"):
        directory.chmod(0o555)
    findings = [ha._finding("stale-state", "review", target, "x", size_bytes=10)]

    receipt = ha.remove_paths([target], findings, home=home)

    assert not target.exists()
    assert [item["path"] for item in receipt["removed"]] == [str(target)]
    assert receipt["partial"] == [] and receipt["refused"] == []


def test_remove_paths_reports_partial_removal_with_remaining_bytes(
    tmp_path, monkeypatch
):
    home = tmp_path
    target = home / ".local/state/tool/mixed"
    _write(target / "mine.bin", 40)
    foreign = _write(target / "foreign/kept.bin", 60)
    real_unlink = os.unlink

    def unlink(path, *args, **kwargs):
        if str(path).endswith("kept.bin"):
            raise PermissionError(13, "Permission denied", str(path))
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", unlink)
    findings = [ha._finding("stale-state", "review", target, "x", size_bytes=100)]

    receipt = ha.remove_paths(
        [target], findings, home=home, receipt_dir=home / "receipts"
    )

    assert foreign.exists() and not (target / "mine.bin").exists()
    assert receipt["removed"] == [] and receipt["refused"] == []
    assert receipt["partial"][0]["reason"] == "os_error:13"
    assert 0 < receipt["partial"][0]["remaining_bytes"] < 100 * 1024
    assert receipt["freed_bytes"] == receipt["partial"][0]["freed_bytes"]
    assert Path(receipt["receipt_path"]).is_file()
