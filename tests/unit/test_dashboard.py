"""Unit tests for the visual dashboard and safe automated intervention."""

from __future__ import annotations

import json
import time
from pathlib import Path

from click.testing import CliRunner
from rich.console import Console

from fixos.cli.dashboard import (
    DashboardScanData,
    ProcessItem,
    StorageItem,
    classify_process_safety,
    collect_dashboard_scan,
    dashboard_cmd,
    execute_safe_cache_cleanup,
    execute_safe_process_termination,
    render_dashboard,
)
from fixos.diagnostics.process_chains import ProcessRecord


class TestClassifyProcessSafety:
    def test_protects_system_pids(self):
        proc = ProcessRecord(
            pid=1,
            ppid=0,
            name="systemd",
            cmdline=("/sbin/init",),
            create_time=time.time() - 3600,
            username="root",
        )
        safety, reason = classify_process_safety(proc, self_pid=999, now=time.time())
        assert safety == "protected"
        assert "PID <= 2" in reason

    def test_protects_self_pid(self):
        proc = ProcessRecord(
            pid=1234,
            ppid=100,
            name="python",
            cmdline=("python", "-m", "fixos", "dashboard"),
            cpu_percent=80.0,
            memory_percent=5.0,
            create_time=time.time() - 3600,
            username="tom",
        )
        safety, reason = classify_process_safety(proc, self_pid=1234, now=time.time())
        assert safety == "protected"
        assert "Bieżący proces" in reason

    def test_protects_privileged_accounts(self):
        proc = ProcessRecord(
            pid=4567,
            ppid=1,
            name="custom-daemon",
            cmdline=("/usr/bin/custom-daemon",),
            cpu_percent=90.0,
            memory_percent=10.0,
            create_time=time.time() - 3600,
            username="root",
        )
        safety, reason = classify_process_safety(proc, self_pid=999, now=time.time())
        assert safety == "protected"
        assert "uprzywilejowanego" in reason

    def test_protects_ide_and_shell_processes(self):
        for name in ("pycharm", "idea", "code", "cursor", "bash", "tmux", "alacritty"):
            proc = ProcessRecord(
                pid=5000,
                ppid=1,
                name=name,
                cmdline=(f"/usr/bin/{name}",),
                cpu_percent=95.0,
                memory_percent=30.0,
                create_time=time.time() - 3600,
                username="tom",
            )
            safety, _reason = classify_process_safety(proc, self_pid=999, now=time.time())
            assert safety == "protected", f"Failed to protect {name}"

    def test_allows_safe_termination_of_stale_detached_worker(self):
        proc = ProcessRecord(
            pid=8888,
            ppid=1,
            name="python3",
            cmdline=("python3", "infinite_loop.py"),
            cpu_percent=98.5,
            memory_percent=28.0,
            create_time=time.time() - 1200,  # 20 min ago
            username="tom",
        )
        safety, reason = classify_process_safety(proc, self_pid=999, now=time.time())
        assert safety == "safe"
        assert "worker" in reason.lower()

    def test_marks_high_cpu_unknown_process_as_review(self):
        proc = ProcessRecord(
            pid=7777,
            ppid=1,
            name="blender_render",
            cmdline=("blender", "-b", "scene.blend"),
            cpu_percent=95.0,
            memory_percent=15.0,
            create_time=time.time() - 1200,
            username="tom",
        )
        safety, _reason = classify_process_safety(proc, self_pid=999, now=time.time())
        assert safety == "review"


class TestDashboardScanAndRender:
    def test_collect_dashboard_scan_returns_valid_data(self, monkeypatch):
        monkeypatch.setattr(
            "fixos.cli.dashboard.scan_dir_native",
            lambda path, min_bytes=0: [
                {"name": "pip", "path": str(Path(path) / "pip"), "bytes": 200 * 1024 * 1024}
            ],
        )
        monkeypatch.setattr(
            "fixos.cli.dashboard.measure_tree",
            lambda path, native=True: {"bytes": 60 * 1024 * 1024, "files": 12},
        )
        data = collect_dashboard_scan()
        assert isinstance(data, DashboardScanData)
        assert data.cpu_percent >= 0.0
        assert data.ram_percent >= 0.0
        assert data.disk_percent >= 0.0
        assert data.cpu_cores >= 1
        assert isinstance(data.storage_items, list)
        assert isinstance(data.heavy_processes, list)
        assert isinstance(data.warnings, list)

    def test_render_dashboard_prints_components(self):
        data = DashboardScanData(
            cpu_percent=45.2,
            cpu_cores=8,
            ram_percent=60.1,
            ram_used_gb=9.6,
            ram_total_gb=16.0,
            disk_percent=72.0,
            disk_used_gb=360.0,
            disk_total_gb=500.0,
            disk_free_gb=140.0,
            is_disk_critical=False,
            storage_items=[
                StorageItem(
                    name="~/.cache/pip",
                    path="/home/tom/.cache/pip",
                    size_mb=450.0,
                    risk="safe",
                    safe_to_cleanup=True,
                    description="pip cache",
                ),
                StorageItem(
                    name="~/.cache/custom",
                    path="/home/tom/.cache/custom",
                    size_mb=1200.0,
                    risk="review",
                    safe_to_cleanup=False,
                    description="custom cache",
                ),
            ],
            safe_reclaimable_gb=0.44,
            total_scanned_storage_gb=1.61,
            heavy_processes=[
                ProcessItem(
                    pid=12345,
                    name="python3",
                    username="tom",
                    cpu_percent=99.0,
                    memory_percent=5.0,
                    create_time=time.time() - 1500,
                    runtime_str="25m",
                    cmdline_str="python3 worker.py",
                    safety="safe",
                    reason="Zapętlony worker",
                )
            ],
            safe_terminable_pids=[12345],
            warnings=[],
        )
        console = Console(record=True, width=120)
        render_dashboard(data, console=console)
        out = console.export_text()
        assert "FixOS • Szybki Dashboard Diagnostyczny" in out
        assert "CPU" in out
        assert "Pamięć RAM" in out
        assert "Dysk (/)" in out
        assert "pip" in out
        assert "BEZPIECZNE ZAMKNIĘCIE" in out


class TestInterventions:
    def test_execute_safe_cache_cleanup_dry_run(self, tmp_path):
        cache_dir = tmp_path / "pip"
        cache_dir.mkdir()
        (cache_dir / "pkg.whl").write_bytes(b"x" * 1024)

        data = DashboardScanData(
            cpu_percent=10.0,
            cpu_cores=4,
            ram_percent=50.0,
            ram_used_gb=8.0,
            ram_total_gb=16.0,
            disk_percent=50.0,
            disk_used_gb=100.0,
            disk_total_gb=200.0,
            disk_free_gb=100.0,
            is_disk_critical=False,
            storage_items=[
                StorageItem(
                    name="test-pip",
                    path=str(cache_dir),
                    size_mb=1.0,
                    risk="safe",
                    safe_to_cleanup=True,
                    description="test cache",
                ),
                StorageItem(
                    name="protected-item",
                    path=str(tmp_path / "protected"),
                    size_mb=50.0,
                    risk="review",
                    safe_to_cleanup=False,
                    description="do not touch",
                ),
            ],
            safe_reclaimable_gb=0.001,
            total_scanned_storage_gb=0.05,
            heavy_processes=[],
            safe_terminable_pids=[],
            warnings=[],
        )

        count, mb = execute_safe_cache_cleanup(data, dry_run=True)
        assert count == 1
        assert mb == 1.0
        # Dry run must NOT delete files
        assert (cache_dir / "pkg.whl").exists()

    def test_execute_safe_cache_cleanup_live(self, tmp_path):
        cache_dir = tmp_path / "uv"
        cache_dir.mkdir()
        (cache_dir / "archive.tar").write_bytes(b"x" * 2048)

        data = DashboardScanData(
            cpu_percent=10.0,
            cpu_cores=4,
            ram_percent=50.0,
            ram_used_gb=8.0,
            ram_total_gb=16.0,
            disk_percent=50.0,
            disk_used_gb=100.0,
            disk_total_gb=200.0,
            disk_free_gb=100.0,
            is_disk_critical=False,
            storage_items=[
                StorageItem(
                    name="test-uv",
                    path=str(cache_dir),
                    size_mb=2.0,
                    risk="safe",
                    safe_to_cleanup=True,
                    description="test uv cache",
                )
            ],
            safe_reclaimable_gb=0.002,
            total_scanned_storage_gb=0.002,
            heavy_processes=[],
            safe_terminable_pids=[],
            warnings=[],
        )

        count, mb = execute_safe_cache_cleanup(data, dry_run=False)
        assert count == 1
        assert mb == 2.0
        # Dir exists (recreated empty) but file is gone
        assert cache_dir.exists()
        assert not (cache_dir / "archive.tar").exists()

    def test_execute_safe_process_termination_dry_run(self):
        data = DashboardScanData(
            cpu_percent=10.0,
            cpu_cores=4,
            ram_percent=50.0,
            ram_used_gb=8.0,
            ram_total_gb=16.0,
            disk_percent=50.0,
            disk_used_gb=100.0,
            disk_total_gb=200.0,
            disk_free_gb=100.0,
            is_disk_critical=False,
            storage_items=[],
            safe_reclaimable_gb=0.0,
            total_scanned_storage_gb=0.0,
            heavy_processes=[
                ProcessItem(
                    pid=99999,
                    name="python",
                    username="tom",
                    cpu_percent=95.0,
                    memory_percent=10.0,
                    create_time=time.time() - 1000,
                    runtime_str="16m",
                    cmdline_str="python worker.py",
                    safety="safe",
                    reason="Stale worker",
                ),
                ProcessItem(
                    pid=88888,
                    name="code",
                    username="tom",
                    cpu_percent=90.0,
                    memory_percent=20.0,
                    create_time=time.time() - 1000,
                    runtime_str="16m",
                    cmdline_str="code",
                    safety="protected",
                    reason="IDE",
                ),
            ],
            safe_terminable_pids=[99999],
            warnings=[],
        )

        terminated = execute_safe_process_termination(data, dry_run=True)
        assert terminated == [99999]


class TestDashboardCliCommand:
    def test_json_flag(self):
        runner = CliRunner()
        result = runner.invoke(dashboard_cmd, ["--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "cpu_percent" in parsed
        assert "ram_percent" in parsed
        assert "disk_percent" in parsed
        assert "storage_items" in parsed
        assert "heavy_processes" in parsed

    def test_auto_fix_dry_run(self):
        runner = CliRunner()
        result = runner.invoke(dashboard_cmd, ["--auto-fix", "--dry-run"])
        assert result.exit_code == 0
        assert "Interwencja zakończona" in result.output
