"""Regression tests for critical memory candidates in `fixos auto` (issue #233 / #227)."""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from fixos.cli import _auto_cleanup as auto
from fixos.cli import _cleanup_space as space
from fixos.cli.main import cli
from fixos.diagnostics import memory_candidates as mc
from fixos.diagnostics import quick_snapshot
from fixos.diagnostics.process_chains import ProcessRecord


NOW = datetime(2026, 11, 28, 18, 0, tzinfo=timezone.utc)
NOW_EPOCH = NOW.timestamp()
GIB = 1024**3


def _cli_runner() -> CliRunner:
    if "mix_stderr" in inspect.signature(CliRunner.__init__).parameters:
        return CliRunner(mix_stderr=False)
    return CliRunner()


def _proc(
    pid: int,
    ppid: int,
    name: str,
    cmdline: tuple[str, ...],
    *,
    hours: float = 24.0,
    cpu_percent: float = 0.0,
    username: str = "tom",
) -> ProcessRecord:
    return ProcessRecord(
        pid=pid,
        ppid=ppid,
        name=name,
        cmdline=cmdline,
        create_time=NOW_EPOCH - hours * 3600.0,
        cpu_percent=cpu_percent,
        username=username,
    )


def _cleaner(
    records: list[ProcessRecord],
    *,
    rss_by_pid: dict[int, int] | None = None,
    swap_by_pid: dict[int, int] | None = None,
    cpu_time_by_pid: dict[int, float] | None = None,
    cgroups_by_pid: dict[int, str] | None = None,
    signalled: list[tuple[int, bool]] | None = None,
    alive: set[int] | None = None,
    identities: dict[int, float] | None = None,
) -> mc.IdleMemoryCandidateCleaner:
    rss = rss_by_pid or {}
    swap = swap_by_pid or {}
    cpu_time = cpu_time_by_pid or {}
    cgroups = cgroups_by_pid or {}
    id_map = (
        identities
        if identities is not None
        else {item.pid: item.create_time for item in records}
    )
    alive_set = alive if alive is not None else set()

    def terminate(pid: int, force: bool) -> None:
        if signalled is not None:
            signalled.append((pid, force))
        alive_set.discard(pid)

    return mc.IdleMemoryCandidateCleaner(
        process_provider=lambda: list(records),
        rss_provider=lambda pid: rss.get(pid, 0),
        vmswap_provider=lambda pid: swap.get(pid, 0),
        cpu_time_provider=lambda pid: cpu_time.get(pid, 0.0),
        cgroup_provider=lambda pid: cgroups.get(pid),
        identity_provider=id_map.get,
        terminator=terminate,
        alive_provider=lambda pid, ct: pid in alive_set
        and abs(id_map.get(pid, -1.0) - ct) < 0.001,
        now=lambda: NOW,
        self_pid=9999,
    )


def test_parse_proc_status_vmswap_bytes() -> None:
    status = "Name:\tbaobab\nVmRSS:\t4089446 kB\nVmSwap:\t21810380 kB\nThreads:\t6\n"
    assert mc.parse_proc_status_vmswap_bytes(status) == 21810380 * 1024
    assert mc.parse_proc_status_vmswap_bytes("Name:\tinit\nVmRSS:\t120 kB\n") == 0
    assert mc.parse_proc_status_vmswap_bytes("") == 0


def test_quick_snapshot_alerts_emit_critical_swap_and_preserve_warning_tier() -> None:
    thresholds = quick_snapshot._profile_thresholds("developer")
    assert thresholds["swap_usage_critical"] == 90

    critical_swap = {
        "disk": {"percent": 20, "free_bytes": 100 * GIB},
        "memory": {"percent": 92},
        "swap": {"total_bytes": 40 * GIB, "percent": 100},
        "cpu": {"percent": 5, "load_1_normalized_percent": 10},
    }
    alerts = quick_snapshot._alerts(critical_swap, {"escalating": []}, thresholds)
    by_res = {item["resource"]: item for item in alerts}
    assert by_res["memory"]["severity"] == "critical"
    assert by_res["swap"]["severity"] == "critical"

    assert mc.has_critical_memory_pressure({"alerts": alerts}) is True
    assert (
        mc.has_critical_memory_pressure(
            {
                "alerts": [],
                "resources": {
                    "memory": {"percent": 91},
                    "swap": {"total_bytes": 10 * GIB, "percent": 20},
                },
            }
        )
        is True
    )
    assert mc.has_critical_memory_pressure({}) is False

    # Callers omitting swap_usage_critical stay backward-compatible.
    partial_thresholds = {k: v for k, v in thresholds.items() if k != "swap_usage_critical"}
    warning_swap = {
        **critical_swap,
        "memory": {"percent": 40},
        "swap": {"total_bytes": 40 * GIB, "percent": 80},
    }
    warn_alerts = quick_snapshot._alerts(warning_swap, {"escalating": []}, partial_thresholds)
    assert next(a for a in warn_alerts if a["resource"] == "swap")["severity"] == "warning"


def test_scan_ranks_by_rss_plus_vmswap_and_protects_agents_and_services() -> None:
    records = [
        _proc(101, 1, "baobab", ("baobab", "/home/tom/github/semcod/fixos"), hours=45.0, cpu_percent=0.0),
        _proc(102, 1, "codex", ("codex", "--continue"), hours=18.0, cpu_percent=0.0),
        _proc(103, 1, "ollama", ("/usr/local/bin/ollama", "serve"), hours=100.0, cpu_percent=0.0),
        _proc(104, 1, "evince", ("evince", "/tmp/report.pdf"), hours=10.0, cpu_percent=25.0),
        _proc(105, 1, "eog", ("eog", "/tmp/pic.png"), hours=0.2, cpu_percent=0.0),
        _proc(106, 1, "okular", ("okular", "/tmp/big.pdf"), hours=2.1, cpu_percent=0.0),
        _proc(107, 1, "loupe", ("loupe", "/tmp/small.png"), hours=10.0, cpu_percent=0.0),
        _proc(108, 1, "vlc", ("vlc", "/tmp/video.mkv"), hours=10.0, cpu_percent=0.0),
    ]
    rss = {
        101: int(3.9 * GIB),
        102: int(11.4 * GIB),
        103: int(8.0 * GIB),
        104: int(1.5 * GIB),
        105: int(1.0 * GIB),
        106: int(1.2 * GIB),
        107: 50 * 1024**2,
        108: int(2.0 * GIB),
    }
    swap = {
        101: int(20.8 * GIB),
        102: int(3.4 * GIB),
        103: int(1.0 * GIB),
        104: 0,
        105: 0,
        106: 0,
        107: 0,
        108: 0,
    }
    cpu_time = {
        101: 12.0,
        102: 60.0,
        103: 100.0,
        104: 300.0,
        105: 5.0,
        106: 2.0 * 3600,  # 2.0h CPU in 2.1h runtime -> only 0.1h idle
        107: 1.0,
        108: 5.0,
    }
    cgroups = {
        108: "0::/system.slice/docker-0123456789abcdef.scope\n",
    }
    cleaner = _cleaner(
        records,
        rss_by_pid=rss,
        swap_by_pid=swap,
        cpu_time_by_pid=cpu_time,
        cgroups_by_pid=cgroups,
    )

    scan = cleaner.scan_memory(top_limit=3)
    assert [row["pid"] for row in scan["top_processes"]] == [101, 102, 103]
    assert scan["top_processes"][0]["total_memory_bytes"] == rss[101] + swap[101]

    assert [c["root_pid"] for c in scan["candidates"]] == [101]
    baobab = scan["candidates"][0]
    assert baobab["name"] == "baobab"
    assert baobab["age_hours"] == 45.0
    assert baobab["reclaimable_memory_bytes"] == rss[101] + swap[101]

    rejected = {r["root_pid"]: r["reasons"] for r in scan["rejected_gui_apps"]}
    assert "cpu-active" in rejected[104]
    assert "process-too-young" in rejected[105]
    assert "insufficient-idle-time" in rejected[106]
    assert "below-memory-threshold" in rejected[107]
    assert "containerized-process" in rejected[108]


def test_scan_aggregates_gui_child_tree_and_rejects_active_or_protected_child() -> None:
    records = [
        # Idle GUI tree whose memory comes from both root and helper child.
        _proc(300, 1, "evince", ("evince", "/tmp/big.pdf"), hours=12.0, cpu_percent=0.0),
        _proc(301, 300, "evinced", ("/usr/libexec/evinced",), hours=12.0, cpu_percent=0.0),
        _proc(302, 300, "evince", ("evince", "--preview"), hours=12.0, cpu_percent=0.0),
        # GUI parent whose child is CPU-active must be rejected.
        _proc(400, 1, "mpv", ("mpv", "/tmp/movie.mkv"), hours=12.0, cpu_percent=0.0),
        _proc(401, 400, "ffmpeg", ("ffmpeg", "-i", "in.mkv"), hours=12.0, cpu_percent=42.0),
        # GUI parent whose child is a protected session/service must be rejected.
        _proc(500, 1, "baobab", ("baobab", "/"), hours=12.0, cpu_percent=0.0),
        _proc(501, 500, "claude", ("claude",), hours=12.0, cpu_percent=0.0),
    ]
    rss = {300: 200 * 1024**2, 301: 150 * 1024**2, 302: 100 * 1024**2, 400: 1 * GIB, 500: 1 * GIB}
    swap = {300: 50 * 1024**2, 301: 50 * 1024**2, 302: 0, 400: 0, 500: 0}
    cleaner = _cleaner(records, rss_by_pid=rss, swap_by_pid=swap)

    scan = cleaner.scan_memory(top_limit=5)
    assert [c["root_pid"] for c in scan["candidates"]] == [300]
    evince = scan["candidates"][0]
    assert evince["process_count"] == 3
    assert evince["rss_bytes"] == 450 * 1024**2
    assert evince["vmswap_bytes"] == 100 * 1024**2
    assert evince["reclaimable_memory_bytes"] == 550 * 1024**2
    assert scan["estimated_reclaimable_bytes"] == 550 * 1024**2

    rejected = {r["root_pid"]: r["reasons"] for r in scan["rejected_gui_apps"]}
    assert "cpu-active" in rejected[400]
    assert "protected-process-or-ancestry" in rejected[500]
    assert 302 not in rejected


def test_close_candidates_dry_run_and_identity_safety_rechecks() -> None:
    records = [
        _proc(201, 1, "baobab", ("baobab", "/"), hours=10.0, cpu_percent=0.0),
    ]
    rss = {201: 1 * GIB}
    swap = {201: 2 * GIB}
    signalled: list[tuple[int, bool]] = []
    identities = {201: records[0].create_time}
    cleaner = _cleaner(
        records,
        rss_by_pid=rss,
        swap_by_pid=swap,
        cpu_time_by_pid={201: 1.0},
        signalled=signalled,
        identities=identities,
    )

    # Dry-run never signals.
    dry_res = cleaner.close_candidates(
        process_identities=[(201, records[0].create_time)],
        apply=False,
    )
    assert signalled == []
    assert len(dry_res["planned"]) == 1
    assert dry_res["closed"] == []

    # Recycled PID with different create_time is rejected before signalling.
    stale_res = cleaner.close_candidates(
        process_identities=[(201, records[0].create_time - 50.0)],
        apply=True,
        grace_seconds=0.0,
    )
    assert signalled == []
    assert stale_res["success"] is False
    assert stale_res["failed"][0]["error"] == "not an eligible idle candidate in the fresh scan"

    # Race check inside Inherited _apply_process when identity_provider flips before signal.
    identities[201] = records[0].create_time + 100.0
    race_res = cleaner.close_candidates(
        process_identities=[(201, records[0].create_time)],
        apply=True,
        grace_seconds=0.0,
    )
    assert signalled == []
    assert race_res["success"] is False
    assert race_res["failed"][0]["error"] == "root PID identity changed"

    # Matching live identity terminates gracefully (SIGTERM, force=False).
    identities[201] = records[0].create_time
    ok_res = cleaner.close_candidates(
        process_identities=[(201, records[0].create_time)],
        apply=True,
        grace_seconds=0.0,
    )
    assert ok_res["success"] is True
    assert len(ok_res["closed"]) == 1
    assert signalled == [(201, False)]


@pytest.fixture
def auto_memory_env(monkeypatch):
    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda _: SimpleNamespace(total=200 * GIB, free=50 * GIB),
    )
    monkeypatch.setattr(
        "fixos.config.FixOsConfig.load", lambda **k: SimpleNamespace(api_key="")
    )
    monkeypatch.setattr(
        "fixos.cli.fix_cmd.run_autonomous_session",
        lambda **k: SimpleNamespace(fixes_applied=[], problems_found=[]),
    )
    monkeypatch.setattr("fixos.cli.quick_cmd.render_quick_snapshot", lambda *a, **k: None)
    for name in (
        "tmp",
        "user_cache",
        "jetbrains",
        "build_caches",
        "snap_old",
        "journal",
        "trash",
        "thumbnails",
    ):
        monkeypatch.setattr(space, "_cleanup_" + name, Mock())
    monkeypatch.setattr(auto, "cleanup_additional_caches", Mock())
    monkeypatch.setattr(auto, "cleanup_docker_builder", Mock())

    state = {
        "ram_total_bytes": 64 * GIB,
        "ram_available_bytes": 4 * GIB,
        "ram_used_bytes": 60 * GIB,
        "ram_percent": 93.8,
        "swap_total_bytes": 40 * GIB,
        "swap_used_bytes": 40 * GIB,
        "swap_percent": 100.0,
    }
    monkeypatch.setattr(
        "fixos.diagnostics.memory_candidates.capture_memory_snapshot",
        lambda: dict(state),
    )

    records = [
        _proc(101, 1, "baobab", ("baobab", "/"), hours=45.0, cpu_percent=0.0),
        _proc(102, 1, "evince", ("evince", "/tmp/doc.pdf"), hours=12.0, cpu_percent=0.0),
        _proc(103, 1, "codex", ("codex",), hours=20.0, cpu_percent=0.0),
    ]
    rss = {101: int(3.9 * GIB), 102: int(0.8 * GIB), 103: int(11.4 * GIB)}
    swap = {101: int(20.8 * GIB), 102: int(0.4 * GIB), 103: int(3.4 * GIB)}
    signalled: list[tuple[int, bool]] = []
    identities = {item.pid: item.create_time for item in records}

    def build_cleaner():
        def terminate(pid: int, force: bool) -> None:
            signalled.append((pid, force))
            freed = rss.get(pid, 0) + swap.get(pid, 0)
            state["ram_available_bytes"] += rss.get(pid, 0)
            state["swap_used_bytes"] = max(0, state["swap_used_bytes"] - freed)

        return mc.IdleMemoryCandidateCleaner(
            process_provider=lambda: list(records),
            rss_provider=lambda pid: rss.get(pid, 0),
            vmswap_provider=lambda pid: swap.get(pid, 0),
            cpu_time_provider=lambda pid: 5.0,
            cgroup_provider=lambda pid: None,
            identity_provider=identities.get,
            terminator=terminate,
            alive_provider=lambda pid, ct: False,
            now=lambda: NOW,
            self_pid=9999,
        )

    monkeypatch.setattr("fixos.cli.fix_cmd._build_memory_cleaner", build_cleaner)
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda: {
            "alerts": [
                {
                    "resource": "memory",
                    "severity": "critical",
                    "message": "Zajętość RAM przekroczyła 90%.",
                },
                {
                    "resource": "swap",
                    "severity": "critical",
                    "message": "Swap przekroczył próg krytyczny 90%.",
                },
            ],
            "resources": {
                "memory": {"percent": 93.8},
                "swap": {"total_bytes": 40 * GIB, "percent": 100.0},
            },
        },
    )
    return signalled, state


def test_fixos_auto_critical_memory_lists_candidates_without_killing_by_default(
    auto_memory_env,
) -> None:
    signalled, _ = auto_memory_env
    result = _cli_runner().invoke(cli, ["auto", "--no-banner", "--no-disc"])
    assert result.exit_code == 0, result.output
    assert signalled == []
    assert "RSS + VmSwap" in result.output
    assert "baobab" in result.output
    assert "--close-idle-apps" in result.output
    assert "RAM dostępny" in result.output
    assert "Swap użyty" in result.output


def test_fixos_auto_close_idle_apps_dry_run_vs_apply(auto_memory_env) -> None:
    signalled, _ = auto_memory_env

    dry_res = _cli_runner().invoke(
        cli, ["auto", "--no-disc", "--close-idle-apps", "--dry-run", "--json"]
    )
    assert dry_res.exit_code == 0, dry_res.output
    assert signalled == []
    dry_payload = json.loads(dry_res.stdout)
    assert dry_payload["memory_pressure_critical"] is True
    assert [c["name"] for c in dry_payload["memory_candidates"]] == ["baobab", "evince"]
    assert dry_payload["memory_closed_apps"] == []
    assert "idle-apps" in dry_payload["steps_executed"]

    apply_res = _cli_runner().invoke(
        cli, ["auto", "--no-disc", "--close-idle-apps", "--json"]
    )
    assert apply_res.exit_code == 0, apply_res.output
    assert signalled == [(101, False), (102, False)]
    payload = json.loads(apply_res.stdout)
    assert [c["name"] for c in payload["memory_closed_apps"]] == ["baobab", "evince"]
    assert payload["memory_available_after_bytes"] > payload["memory_available_before_bytes"]
    assert payload["swap_freed_bytes"] > 0


def test_fixos_auto_interactive_prompts_and_closes_only_confirmed_app(
    auto_memory_env, monkeypatch
) -> None:
    signalled, _ = auto_memory_env
    monkeypatch.setattr("fixos.cli.fix_cmd._is_interactive_terminal", lambda: True)

    result = _cli_runner().invoke(
        cli,
        ["auto", "--no-banner", "--no-disc", "--interactive"],
        input="y\nn\n",
    )
    assert result.exit_code == 0, result.output
    assert signalled == [(101, False)]
    assert "baobab" in result.output


def test_fixos_auto_non_critical_memory_skips_process_scan_but_reports_summary(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda _: SimpleNamespace(total=200 * GIB, free=50 * GIB),
    )
    monkeypatch.setattr(
        "fixos.config.FixOsConfig.load", lambda **k: SimpleNamespace(api_key="")
    )
    monkeypatch.setattr(
        "fixos.cli.fix_cmd.run_autonomous_session",
        lambda **k: SimpleNamespace(fixes_applied=[], problems_found=[]),
    )
    monkeypatch.setattr("fixos.cli.quick_cmd.render_quick_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(
        "fixos.diagnostics.quick_snapshot.collect_quick_snapshot",
        lambda: {
            "alerts": [],
            "resources": {
                "memory": {"percent": 40.0},
                "swap": {"total_bytes": 40 * GIB, "percent": 10.0},
            },
        },
    )
    build_cleaner = Mock()
    monkeypatch.setattr("fixos.cli.fix_cmd._build_memory_cleaner", build_cleaner)

    result = _cli_runner().invoke(cli, ["auto", "--no-disc", "--json"])
    assert result.exit_code == 0, result.output
    build_cleaner.assert_not_called()
    payload = json.loads(result.stdout)
    assert payload["memory_pressure_critical"] is False
    assert payload["memory_candidates"] == []
    assert "memory_available_before_bytes" in payload
    assert "swap_used_before_bytes" in payload
