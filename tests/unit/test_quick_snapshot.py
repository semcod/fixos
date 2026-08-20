from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fixos.diagnostics import quick_snapshot


def _resources(*, disk_used=500, memory_used=300, cpu=10):
    return {
        "cpu": {
            "percent": cpu,
            "logical_cpus": 4,
            "load": [0.2, 0.2, 0.2],
            "load_1_normalized_percent": 5,
        },
        "memory": {
            "total_bytes": 1000,
            "used_bytes": memory_used,
            "available_bytes": 1000 - memory_used,
            "percent": memory_used / 10,
        },
        "swap": {"total_bytes": 1000, "used_bytes": 100, "percent": 10},
        "disk": {
            "mount": "/",
            "total_bytes": 10 * 1024**3,
            "used_bytes": disk_used,
            "free_bytes": 10 * 1024**3 - disk_used,
            "percent": 50,
        },
        "top_processes": [],
    }


def _cache_item(size):
    return {
        "id": "pip",
        "label": "pip cache",
        "size_bytes": size,
        "size_gb": size / 1024**3,
        "paths": ["/tmp/home/.cache/pip"],
        "command": "python -m pip cache purge",
        "risk": "safe",
        "complete": True,
    }


def test_first_snapshot_creates_baseline_then_reports_growth(monkeypatch, tmp_path):
    first_resources = _resources(disk_used=4 * 1024**3, memory_used=300)
    second_resources = _resources(
        disk_used=6 * 1024**3,
        memory_used=500,
    )
    resources = iter((first_resources, second_resources))
    caches = iter(
        (
            ([_cache_item(1 * 1024**3)], [], True),
            ([_cache_item(2 * 1024**3)], [], True),
        )
    )
    monkeypatch.setattr(quick_snapshot, "_resource_snapshot", lambda: next(resources))
    monkeypatch.setattr(
        quick_snapshot,
        "_measure_caches",
        lambda home, timeout: next(caches),
    )
    monkeypatch.setattr(quick_snapshot, "_cached_docker_review", lambda now: None)
    monkeypatch.setattr(
        quick_snapshot,
        "_detect_context",
        lambda cwd: {
            "os": "Linux",
            "distribution": "Test Linux",
            "profile": "developer",
            "tech_stack": ["python"],
        },
    )

    started = datetime(2026, 7, 23, 8, tzinfo=timezone.utc)
    first = quick_snapshot.collect_quick_snapshot(
        state_dir=tmp_path,
        home=tmp_path,
        cwd=tmp_path,
        now=started,
    )
    second = quick_snapshot.collect_quick_snapshot(
        state_dir=tmp_path,
        home=tmp_path,
        cwd=tmp_path,
        now=started + timedelta(hours=1),
    )

    assert first["growth"]["status"] == "baseline_created"
    assert second["growth"]["status"] == "compared"
    assert second["growth"]["disk_delta_bytes"] == 2 * 1024**3
    assert second["growth"]["cache_growth"] == [{"id": "pip", "delta_bytes": 1024**3}]
    assert second["growth"]["today"]["disk_delta_bytes"] == 2 * 1024**3
    assert second["growth"]["escalating"][0]["resource"] == "disk"
    assert (tmp_path / "quick-history.json").exists()


def test_no_save_does_not_create_history(monkeypatch, tmp_path):
    monkeypatch.setattr(
        quick_snapshot, "_resource_snapshot", lambda: deepcopy(_resources())
    )
    monkeypatch.setattr(
        quick_snapshot, "_measure_caches", lambda home, timeout: ([], [], True)
    )
    monkeypatch.setattr(quick_snapshot, "_cached_docker_review", lambda now: None)
    monkeypatch.setattr(quick_snapshot, "_detect_context", lambda cwd: {})

    result = quick_snapshot.collect_quick_snapshot(
        state_dir=tmp_path,
        home=tmp_path,
        cwd=tmp_path,
        save=False,
    )

    assert result["growth"]["status"] == "baseline_created"
    assert not (tmp_path / "quick-history.json").exists()


def test_safe_cache_rules_never_scan_broad_or_user_data_paths():
    all_paths = {
        path
        for rule in quick_snapshot.CACHE_RULES
        if rule.risk == "safe"
        for path in rule.paths
    }

    assert "/" not in all_paths
    assert "~" not in all_paths
    assert not any("models" in path.lower() for path in all_paths)
    assert not any("extensions" in path.lower() for path in all_paths)
    assert not any("Trash" in path for path in all_paths)


def test_compiler_cache_rule_covers_ccache_and_sccache():
    rule = next(rule for rule in quick_snapshot.CACHE_RULES if rule.id == "ccache")

    assert "ccache --clear" in rule.command
    assert "~/.cache/sccache/*" in rule.command


def test_fresh_cached_docker_data_is_review_only(monkeypatch, tmp_path):
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_root))
    path = cache_root / "fixos" / "docker-usage.json"
    path.parent.mkdir(parents=True)
    now = datetime.now().astimezone()
    path.write_text(
        (
            '{"generated_at":"' + now.isoformat() + '","usage":{"rows":{"Build Cache":'
            '{"reclaimable_mb":2048}}}}'
        ),
        encoding="utf-8",
    )

    item = quick_snapshot._cached_docker_review(now)

    assert item is not None
    assert item["risk"] == "review"
    assert item["size_gb"] == 2


def test_developer_profile_uses_its_disk_threshold():
    resources = _resources()
    resources["disk"]["percent"] = 80
    thresholds = quick_snapshot._profile_thresholds("developer")

    alerts = quick_snapshot._alerts(
        resources,
        {"escalating": []},
        thresholds,
    )

    assert thresholds["disk_usage_warning"] == 75
    assert alerts[0]["resource"] == "disk"


def test_process_load_is_sampled_and_ranked_by_cpu_or_memory(monkeypatch):
    class FakeProcess:
        def __init__(self, pid, name, memory_percent, sampled_cpu):
            self.info = {
                "pid": pid,
                "name": name,
                "memory_percent": memory_percent,
            }
            self.sampled_cpu = sampled_cpu
            self.calls = 0

        def cpu_percent(self, interval=None):
            self.calls += 1
            return 0 if self.calls == 1 else self.sampled_cpu

    memory_hog = FakeProcess(101, "memory-hog", 30, 0)
    cpu_hog = FakeProcess(202, "cpu-hog", 20, 400)
    idle = FakeProcess(303, "idle", 1, 0)
    processes = [memory_hog, cpu_hog, idle]
    monkeypatch.setattr(quick_snapshot.psutil, "process_iter", lambda attrs: processes)
    monkeypatch.setattr(quick_snapshot.psutil, "cpu_percent", lambda interval: 42.5)

    system_cpu, top = quick_snapshot._sample_process_load(8, interval=0)

    assert system_cpu == 42.5
    assert [item["pid"] for item in top] == [202, 101, 303]
    assert top[0]["cpu_percent"] == 400
    assert all(process.calls == 2 for process in processes)
