"""Tests for fixos.cli._cleanup_space._cleanup_tmp and --tmp CLI option."""

import json
import os
import time
from pathlib import Path

import click
from click.testing import CliRunner

from fixos.cli import _cleanup_space as space
from fixos.cli import cleanup_cmd


def _invoke(fn, *args, **kwargs):
    input_text = kwargs.pop("input_text", "")

    @click.command()
    def command():
        fn(*args, **kwargs)

    return CliRunner().invoke(command, input=input_text)


def test_cleanup_tmp_empty_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(space, "Path", lambda p: tmp_path if p == "/tmp" else Path(p))
    result = _invoke(space._cleanup_tmp, False, False, True, False, days=1.0)
    assert result.exit_code == 0
    assert "Brak plików w /tmp starszych niż 1.0 dni" in result.output


def test_cleanup_tmp_filters_by_age_and_excludes_system_files(monkeypatch, tmp_path):
    # Mock Path("/tmp") to point to tmp_path
    monkeypatch.setattr(space, "Path", lambda p: tmp_path if p == "/tmp" else Path(p))

    now = time.time()
    old_time = now - 2 * 86400  # 2 days old
    recent_time = now - 0.5 * 86400  # 12 hours old

    # Excluded files/dirs even if old
    x11 = tmp_path / ".X11-unix"
    x11.mkdir()
    os.utime(x11, (old_time, old_time))

    x_lock = tmp_path / ".X0-lock"
    x_lock.write_text("1234")
    os.utime(x_lock, (old_time, old_time))

    ice = tmp_path / ".ICE-unix"
    ice.mkdir()
    os.utime(ice, (old_time, old_time))

    # Recent file (should not be candidate)
    recent_file = tmp_path / "recent.txt"
    recent_file.write_text("new")
    os.utime(recent_file, (recent_time, recent_time))

    # Old file (should be candidate)
    old_file = tmp_path / "old.txt"
    old_file.write_text("old content")
    os.utime(old_file, (old_time, old_time))

    # Old directory (should be candidate)
    old_dir = tmp_path / "old_dir"
    old_dir.mkdir()
    (old_dir / "sub.txt").write_text("sub")
    os.utime(old_dir, (old_time, old_time))

    result = _invoke(space._cleanup_tmp, False, False, True, False, days=1.0)
    assert result.exit_code == 0
    assert "old.txt" in result.output
    assert "old_dir" in result.output
    assert "recent.txt" not in result.output
    assert ".X11-unix" not in result.output
    assert ".X0-lock" not in result.output
    assert ".ICE-unix" not in result.output


def test_cleanup_tmp_json_output(monkeypatch, tmp_path):
    monkeypatch.setattr(space, "Path", lambda p: tmp_path if p == "/tmp" else Path(p))
    now = time.time()
    old_time = now - 3 * 86400

    old_file = tmp_path / "stale.log"
    old_file.write_text("stale data")
    os.utime(old_file, (old_time, old_time))

    result = _invoke(space._cleanup_tmp, True, False, False, False, days=1.0)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["days"] == 1.0
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["path"] == str(old_file)


def test_cleanup_tmp_dry_run(monkeypatch, tmp_path):
    monkeypatch.setattr(space, "Path", lambda p: tmp_path if p == "/tmp" else Path(p))
    now = time.time()
    old_time = now - 2 * 86400

    old_file = tmp_path / "to_delete.txt"
    old_file.write_text("content")
    os.utime(old_file, (old_time, old_time))

    result = _invoke(space._cleanup_tmp, False, True, False, False, days=1.0, input_text="all\n")
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output
    assert old_file.exists()


def test_cleanup_tmp_removes_with_yes(monkeypatch, tmp_path):
    monkeypatch.setattr(space, "Path", lambda p: tmp_path if p == "/tmp" else Path(p))
    now = time.time()
    old_time = now - 2 * 86400

    old_file = tmp_path / "del.txt"
    old_file.write_text("delete me")
    os.utime(old_file, (old_time, old_time))

    result = _invoke(space._cleanup_tmp, False, False, False, True, days=1.0)
    assert result.exit_code == 0
    assert not old_file.exists()


def test_cleanup_cli_tmp_flag(monkeypatch, tmp_path):
    runner = CliRunner()
    result = runner.invoke(cleanup_cmd.cleanup_services, ["--tmp", "--list", "--dry-run"])
    assert result.exit_code == 0


def test_cleanup_cli_threshold_gb(monkeypatch):
    from fixos.diagnostics.service_scanner import ServiceDataScanner

    captured_threshold = []

    def fake_init(self, threshold_mb=500):
        captured_threshold.append(threshold_mb)
        self.threshold_mb = threshold_mb

    monkeypatch.setattr(ServiceDataScanner, "__init__", fake_init)
    monkeypatch.setattr(
        ServiceDataScanner,
        "get_cleanup_plan",
        lambda self, selected_services=None: {
            "services_found": 0,
            "services": [],
            "safe_to_cleanup": [],
            "requires_review": [],
            "dangerous": [],
            "total_size_gb": 0.0,
            "safe_cleanup_gb": 0.0,
            "safe_prune_gb": 0.0,
            "requires_review_gb": 0.0,
            "dangerous_gb": 0.0,
            "manager_reported_reclaimable_gb": 0.0,
            "warnings": [],
        },
    )

    runner = CliRunner()
    result = runner.invoke(cleanup_cmd.cleanup_services, ["--threshold-gb", "10", "--list"])
    assert result.exit_code == 0
    assert captured_threshold == [10240]


def test_service_cleaner_tmp_and_buildcache_in_safe_actions(monkeypatch, tmp_path):
    from fixos.diagnostics.service_cleanup import ServiceCleaner
    from fixos.diagnostics.service_scanner import ServiceDataInfo, ServiceType

    class FakeScanner:
        threshold_mb = 500
        SERVICE_PATHS = {}

        def scan_all_services(self):
            return []

        def scan_service(self, service_type):
            if service_type == ServiceType.DOCKER:
                return [
                    ServiceDataInfo(
                        service_type=ServiceType.DOCKER,
                        name="Docker",
                        path="/var/lib/docker",
                        size_mb=1000.0,
                        size_gb=1.0,
                        description="Docker test",
                        can_cleanup=True,
                        cleanup_command="docker builder prune",
                        preview_command="docker system df",
                        safe_to_cleanup=True,
                        details={"usage": {}},
                    )
                ]
            return []

    cleaner = ServiceCleaner(FakeScanner())

    # Add old file to tmp_path
    now = time.time()
    old_file = tmp_path / "old_stale_artifact.log"
    old_file.write_text("lots of stale logs")
    os.utime(old_file, (now - 3 * 86400, now - 3 * 86400))

    # Mock scan_docker_buildcache to return a test target
    monkeypatch.setattr(
        cleaner,
        "scan_docker_buildcache",
        lambda: {
            "error": None,
            "targets": [
                {
                    "name": "arm64-builder",
                    "driver": "docker-container",
                    "reclaimable_bytes": 1024 * 1024 * 1024,
                    "command": ["echo", "pruning arm64-builder"],
                }
            ],
        },
    )

    actions = cleaner.build_safe_age_actions()
    kinds = [a["cleanup_kind"] for a in actions]
    assert "docker-buildcache" in kinds
    # When scanning tmp_path
    tmp_actions = cleaner.scan_tmp_candidates(days=1.0, tmp_dir=tmp_path)
    assert len(tmp_actions) == 1
    assert tmp_actions[0]["name"] == "old_stale_artifact.log"

    # Test cleaner.cleanup_tmp dry run and execution
    dry_result = cleaner.cleanup_tmp(days=1.0, dry_run=True, tmp_dir=tmp_path)
    assert dry_result["success"] is True
    assert "[DRY RUN]" in dry_result["output"]
    assert old_file.exists()

    exec_result = cleaner.cleanup_tmp(days=1.0, dry_run=False, tmp_dir=tmp_path)
    assert exec_result["success"] is True
    assert not old_file.exists()

    # Test cleaner.cleanup_docker_buildcache dry run and execution
    buildcache_dry = cleaner.cleanup_docker_buildcache(dry_run=True)
    assert buildcache_dry["success"] is True
    assert "[DRY RUN]" in buildcache_dry["output"]

    buildcache_exec = cleaner.cleanup_docker_buildcache(dry_run=False)
    assert buildcache_exec["success"] is True

