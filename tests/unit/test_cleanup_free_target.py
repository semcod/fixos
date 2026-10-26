"""Unit tests for the target-driven cleanup ladder (ticket-093)."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
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


def test_find_stale_release_caches_preserves_writable_old_entries(tmp_path):
    old = _make_release_tree(tmp_path, "agent-a", "rel-old", age_days=10)
    _make_release_tree(tmp_path, "agent-a", "rel-new", age_days=1)
    removable, protected = find_stale_release_caches(share_root=tmp_path, min_days=7.0)
    assert removable == []
    assert [e["path"] for e in protected] == [old]
    assert protected[0]["reason"] == "persistent deployment/rollback data"
    assert protected[0]["size_measured"] is False


@pytest.mark.parametrize("parent_name", ["releases", "release", "snapshots"])
def test_old_release_referenced_by_unit_and_current_link_is_preserved(tmp_path, parent_name, monkeypatch):
    share = tmp_path / "share"
    release = share / "agent" / parent_name / "pinned"
    release.mkdir(parents=True)
    payload = release / "worker.py"
    payload.write_text("# immutable deployed worker\n")
    stamp = time.time() - 8 * 86400
    os.utime(release, (stamp, stamp))
    (release.parent / "current").symlink_to(release, target_is_directory=True)
    unit = tmp_path / "worker.service"
    unit.write_text(f"[Service]\nExecStart=/usr/bin/python3 {payload}\nWorkingDirectory={release}\n")
    original_iterdir = Path.iterdir

    def no_payload_walk(path):
        assert path != release, "protected payloads must not be traversed to estimate space"
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", no_payload_walk)
    removable, protected = find_stale_release_caches(share_root=share)
    assert removable == []
    assert [entry["path"] for entry in protected] == [release]
    assert remove_release_caches(protected) == 0
    assert payload.read_text() == "# immutable deployed worker\n"


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


def test_remove_release_caches_rejects_precomputed_and_forged_candidates(tmp_path, monkeypatch):
    kept = _make_release_tree(tmp_path, "agent-c", "rel-busy", age_days=30)
    other = tmp_path / "Documents"
    other.mkdir()
    payload = other / "important.txt"
    payload.write_text("keep")

    def forbidden_delete(*_args, **_kwargs):
        pytest.fail("release cleanup must never attempt recursive deletion")

    monkeypatch.setattr("shutil.rmtree", forbidden_delete)
    reclaimed = remove_release_caches(
        [
            {"path": kept, "size_bytes": 123},
            {"path": other, "size_bytes": 456},
        ]
    )
    assert reclaimed == 0
    assert kept.exists()
    assert payload.read_text() == "keep"


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
    assert reclaimed == 0
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


@pytest.mark.parametrize("dry_run", [False, True])
def test_free_target_ladder_preserves_releases_and_continues_cache_tiers(monkeypatch, tmp_path, capsys, dry_run):
    import fixos.cli._cleanup_free_target as target

    release = _make_release_tree(tmp_path, "agent", "old", age_days=30)
    candidates = target.find_stale_release_caches(share_root=tmp_path)
    monkeypatch.setattr(cleanup_cmd, "find_stale_release_caches", lambda: candidates)
    monkeypatch.setattr(target, "free_bytes", lambda *_: 0)
    monkeypatch.setattr(cleanup_cmd, "print_privileged_hints", lambda *_: None)
    monkeypatch.setattr(cleanup_cmd, "_cleanup_tmp", lambda *_a, **_k: None)
    monkeypatch.setattr(cleanup_cmd, "_cleanup_state_old", lambda *_a, **_k: None)
    monkeypatch.setattr(cleanup_cmd, "_cleanup_projects_old", lambda *_a, **_k: None)

    class EmptyScanner:
        def __init__(self, **_kwargs):
            pass

        def get_cleanup_plan(self, **_kwargs):
            return {}

    monkeypatch.setattr(cleanup_cmd, "ServiceDataScanner", EmptyScanner)
    monkeypatch.setattr(cleanup_cmd, "_execute_yes_cleanup", lambda *_a, **_k: None)
    calls = []

    def cache_tier(name):
        calls.append(name)
        return TierResult(name)

    monkeypatch.setattr(cleanup_cmd, "docker_prune_dangling", lambda: cache_tier("dangling"))
    monkeypatch.setattr(cleanup_cmd, "docker_remove_unused_old_images", lambda **_: cache_tier("images"))
    cleanup_cmd._run_free_target_mode(10, 100, False, dry_run, None)
    output = capsys.readouterr().out
    assert "1 starych katalogów zachowanych" in output
    assert "dane wdrożeń i przywracania, nie cache" in output
    assert (release / "payload.bin").read_bytes() == b"x" * 4096
    assert calls == ([] if dry_run else ["dangling", "images"])


def test_free_gb_rejects_other_actions():
    runner = CliRunner()
    result = runner.invoke(
        cleanup_cmd.cleanup_services,
        ["--free-gb", "10", "--docker-old"],
    )
    assert result.exit_code != 0
    assert "osobną akcję" in result.output


def test_free_target_ladder_runs_7d_state_and_unused_projects_tiers(monkeypatch, tmp_path):
    import fixos.cli._cleanup_free_target as target

    monkeypatch.setattr(cleanup_cmd, "find_stale_release_caches", lambda: ([], []))
    monkeypatch.setattr(target, "free_bytes", lambda *_: 0)
    monkeypatch.setattr(cleanup_cmd, "print_privileged_hints", lambda *_: None)
    monkeypatch.setattr(cleanup_cmd, "_cleanup_tmp", lambda *_a, **_k: None)

    class EmptyScanner:
        def __init__(self, **_kwargs):
            pass

        def get_cleanup_plan(self, **_kwargs):
            return {}

    monkeypatch.setattr(cleanup_cmd, "ServiceDataScanner", EmptyScanner)
    monkeypatch.setattr(cleanup_cmd, "_execute_yes_cleanup", lambda *_a, **_k: None)
    monkeypatch.setattr(cleanup_cmd, "docker_prune_dangling", lambda: TierResult("dangling"))
    monkeypatch.setattr(
        cleanup_cmd, "docker_remove_unused_old_images", lambda **_: TierResult("images")
    )

    state_days = []
    project_days = []
    monkeypatch.setattr(
        cleanup_cmd,
        "_cleanup_state_old",
        lambda *_a, **kw: state_days.append(kw.get("days")),
    )
    monkeypatch.setattr(
        cleanup_cmd,
        "_cleanup_projects_old",
        lambda *_a, **kw: project_days.append(kw.get("days")),
    )

    cleanup_cmd._run_free_target_mode(10, 100, False, False, None)
    assert state_days == [7]
    assert project_days == [7]



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
