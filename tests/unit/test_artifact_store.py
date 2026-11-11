"""Tests for reference-aware artifact store reclamation."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fixos.diagnostics.artifact_store import (
    SYSTEM_TARGETS,
    collect_references,
    is_protected_path,
    remove_artifacts,
    scan_artifact_stores,
    scan_build_caches,
    scan_system_targets,
)

OLD = time.time() - 10 * 86400
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def _age(path: Path, when: float = OLD) -> None:
    for entry in [path, *path.rglob("*")]:
        try:
            os.utime(entry, (when, when))
        except OSError:
            continue


def _store(root: Path, digest: str, filename: str, payload: bytes = b"x") -> Path:
    entry = root / "sha256" / digest
    entry.mkdir(parents=True)
    (entry / filename).write_bytes(payload)
    _age(entry)
    return entry


def test_unreferenced_digest_is_eligible(tmp_path: Path) -> None:
    store = tmp_path / "inputs"
    entry = _store(store, DIGEST_A, "base.img", b"y" * 32)
    report = scan_artifact_stores([store], min_age_days=1)
    assert report["found"] == 1
    assert report["eligible"] == 1
    assert report["items"][0]["path"] == str(entry)
    assert report["items"][0]["bytes"] >= 32


def test_digest_named_in_manifest_is_protected(tmp_path: Path) -> None:
    store = tmp_path / "inputs"
    entry = _store(store, DIGEST_A, "payload.tar.gz")
    (tmp_path / "recipe.json").write_text(
        json.dumps({"payload": f"inputs/sha256/{DIGEST_A}/payload.tar.gz"})
    )
    report = scan_artifact_stores([store], min_age_days=1)
    item = report["items"][0]
    assert item["path"] == str(entry)
    assert item["eligible"] is False
    assert any(reason.startswith("referenced:digest-in-text:") for reason in item["reasons"])


def test_implicit_absolute_path_reference_is_protected(tmp_path: Path) -> None:
    """The regression that broke the PC build: guestfs.json names a kernel path."""

    store = tmp_path / "inputs"
    entry = _store(store, DIGEST_B, "builder-kernel", b"k" * 16)
    runtime = tmp_path / "inputs" / "runtime" / ("f" * 64)
    runtime.mkdir(parents=True)
    (runtime / "guestfs.json").write_text(
        json.dumps({"SUPERMIN_KERNEL": str(entry / "builder-kernel")})
    )
    report = scan_artifact_stores([store], min_age_days=1)
    item = report["items"][0]
    assert item["path"] == str(entry)
    assert item["eligible"] is False
    assert any(
        reason.startswith("referenced:absolute-path-in-text:") for reason in item["reasons"]
    )


def test_symlink_reference_is_protected(tmp_path: Path) -> None:
    store = tmp_path / "inputs"
    entry = _store(store, DIGEST_C, "modules.tar")
    link_dir = tmp_path / "links"
    link_dir.mkdir()
    (link_dir / "modules").symlink_to(entry / "modules.tar")
    references = collect_references(store, [(tmp_path, 4)])
    assert DIGEST_C in references
    assert any(item.startswith("symlink:") for item in references[DIGEST_C])


def test_recent_digest_is_protected(tmp_path: Path) -> None:
    store = tmp_path / "inputs"
    entry = store / "sha256" / DIGEST_A
    entry.mkdir(parents=True)
    (entry / "fresh.bin").write_bytes(b"z")
    report = scan_artifact_stores([store], min_age_days=1)
    item = report["items"][0]
    assert item["path"] == str(entry)
    assert item["eligible"] is False
    assert any(reason.startswith("too-recent:") for reason in item["reasons"])


def test_private_home_directories_are_never_candidates(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    downloads = home / "Downloads"
    store = downloads / "inputs"
    _store(store, DIGEST_A, "photo.zip")
    monkeypatch.setenv("HOME", str(home))
    reasons = is_protected_path(store / "sha256" / DIGEST_A, home=home)
    assert any(reason.startswith("private-home-data:") for reason in reasons)
    report = scan_artifact_stores([store], min_age_days=1)
    assert report["eligible"] == 0
    assert any(
        reason.startswith("private-home-data:") for reason in report["items"][0]["reasons"]
    )


def test_credential_store_is_never_a_candidate(tmp_path: Path) -> None:
    store = tmp_path / ".gnupg" / "inputs"
    _store(store, DIGEST_A, "keyring.bin")
    report = scan_artifact_stores([store], min_age_days=1)
    assert report["eligible"] == 0
    assert any(
        reason.startswith("credential-store:") for reason in report["items"][0]["reasons"]
    )


def test_remove_artifacts_deletes_only_eligible_and_writes_receipt(tmp_path: Path) -> None:
    store = tmp_path / "inputs"
    gone = _store(store, DIGEST_A, "old.img")
    kept = _store(store, DIGEST_B, "used.img")
    (tmp_path / "manifest.json").write_text(f"sha256/{DIGEST_B}")
    report = scan_artifact_stores([store], min_age_days=1)
    eligible = [item for item in report["items"] if item["eligible"]]
    assert [item["path"] for item in eligible] == [str(gone)]
    receipt_dir = tmp_path / "receipts"
    result = remove_artifacts(report["items"], receipt_dir=receipt_dir)
    assert [item["path"] for item in result["removed"]] == [str(gone)]
    assert not gone.exists()
    assert kept.exists()
    assert result["freed_bytes"] > 0
    assert Path(result["receipt"]).is_file()


def test_build_caches_respect_age_and_git_tracking(tmp_path: Path) -> None:
    project = tmp_path / "project"
    cache = project / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "module.pyc").write_bytes(b"p")
    fresh = project / "dist"
    fresh.mkdir()
    (fresh / "wheel.whl").write_bytes(b"w")
    _age(cache)
    report = scan_build_caches([tmp_path], min_age_days=1)
    kinds = {Path(item["path"]).name: item for item in report["items"]}
    assert kinds["__pycache__"]["eligible"] is True
    assert kinds["dist"]["eligible"] is False
    assert any(reason.startswith("too-recent:") for reason in kinds["dist"]["reasons"])


def test_system_targets_reclaim_user_cache_but_not_downloads(tmp_path: Path) -> None:
    home = tmp_path / "home"
    pip_cache = home / ".cache" / "pip"
    pip_cache.mkdir(parents=True)
    (pip_cache / "wheel.whl").write_bytes(b"x" * 24)
    _age(pip_cache)
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "invoice.zip").write_bytes(b"z" * 24)
    _age(downloads)
    targets = [t for t in SYSTEM_TARGETS if t["name"] in {"pip-cache", "trash"}]
    report = scan_system_targets(
        home=home,
        min_age_days=1,
        targets=targets,
        overrides={"pip-cache": pip_cache, "trash": downloads},
    )
    by_name = {item["target"]: item for item in report["items"]}
    assert by_name["pip-cache"]["eligible"] is True
    assert by_name["trash"]["eligible"] is False
    assert any(
        reason.startswith("private-home-data:")
        for reason in by_name["trash"]["reasons"]
    )
    assert report["eligible"] == 1


def test_system_targets_skip_fresh_and_mount_points(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "fresh.bin").write_bytes(b"f")
    targets = [{"name": "uv-cache", "path": str(cache), "pattern": None, "kind": "user-cache"}]
    report = scan_system_targets(home=tmp_path, min_age_days=1, targets=targets)
    item = report["items"][0]
    assert item["eligible"] is False
    assert any(reason.startswith("too-recent:") for reason in item["reasons"])
    report = scan_system_targets(home=tmp_path, min_age_days=0, targets=targets)
    assert report["items"][0]["eligible"] is True


def test_system_targets_rotated_logs_pattern(tmp_path: Path) -> None:
    logs = tmp_path / "log"
    logs.mkdir()
    rotated = logs / "syslog.1.gz"
    rotated.write_bytes(b"r")
    active = logs / "syslog"
    active.write_bytes(b"a")
    _age(logs)
    targets = [{"name": "rotated-logs", "path": str(logs), "pattern": "rotated", "kind": "logs"}]
    report = scan_system_targets(home=tmp_path, min_age_days=1, targets=targets)
    paths = [Path(item["path"]).name for item in report["items"]]
    assert paths == ["syslog.1.gz"]
