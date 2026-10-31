"""Disk severity must reflect capacity available to ordinary processes."""

from types import SimpleNamespace

import pytest

from fixos.diagnostics.disk_analyzer import DiskAnalyzer

GIB = 1024**3


@pytest.fixture
def analyzer(tmp_path, monkeypatch):
    instance = DiskAnalyzer(str(tmp_path))
    for method in (
        "get_large_files",
        "get_cache_dirs",
        "get_log_dirs",
        "get_temp_dirs",
        "suggest_cleanup_actions",
    ):
        monkeypatch.setattr(instance, method, lambda *args, **kwargs: [])
    return instance


@pytest.mark.parametrize(
    ("used", "available", "expected_percent", "expected_status"),
    [
        (90, 1, 98.90, "critical"),
        (94, 2, 97.92, "critical"),
        (90, 0, 100.0, "critical"),
        (0, 0, 100.0, "critical"),
        (90, 10, 90.0, "warning"),
        (50, 50, 50.0, "healthy"),
        (0, 100, 0.0, "healthy"),
    ],
)
def test_capacity_available_to_processes_controls_severity(
    analyzer, monkeypatch, used, available, expected_percent, expected_status
):
    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda path: SimpleNamespace(
            total=100 * GIB, used=used * GIB, free=available * GIB
        ),
    )

    report = analyzer.analyze_disk_usage()

    assert report["status"] == expected_status
    assert report["usage_percent"] == expected_percent
    assert report["total_gb"] == 100
    assert report["used_gb"] == used
    assert report["free_gb"] == available


def test_zero_capacity_is_reported_as_an_error(analyzer, monkeypatch):
    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda path: SimpleNamespace(total=0, used=0, free=0),
    )

    report = analyzer.analyze_disk_usage()

    assert "error" in report
    assert "status" not in report
