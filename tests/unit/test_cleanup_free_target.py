"""Unit tests for the target-driven cleanup ladder (ticket-093)."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from click.testing import CliRunner

from fixos.cli import cleanup_cmd
from fixos.cli._cleanup_free_target import (
    TierResult,
    docker_call,
    find_stale_release_caches,
    free_bytes,
    remove_release_caches,
    run_free_target_ladder,
)

# ── free_bytes ────────────────────────────────────────────────────────────


def test_free_bytes_matches_statvfs():
    stat = os.statvfs("/")
    assert free_bytes("/") == stat.f_bavail * stat.f_frsize
    assert free_bytes("/nonexistent-path-xyz") == 0


# ── run_free_target_ladder ────────────────────────────────────────────────


def test_ladder_stops_as_soon_as_goal_reached():
    # Convention: one free_fn() call at start plus one before and one after
    # each tier.
    free_values = iter(
        [2 * 1024**3, 4 * 1024**3, 8 * 1024**3, 8 * 1024**3, 12 * 1024**3]
    )
    calls = []

    def free_fn():
        return next(free_values)

    def tier(name, freed_marker):
        def _tier():
            calls.append(freed_marker)
            return TierResult(name)

        return _tier

    report = run_free_target_ladder(
        10.0,
        tiers=[tier("a", 1), tier("b", 2), tier("c", 3)],
        free_fn=free_fn,
        echo=lambda _msg: None,
    )
    assert calls == [1, 2]  # third tier never runs
    assert report.goal_reached
    assert [t.name for t in report.tiers] == ["a", "b"]
    assert report.tiers[-1].bytes_freed == 4 * 1024**3


def test_ladder_runs_all_tiers_when_goal_unmet():
    free_values = iter([1024, 2048, 3072, 4096, 5120])

    def free_fn():
        return next(free_values)

    report = run_free_target_ladder(
        10.0,
        tiers=[lambda: TierResult("a"), lambda: TierResult("b")],
        free_fn=free_fn,
        echo=lambda _msg: None,
    )
    assert not report.goal_reached
    assert len(report.tiers) == 2


def test_ladder_skips_tiers_already_at_goal():
    def free_fn():
        return 20 * 1024**3

    ran = []

    def _tier():
        ran.append(1)
        return TierResult("a")

    report = run_free_target_ladder(
        10.0, tiers=[_tier], free_fn=free_fn, echo=lambda _msg: None
    )
    assert not ran
    assert report.goal_reached


def test_ladder_dry_run_measures_all_tiers():
    free_values = iter([1024, 5 * 1024**3, 9 * 1024**3])

    def free_fn():
        return next(free_values)

    ran = []

    def _tier():
        ran.append(1)
        return TierResult("a")

    run_free_target_ladder(
        8.0,
        tiers=[_tier],
        free_fn=free_fn,
        echo=lambda _msg: None,
        dry_run=True,
    )
    # dry-run never breaks early on measured deltas
    assert ran == [1]


# ── stale release caches ──────────────────────────────────────────────────


def _make_release_tree(
    root: Path, owner: str, name: str, age_days: float, payload=b"x" * 4096
):
    entry = root / owner / "releases" / name
    entry.mkdir(parents=True)
    (entry / "payload.bin").write_bytes(payload)
    stamp = time.time() - age_days * 86400
    os.utime(entry, (stamp, stamp))
    return entry


def test_find_stale_release_caches_selects_only_old_entries(tmp_path):
    old = _make_release_tree(tmp_path, "agent-a", "rel-old", age_days=10)
    _make_release_tree(tmp_path, "agent-a", "rel-new", age_days=1)
    removable, protected = find_stale_release_caches(share_root=tmp_path, min_days=7.0)
    assert [e["path"] for e in removable] == [old]
    assert protected == []


def test_find_stale_release_caches_reports_readonly_as_protected(tmp_path):
    old = _make_release_tree(tmp_path, "agent-b", "rel-locked", age_days=30)
    parent = old.parent
    os.chmod(parent, 0o555)
    try:
        removable, protected = find_stale_release_caches(
            share_root=tmp_path, min_days=7.0
        )
        assert removable == []
        assert [e["path"] for e in protected] == [old]
    finally:
        os.chmod(parent, 0o755)


def test_readonly_protection_also_holds_under_root(tmp_path, monkeypatch):
    # CI distro jobs run as root, where os.access(W_OK) is always True;
    # the write-bit check must still classify the tree as protected.
    old = _make_release_tree(tmp_path, "agent-e", "rel-root", age_days=30)
    parent = old.parent
    os.chmod(parent, 0o555)
    monkeypatch.setattr(os, "access", lambda *_a, **_k: True)
    try:
        removable, protected = find_stale_release_caches(
            share_root=tmp_path, min_days=7.0
        )
        assert removable == []
        assert [e["path"] for e in protected] == [old]
    finally:
        os.chmod(parent, 0o755)


def test_remove_release_caches_skips_failures_and_returns_bytes(tmp_path, monkeypatch):
    kept = _make_release_tree(tmp_path, "agent-c", "rel-busy", age_days=30)
    gone = _make_release_tree(tmp_path, "agent-c", "rel-gone", age_days=30)

    import shutil as real_shutil

    original_rmtree = real_shutil.rmtree

    def fake_rmtree(path, **_kwargs):
        if Path(path) == kept:
            raise OSError("device busy")
        original_rmtree(path, **_kwargs)

    monkeypatch.setattr("fixos.cli._cleanup_free_target.shutil.rmtree", fake_rmtree)
    reclaimed = remove_release_caches(
        [
            {"path": kept, "size_bytes": 123},
            {"path": gone, "size_bytes": 456},
        ]
    )
    assert reclaimed == 456
    assert kept.exists()
    assert not gone.exists()


def test_remove_release_caches_refuses_readonly_even_under_root(tmp_path, monkeypatch):
    entry = _make_release_tree(tmp_path, "agent-f", "rel-locked", age_days=30)
    os.chmod(entry, 0o555)
    monkeypatch.setattr(os, "access", lambda *_a, **_k: True)
    try:
        reclaimed = remove_release_caches([{"path": entry, "size_bytes": 100}])
        assert reclaimed == 0
        assert entry.exists()
    finally:
        os.chmod(entry, 0o755)


def test_remove_release_caches_dry_run_keeps_everything(tmp_path):
    entry = _make_release_tree(tmp_path, "agent-d", "rel-x", age_days=30)
    reclaimed = remove_release_caches(
        [{"path": entry, "size_bytes": 100}], dry_run=True
    )
    assert reclaimed == 100
    assert entry.exists()


# ── docker robustness ─────────────────────────────────────────────────────


def test_docker_call_times_out_instead_of_hanging(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="docker", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, reason = docker_call(["system", "df"], timeout=1)
    assert not ok
    assert "timed out" in reason


def test_docker_call_reports_missing_binary(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, reason = docker_call(["ps"])
    assert not ok
    assert "not available" in reason


def test_docker_used_refs_parses_names_and_digests(monkeypatch):
    import fixos.cli._cleanup_free_target as target

    def fake_docker_call(args, timeout=30):
        assert args[:3] == ["ps", "-a", "--format"]
        return True, "sha256:abc123\npostgres:16-alpine\nsha256:abc123\n\n"

    monkeypatch.setattr(target, "docker_call", fake_docker_call)
    used = target._docker_used_image_refs(30)
    assert used == ({"abc123"}, {"postgres:16-alpine"})


# ── CLI wiring ────────────────────────────────────────────────────────────


def test_free_gb_runs_ladder_and_reports_goal(monkeypatch, tmp_path):
    captured = {}

    def fake_mode(goal_gb, threshold_mb, json_output, dry_run, days):
        captured.update(
            goal_gb=goal_gb,
            threshold_mb=threshold_mb,
            dry_run=dry_run,
            days=days,
        )

    monkeypatch.setattr(cleanup_cmd, "_run_free_target_mode", fake_mode)
    runner = CliRunner()
    result = runner.invoke(
        cleanup_cmd.cleanup_services,
        ["--free-gb", "12", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert captured["goal_gb"] == 12.0
    assert captured["dry_run"] is True


def test_free_gb_rejects_other_actions():
    runner = CliRunner()
    result = runner.invoke(
        cleanup_cmd.cleanup_services,
        ["--free-gb", "10", "--docker-old"],
    )
    assert result.exit_code != 0
    assert "osobną akcję" in result.output


def test_threshold_gb_keeps_per_service_semantics(monkeypatch):
    # --threshold-gb must still only override the scan threshold (regression
    # guard for the trap fixed in ticket-093).
    seen = {}

    class FakeScanner:
        def __init__(self, threshold_mb):
            seen["threshold_mb"] = threshold_mb

        def get_cleanup_plan(self, selected_services=None):
            return {
                "services": [],
                "services_found": 0,
                "safe_to_cleanup": [],
                "requires_review": [],
                "dangerous": [],
            }

    monkeypatch.setattr(cleanup_cmd, "ServiceDataScanner", FakeScanner)
    runner = CliRunner()
    result = runner.invoke(
        cleanup_cmd.cleanup_services, ["--threshold-gb", "2", "--list"]
    )
    assert result.exit_code == 0, result.output
    assert seen["threshold_mb"] == 2048
