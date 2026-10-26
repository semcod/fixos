"""Safety and reporting regressions for expanded autonomous cleanup."""

import inspect
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from fixos.cli import _auto_cleanup as auto
from fixos.cli import _cleanup_space as space
from fixos.cli.main import cli


def _cli_runner() -> CliRunner:
    if "mix_stderr" in inspect.signature(CliRunner.__init__).parameters:
        return CliRunner(mix_stderr=False)
    return CliRunner()


def put(home, relative, content="cached"):
    path = home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_cleanup_keeps_downloads_profiles_models_and_unknown_cache(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    caches = [
        put(tmp_path, p)
        for p in (
            ".npm/_npx/pkg/cache",
            ".cache/pypoetry/artifacts/pkg.whl",
            ".cache/google-chrome/Default/Cache/data",
            ".cargo/registry/cache/repo/a.crate",
            ".cache/go-build/leaf/cache",
            ".cache/ruff/leaf/cache",
            ".cache/mypy/leaf/cache",
            ".cache/Flake8/leaf/cache",
            ".cache/black/leaf/cache",
        )
    ]
    protected = [
        put(tmp_path, p)
        for p in (
            "Downloads/important.zip",
            "Documents/notes.txt",
            ".cache/unknown/state.db",
            ".config/google-chrome/Default/Bookmarks",
            ".cache/google-chrome/Default/Cookies",
            ".cache/huggingface/hub/model",
            ".cache/ms-playwright/browser",
            ".local/share/JetBrains/LocalHistory/changes",
            ".cargo/registry/src/pkg/src.rs",
        )
    ]
    auto.cleanup_additional_caches(dry_run=False, yes=True)
    assert all(not p.exists() for p in caches)
    assert all(p.read_text() == "cached" for p in protected)


def test_dry_run_preserves_candidates(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = put(tmp_path, ".npm/_npx/pkg/index.js")
    auto.cleanup_additional_caches(dry_run=True, yes=True)
    assert path.exists()
    assert "DRY-RUN" in capsys.readouterr().out


@pytest.mark.parametrize("ancestor", [".cache", ".npm", ".cargo"])
def test_symlinked_cache_ancestor_cannot_reach_downloads(
    tmp_path, monkeypatch, ancestor
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    files = [
        put(tmp_path, f"Downloads/{p}")
        for p in (
            "_npx/user-data",
            "registry/cache/user-data",
            "pypoetry/artifacts/user-data",
            "pip/user-data",
            "google-chrome/Default/Cache/user-data",
        )
    ]
    (tmp_path / ancestor).symlink_to(tmp_path / "Downloads", target_is_directory=True)
    auto.cleanup_additional_caches(dry_run=False, yes=True)
    space._cleanup_user_cache(False, False, False, True)
    assert all(p.exists() for p in files)


def test_nested_mount_protects_cache(tmp_path, monkeypatch):
    path = put(tmp_path, ".npm/_npx/mounted/data")
    original = Path.is_mount
    monkeypatch.setattr(Path, "is_mount", lambda p: p.name == "mounted" or original(p))
    assert not auto.cache_path_allowed(tmp_path, path.parents[1])


def test_internal_symlink_is_unlinked_without_following(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    original = put(tmp_path, "Downloads/file")
    cache = tmp_path / ".npm/_npx"
    cache.mkdir(parents=True)
    (cache / "link").symlink_to(original)
    auto.cleanup_additional_caches(dry_run=False, yes=True)
    assert original.exists()
    assert not cache.exists()


def test_candidate_replaced_with_symlink_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    protected = put(tmp_path, "Downloads/file")
    cache = tmp_path / ".npm/_npx"
    cache.parent.mkdir()
    cache.symlink_to(protected.parent, target_is_directory=True)
    monkeypatch.setattr(
        auto,
        "additional_cache_candidates",
        lambda home: [{"path": cache, "size_bytes": 1, "description": "cache"}],
    )
    auto.cleanup_additional_caches(dry_run=False, yes=True)
    assert protected.exists()


@pytest.mark.parametrize("dry_run", [True, False])
def test_docker_prunes_only_retained_build_cache(monkeypatch, dry_run):
    monkeypatch.setattr(auto.shutil, "which", lambda _: "/usr/bin/docker")
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout="done"))
    monkeypatch.setattr(auto.subprocess, "run", run)
    auto.cleanup_docker_builder(dry_run=dry_run, yes=True)
    if dry_run:
        run.assert_not_called()
    else:
        assert run.call_args.args[0] == [
            "docker",
            "builder",
            "prune",
            "--all",
            "--force",
            "--filter",
            "until=168h",
        ]
        assert run.call_args.kwargs["timeout"] == 30


def test_docker_timeout_does_not_stop_cleanup(monkeypatch, capsys):
    monkeypatch.setattr(auto.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(
        auto.subprocess,
        "run",
        Mock(side_effect=subprocess.TimeoutExpired("docker", 30)),
    )
    auto.cleanup_docker_builder(dry_run=False, yes=True)
    assert "timeout" in capsys.readouterr().out


@pytest.fixture
def auto_cli(monkeypatch):
    monkeypatch.setattr(
        "fixos.config.FixOsConfig.load", lambda **k: SimpleNamespace(api_key="")
    )
    monkeypatch.setattr("fixos.diagnostics.quick_snapshot.collect_quick_snapshot", dict)
    monkeypatch.setattr(
        "fixos.cli.fix_cmd.run_autonomous_session",
        lambda **k: SimpleNamespace(fixes_applied=[], problems_found=[]),
    )
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
    extra = Mock(side_effect=lambda **k: print("cache progress", flush=True))
    docker = Mock(side_effect=lambda **k: print("docker progress", flush=True))
    monkeypatch.setattr(auto, "cleanup_additional_caches", extra)
    monkeypatch.setattr(auto, "cleanup_docker_builder", docker)
    return extra, docker


def test_root_accounting_excludes_tmp_and_reports_remaining_pressure(
    auto_cli, monkeypatch
):
    import shutil

    usage = iter(
        [
            SimpleNamespace(total=1000 * 1024**3, free=1024**3),
            SimpleNamespace(total=32 * 1024**3, free=1024**3),
            SimpleNamespace(total=1000 * 1024**3, free=2 * 1024**3),
            SimpleNamespace(total=32 * 1024**3, free=6 * 1024**3),
        ]
    )
    monkeypatch.setattr(shutil, "disk_usage", lambda _: next(usage))
    original = Path.is_dir
    monkeypatch.setattr(
        Path, "is_dir", lambda p: True if str(p) == "/tmp" else original(p)
    )
    # Simulate separate /tmp without changing stat globally (pytest uses it).
    import os

    stat_original = os.stat

    def stat(path, *args, **kwargs):
        if path == "/" or path == "/tmp":
            return SimpleNamespace(st_dev=1 if path == "/" else 2)
        return stat_original(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", stat)
    result = _cli_runner().invoke(cli, ["auto", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["disk_freed_bytes"] == 1024**3
    assert payload["tmp_freed_bytes"] == 5 * 1024**3
    assert payload["status"] == "disk_pressure_remaining"
    assert not payload["goal_reached"]
    assert "cache progress" in result.stderr
    assert "trash" not in payload["steps_executed"]


def test_auto_opt_outs_skip_new_cleanup(auto_cli):
    result = CliRunner().invoke(
        cli, ["auto", "--json", "--no-user-cache", "--no-docker-build-cache"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)
    for action in auto_cli:
        action.assert_not_called()


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "0"])
def test_invalid_goal_rejected_before_cleanup(auto_cli, value):
    result = CliRunner().invoke(cli, ["auto", "--free-gb", value])
    assert result.exit_code == 2
    for action in auto_cli:
        action.assert_not_called()


@pytest.mark.parametrize("dry_run", [False, True])
def test_interactive_cache_skips_nested_mounts(tmp_path, monkeypatch, capsys, dry_run):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    protected = put(tmp_path, ".cache/pip/mounted/document.txt")
    original = Path.is_mount
    monkeypatch.setattr(Path, "is_mount", lambda p: p.name == "mounted" or original(p))
    monkeypatch.setattr(space, "_choose", lambda *a: [0])
    monkeypatch.setattr(space, "_confirm_remove", lambda: True)
    space._cleanup_user_cache(False, dry_run, False, False)
    assert protected.exists()
    output = capsys.readouterr().out
    assert "rm -rf" not in output
    assert "pominięto" in output.lower()


@pytest.mark.parametrize("replacement", ["symlink", "mount"])
def test_interactive_cache_rechecks_after_confirmation(
    tmp_path, monkeypatch, replacement
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cache_file = put(tmp_path, ".cache/pip/cache")
    protected = put(tmp_path, "Downloads/document.txt")
    monkeypatch.setattr(space, "_choose", lambda *a: [0])

    def confirm():
        if replacement == "symlink":
            cache_file.unlink()
            cache_file.parent.rmdir()
            cache_file.parent.symlink_to(protected.parent, target_is_directory=True)
        else:
            original = Path.is_mount
            monkeypatch.setattr(
                Path, "is_mount", lambda p: p == cache_file.parent or original(p)
            )
        return True

    monkeypatch.setattr(space, "_confirm_remove", confirm)
    remove = Mock()
    monkeypatch.setattr(space, "_remove_selected", remove)
    space._cleanup_user_cache(False, False, False, False)
    remove.assert_not_called()
    assert protected.exists()


def test_interactive_cache_still_removes_selected_regular_unknown_cache(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cache_file = put(tmp_path, ".cache/custom-tool/cache")
    protected = put(tmp_path, "Downloads/document.txt")
    monkeypatch.setattr(space, "_choose", lambda *a: [0])
    monkeypatch.setattr(space, "_confirm_remove", lambda: True)
    space._cleanup_user_cache(False, False, False, False)
    assert not cache_file.exists()
    assert protected.exists()


def test_auto_executes_7d_state_and_projects_cleanup_by_default(auto_cli):
    result = _cli_runner().invoke(cli, ["auto", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert "state-old" in payload["steps_executed"]
    assert "projects-old" in payload["steps_executed"]
    space._cleanup_build_caches.assert_called_once()
    kwargs = space._cleanup_build_caches.call_args.kwargs
    assert kwargs["clean_state_old"] is True
    assert kwargs["clean_projects_old"] is True
    assert kwargs["stale_days"] == 7


def test_auto_respects_no_state_old_and_no_projects_old(auto_cli):
    result = _cli_runner().invoke(
        cli, ["auto", "--json", "--no-state-old", "--no-projects-old"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert "state-old" not in payload["steps_executed"]
    assert "projects-old" not in payload["steps_executed"]


def test_cleanup_removes_developer_caches_and_preserves_models_and_browser_data(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    caches = [
        put(tmp_path, p)
        for p in (
            ".cache/go-build/leaf/cache",
            ".cache/ruff/leaf/cache",
            ".cache/mypy/leaf/cache",
            ".cache/Flake8/leaf/cache",
            ".cache/black/leaf/cache",
        )
    ]
    protected = [
        put(tmp_path, p)
        for p in (
            ".cache/huggingface/hub/models--bert-base-uncased/model.safetensors",
            ".cache/google-chrome/Default/History",
            ".cache/google-chrome/Default/Cookies",
            ".config/google-chrome/Default/Bookmarks",
            ".cache/unknown_tool/cache",
        )
    ]
    auto.cleanup_additional_caches(dry_run=False, yes=True)
    assert all(not p.exists() for p in caches)
    assert all(p.exists() for p in protected)


def test_additional_cache_candidates_includes_developer_caches(tmp_path):
    for p in (
        ".cache/go-build/data",
        ".cache/ruff/data",
        ".cache/mypy/data",
        ".cache/Flake8/data",
        ".cache/black/data",
    ):
        put(tmp_path, p, "data")
    candidates = auto.additional_cache_candidates(tmp_path)
    descriptions = {c["description"] for c in candidates}
    assert "~/.cache/go-build" in descriptions
    assert "~/.cache/ruff" in descriptions
    assert "~/.cache/mypy" in descriptions
    assert "~/.cache/Flake8" in descriptions
    assert "~/.cache/black" in descriptions


def test_quick_snapshot_reflects_go_and_python_caches_in_safe_reclaim(
    tmp_path, monkeypatch
):
    from datetime import datetime, timezone

    from fixos.diagnostics import quick_snapshot as qs

    put(tmp_path, ".cache/go-build/sample.bin", "x" * 2048)
    put(tmp_path, ".cache/ruff/sample.bin", "y" * 4096)
    put(tmp_path, ".cache/mypy/sample.bin", "z" * 1024)

    monkeypatch.setattr(
        qs,
        "_resource_snapshot",
        lambda: {
            "cpu": {
                "percent": 10,
                "logical_cpus": 4,
                "load": [0.1, 0.1, 0.1],
                "load_1_normalized_percent": 2,
            },
            "memory": {
                "total_bytes": 1000,
                "used_bytes": 300,
                "available_bytes": 700,
                "percent": 30,
            },
            "swap": {"total_bytes": 1000, "used_bytes": 0, "percent": 0},
            "disk": {
                "mount": "/",
                "total_bytes": 10 * 1024**3,
                "used_bytes": 1024**3,
                "free_bytes": 9 * 1024**3,
                "percent": 10,
            },
            "top_processes": [],
        },
    )
    monkeypatch.setattr(qs, "_cached_docker_review", lambda now, **_: None)

    snapshot = qs.collect_quick_snapshot(
        state_dir=tmp_path,
        home=tmp_path,
        cwd=tmp_path,
        save=False,
        now=datetime.now(timezone.utc),
    )

    safe_items = snapshot["safe_reclaim"]["items"]
    item_ids = {item["id"] for item in safe_items}
    assert "go-build" in item_ids
    assert "python-linters" in item_ids
    assert snapshot["safe_reclaim"]["estimated_max_bytes"] > 0



