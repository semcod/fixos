"""Regression tests for autonomous Docker & /tmp remediation in fixos auto (ticket-176)."""

from __future__ import annotations

import os
import time
from types import SimpleNamespace

import pytest

from fixos.cli import _auto_cleanup as auto
from fixos.cli import _cleanup_free_target as free_target
from fixos.cli import _cleanup_space as space


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("onedev-docs157-unpinned-counterexample:new", True),
        ("onedev-docs157-unpinned-counterexample:old", True),
        ("onedev-progress-staged:d0fd86b-full-gkqhtd", True),
        ("subactor-planfile:qualify-352-5b89992e4fd8", True),
        ("local/planfile-api-rust:qualified-58d6f881459d", True),
        ("subactor-autonomy-protobuf-native:qualification-20261118", True),
        ("local-forge-qualification:0e4dc94b-20261117t1254", True),
        (
            "maskservice-maskauth-cache:continue-20261116-1945-python-3-12-d006270de45d",
            True,
        ),
        # Protected tags must always be rejected
        ("onedev-docs157-approved:20bfcff1", False),
        ("forge-native-isolated:approved-v2", False),
        ("subactor-autonomy-sandbox:0.1.0", False),
        ("onedev-willops-parent:sha256-d32d4a1ca59d", False),
        ("onedev-docs157-base-private:72056962fc7b7a9b", False),
        ("postgres:16-alpine", False),
        ("maskservice-fleet-local-dashboard:latest", False),
        ("subactor-planfile:pr348-runtime-candidate-20261117", False),
        ("<none>:<none>", False),
        ("", False),
    ],
)
def test_is_ephemeral_docker_image_tag(ref: str, expected: bool) -> None:
    assert auto.is_ephemeral_docker_image_tag(ref) is expected


def test_cleanup_ephemeral_docker_images_skips_in_use_and_protected(monkeypatch) -> None:
    monkeypatch.setattr(auto.shutil, "which", lambda _: "/usr/bin/docker")
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))
        if cmd[:2] == ["docker", "ps"]:
            return SimpleNamespace(
                returncode=0, stdout="inuse-app:latest\nsha256:aaa111222333444\n"
            )
        if cmd[:3] == ["docker", "image", "inspect"]:
            return SimpleNamespace(returncode=0, stdout="sha256:bbb111222333444\n")
        if cmd[:2] == ["docker", "images"]:
            rows = [
                "sha256:aaa111222333444\tondev-progress-staged:in-use-by-id",
                "sha256:bbb111222333444\tondev-progress-staged:in-use-by-inspected-tag",
                "sha256:ccc111222333444\tonedev-docs157-unpinned-counterexample:new",
                "sha256:ddd111222333444\tonedev-docs157-approved:20bfcff1",
                "sha256:eee111222333444\tsubactor-planfile:qualify-352-5b89992e",
                "sha256:fff111222333444\tpostgres:16-alpine",
            ]
            return SimpleNamespace(returncode=0, stdout="\n".join(rows))
        if cmd[:2] == ["docker", "rmi"]:
            return SimpleNamespace(returncode=0, stdout="Untagged\n")
        raise AssertionError(f"Unexpected docker command: {cmd}")

    monkeypatch.setattr(auto.subprocess, "run", fake_run)
    removed = auto.cleanup_ephemeral_docker_images(dry_run=False, yes=True)
    assert removed == [
        "onedev-docs157-unpinned-counterexample:new",
        "subactor-planfile:qualify-352-5b89992e",
    ]
    rmi_calls = [c for c in calls if c[:2] == ["docker", "rmi"]]
    assert rmi_calls == [
        [
            "docker",
            "rmi",
            "onedev-docs157-unpinned-counterexample:new",
            "subactor-planfile:qualify-352-5b89992e",
        ]
    ]


def test_cleanup_ephemeral_docker_images_fails_closed_when_inspect_fails(
    monkeypatch,
) -> None:
    monkeypatch.setattr(auto.shutil, "which", lambda _: "/usr/bin/docker")
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))
        if cmd[:2] == ["docker", "ps"]:
            return SimpleNamespace(returncode=0, stdout="running-service:latest\n")
        if cmd[:3] == ["docker", "image", "inspect"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="daemon busy")
        raise AssertionError(f"Should have aborted before: {cmd}")

    monkeypatch.setattr(auto.subprocess, "run", fake_run)
    assert auto.cleanup_ephemeral_docker_images(dry_run=False, yes=True) == []
    assert not any(c[:2] == ["docker", "rmi"] for c in calls)


def test_cleanup_docker_builder_runs_dangling_and_retained_prunes(monkeypatch) -> None:
    monkeypatch.setattr(auto.shutil, "which", lambda _: "/usr/bin/docker")
    seen: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        seen.append(list(cmd))
        return SimpleNamespace(returncode=0, stdout="Total reclaimed space: 1GB\n")

    monkeypatch.setattr(auto.subprocess, "run", fake_run)
    auto.cleanup_docker_builder(dry_run=False, yes=True)
    assert ["docker", "image", "prune", "--force"] in seen
    assert ["docker", "builder", "prune", "--force"] in seen
    assert seen[-1] == [
        "docker",
        "builder",
        "prune",
        "--all",
        "--force",
        "--filter",
        "until=168h",
    ]


def test_additional_cache_paths_include_uv_and_pip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(auto.Path, "home", lambda: tmp_path)
    uv_file = tmp_path / ".cache" / "uv" / "archive" / "pkg.whl"
    uv_file.parent.mkdir(parents=True)
    uv_file.write_text("wheel")
    pip_file = tmp_path / ".cache" / "pip" / "http" / "entry"
    pip_file.parent.mkdir(parents=True)
    pip_file.write_text("entry")

    auto.cleanup_additional_caches(dry_run=False, yes=True)
    assert not (tmp_path / ".cache" / "uv").exists()
    assert not (tmp_path / ".cache" / "pip").exists()


def test_scan_tmp_reclaims_stale_ephemeral_test_dirs_after_2h(tmp_path) -> None:
    now = time.time()
    three_hours_ago = now - 3 * 3600
    thirty_min_ago = now - 1800

    stale_pytest = tmp_path / "pytest-of-tester"
    stale_pytest.mkdir()
    (stale_pytest / "data.bin").write_bytes(b"x" * 1024)
    os.utime(stale_pytest, (three_hours_ago, three_hours_ago))

    fresh_pytest = tmp_path / "heyasa-pytest-active"
    fresh_pytest.mkdir()
    os.utime(fresh_pytest, (thirty_min_ago, thirty_min_ago))

    regular_recent = tmp_path / "user-work-dir"
    regular_recent.mkdir()
    os.utime(regular_recent, (three_hours_ago, three_hours_ago))

    link_target = tmp_path / "keep-target"
    link_target.mkdir()
    stale_link = tmp_path / "oqllm-symlink"
    stale_link.symlink_to(link_target, target_is_directory=True)

    candidates = space._scan_tmp(days=1.0, tmp_dir=tmp_path)
    names = {c["name"] for c in candidates}
    assert "pytest-of-tester" in names
    assert "heyasa-pytest-active" not in names
    assert "user-work-dir" not in names
    assert "oqllm-symlink" not in names


def test_free_target_docker_remove_ephemeral_unused_images(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_docker_call(args, timeout=30):
        calls.append(list(args))
        if args[:2] == ["ps", "-a"]:
            return True, "app:latest\n"
        if args[:2] == ["image", "inspect"]:
            return True, "sha256:1111222233334444\n"
        if args[:1] == ["images"]:
            listing = (
                "sha256:1111222233334444\tapp:latest\n"
                "sha256:9999888877776666\tonedev-progress-staged:abc123\n"
                "sha256:5555666677778888\tforge-native-isolated:approved-v2\n"
            )
            return True, listing
        if args[:1] == ["rmi"]:
            return True, "Untagged"
        raise AssertionError(f"Unexpected docker_call: {args}")

    monkeypatch.setattr(free_target, "docker_call", fake_docker_call)
    res = free_target.docker_remove_ephemeral_unused_images()
    assert res.attempted is True
    assert ["rmi", "onedev-progress-staged:abc123"] in calls
