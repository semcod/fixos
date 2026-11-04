"""Behavioral regressions for evidence-based, read-only disk triage."""

import errno
import os
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from fixos.diagnostics import large_files
from fixos.diagnostics.large_files import analyze_large_files
from fixos.diagnostics.storage_rules import decide_file, file_kind

OPEN_PROBE = large_files._open_evidence


def make_file(path, size, header=b"data"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as output:
        output.write(header)
        output.truncate(size)
    return path


def empty_processes(*args, **kwargs):
    return {
        "status": "partial",
        "opened": {},
        "examined": 0,
        "errors": 1,
        "open_deleted_allocated_bytes": 0,
        "open_deleted_files": 0,
    }


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    "alias_name,decision,rule",
    [
        ("backups/copy.bin", "protected", "BACKUP"),
        (".git/objects/copy.bin", "protected", "RECOVERY_OR_SOURCE"),
        ("data/copy.sqlite", "protected", "DATABASE"),
        ("docker/copy.bin", "manager-review", "CONTAINER_STORE"),
    ],
)
def test_alias_context_cannot_be_masked_by_cache_path(
    tmp_path, monkeypatch, reverse, alias_name, decision, rule
):
    # Wellman may put pytest's temp tree beneath .subactor/.worktrees.
    # Isolate the fixture's own path context from its host ancestors.
    monkeypatch.setattr(
        large_files,
        "decide_file",
        lambda row: decide_file(
            {
                **row,
                "path": str(Path("/fixture") / Path(row["path"]).relative_to(tmp_path)),
            }
        ),
    )
    cache = make_file(tmp_path / ".cache/candidate.bin", 1024)
    alias = tmp_path / alias_name
    alias.parent.mkdir(parents=True, exist_ok=True)
    os.link(cache, alias)
    roots = [cache.parent, alias.parent]
    if reverse:
        roots.reverse()
    report = analyze_large_files(roots, min_bytes=0)
    assert len(report["files"]) == 1
    row = report["files"][0]
    assert row["decision"] == decision
    assert row["rule_id"] == rule
    assert row["decision_path"] == str(alias)
    assert set(row["observed_paths"]) == {str(cache), str(alias)}
    assert row["observed_paths_may_be_incomplete"] is False
    assert row["reclaim_upper_bound_bytes"] == 0
    assert (
        sum(group["allocated_bytes"] for group in report["groups"])
        == row["allocated_bytes"]
    )
    assert cache.exists() and alias.exists()


def test_unobserved_alias_context_is_explicit_and_never_promises_reclaim(tmp_path):
    cache = make_file(tmp_path / ".cache/candidate.bin", 1024)
    alias = tmp_path / "outside.bin"
    os.link(cache, alias)
    row = analyze_large_files([cache.parent], min_bytes=0)["files"][0]
    assert row["observed_paths_may_be_incomplete"] is True
    assert row["observed_paths"] == [str(cache)]
    assert row["reclaim_upper_bound_bytes"] == 0
    assert row["reclaimable_bytes"] is None


@pytest.fixture(autouse=True)
def bounded_probes(monkeypatch):
    monkeypatch.setattr(large_files, "_open_evidence", empty_processes)
    monkeypatch.setattr(
        large_files,
        "_swap_evidence",
        lambda: {"status": "unavailable", "paths": set(), "identities": set()},
    )


def test_default_threshold_is_strictly_above_500_decimal_mb(tmp_path):
    make_file(tmp_path / "exact.bin", 500_000_000)
    make_file(tmp_path / "above.bin", 500_000_001)
    report = analyze_large_files([tmp_path])
    assert [Path(row["path"]).name for row in report["files"]] == ["above.bin"]
    assert report["min_bytes_exclusive"] == 500_000_000
    assert report["scan"]["status"] == "complete"
    assert report["llm_used"] is False and report["data_mutations"] == 0


def test_largest_file_is_found_after_result_limit_would_have_been_hit(tmp_path):
    for index in range(10):
        make_file(tmp_path / f"early-{index}.dat", 1024 + index)
    largest = make_file(tmp_path / "last-largest.dat", 50_000)
    report = analyze_large_files([tmp_path], min_bytes=100, limit=2)
    assert report["files"][0]["path"] == str(largest)
    assert report["scan"]["unique_large_files"] == 11
    assert report["results_truncated"] is True
    assert report["scan"]["status"] == "complete"


def test_hardlinks_and_overlapping_roots_are_not_counted_twice(tmp_path):
    root = tmp_path / "data"
    original = make_file(root / "archive.zip", 600_000_000)
    os.link(original, root / "second.zip")
    outside = tmp_path / "external-link.zip"
    os.link(original, outside)
    report = analyze_large_files([root, tmp_path])
    assert len(report["files"]) == 1
    assert report["scan"]["large_paths"] == 3
    assert report["scan"]["hardlink_paths_deduplicated"] == 2
    row = report["files"][0]
    assert row["link_count"] == 3 and row["reclaim_upper_bound_bytes"] == 0
    assert row["reclaimable_bytes"] is None
    assert set(row["observed_paths"]) == {
        str(original),
        str(root / "second.zip"),
        str(outside),
    }


def test_sparse_file_reports_blocks_separately_from_logical_size(tmp_path):
    path = make_file(tmp_path / "sparse.bin", 600_000_000)
    report = analyze_large_files([tmp_path])
    row = report["files"][0]
    assert row["logical_bytes"] == 600_000_000
    assert row["allocated_bytes"] == path.stat().st_blocks * 512
    assert row["sparse"] is True
    assert report["groups"][0]["allocated_bytes"] == row["allocated_bytes"]


def test_symlink_files_and_directories_are_not_followed(tmp_path):
    outside = make_file(tmp_path / "outside" / "large.bin", 1000)
    root = tmp_path / "root"
    root.mkdir()
    (root / "file-link").symlink_to(outside)
    (root / "dir-link").symlink_to(outside.parent, target_is_directory=True)
    report = analyze_large_files([root], min_bytes=0)
    assert report["files"] == []
    assert report["scan"]["symlinks_skipped"] == 2
    with pytest.raises(ValueError, match="Symlink"):
        analyze_large_files([root / "dir-link"])


def test_entry_budget_is_explicitly_partial(tmp_path):
    for index in range(5):
        make_file(tmp_path / f"{index}.bin", 100)
    report = analyze_large_files([tmp_path], min_bytes=0, max_entries=2)
    assert report["scan"]["entries_scanned"] == 2
    assert report["scan"]["budget_exhausted"] is True
    assert report["scan"]["status"] == "partial"


def test_permission_errors_are_not_reported_as_an_empty_complete_scan(
    tmp_path, monkeypatch
):
    denied = tmp_path / "denied"
    denied.mkdir()
    real_scandir = os.scandir

    def scandir(path):
        if Path(path) == denied:
            raise PermissionError(errno.EACCES, "denied")
        return real_scandir(path)

    monkeypatch.setattr(large_files.os, "scandir", scandir)
    report = analyze_large_files([tmp_path], min_bytes=0)
    assert report["scan"]["status"] == "partial"
    assert report["scan"]["error_samples"] == [
        {"path": str(denied), "errno": errno.EACCES}
    ]


@pytest.mark.parametrize(
    "path,kind,expected",
    [
        ("/swapfile", "other", "POSSIBLE_SWAP"),
        ("/data/.git/objects/pack/large.pack", "other", "RECOVERY_OR_SOURCE"),
        ("/data/.worktrees/task/dist/archive.zip", "archive", "RECOVERY_OR_SOURCE"),
        (
            "/home/user/.cache/JetBrains/LocalHistory/data",
            "other",
            "RECOVERY_OR_SOURCE",
        ),
        ("/home/user/.cache/PyCharm2026/index", "other", "IDE_STATE"),
        ("/data/backups/archive.tar", "archive", "BACKUP"),
        ("/data/current.db", "database", "DATABASE"),
        ("/var/lib/docker/overlay2/layer", "other", "CONTAINER_STORE"),
        ("/usr/share/ollama/.ollama/models/blob", "other", "MODEL_STORE"),
        ("/data/base.qcow2", "disk-image", "IMAGE_DEPENDENCIES"),
        ("/data/artifacts/release.tar.gz", "archive", "RELEASE_ARTIFACT"),
        ("/data/model.gguf", "model", "MODEL_STORE"),
        ("/home/user/.local/state/session/log", "other", "APPLICATION_STATE"),
        ("/home/user/.cache/tool/archive.zip", "archive", "CACHE_REVIEW"),
        ("/home/user/Downloads/archive.zip", "archive", "LARGE_USER_FILE"),
    ],
)
def test_rule_precedence_and_reasons(path, kind, expected):
    row = {
        "path": path,
        "kind": kind,
        "logical_bytes": 1000,
        "allocated_bytes": 512,
        "link_count": 1,
        "age_days": 500,
        "process_visibility": "partial",
    }
    decision = decide_file(row)
    assert decision["rule_id"] == expected
    assert decision["reasons"] and decision["next_step"]
    assert decision["automatic_delete"] is False
    assert decision["reclaimable_bytes"] is None


def test_positive_open_and_swap_evidence_override_cache_heuristics(
    tmp_path, monkeypatch
):
    path = make_file(tmp_path / ".cache" / "test.bin", 1000)
    info = path.stat()
    identity = (info.st_dev, info.st_ino)
    monkeypatch.setattr(
        large_files,
        "_open_evidence",
        lambda *a: dict(empty_processes(), opened={identity: {123}}),
    )
    report = analyze_large_files([tmp_path], min_bytes=0)
    assert report["files"][0]["rule_id"] == "OPEN_OR_MAPPED"
    monkeypatch.setattr(
        large_files,
        "_swap_evidence",
        lambda: {"status": "observed", "paths": set(), "identities": {identity}},
    )
    report = analyze_large_files([tmp_path], min_bytes=0)
    assert report["files"][0]["rule_id"] == "ACTIVE_SWAP"
    assert report["files"][0]["reclaim_upper_bound_bytes"] == 0


def test_changed_file_is_protected_and_not_given_reclaim_estimate(
    tmp_path, monkeypatch
):
    path = make_file(tmp_path / "large.bin", 1000)

    def change(*args):
        path.write_bytes(b"changed")
        return empty_processes()

    monkeypatch.setattr(large_files, "_open_evidence", change)
    report = analyze_large_files([tmp_path], min_bytes=0)
    assert report["files"][0]["rule_id"] == "CHANGED_DURING_SCAN"
    assert report["files"][0]["decision"] == "protected"


def test_signatures_override_misleading_extension():
    assert file_kind(Path("fake.zip"), b"QFI\xfb" + b"\0" * 12) == "disk-image"
    assert file_kind(Path("plain.bin"), b"SQLite format 3\0") == "database"
    assert file_kind(Path("plain.bin"), b"GGUF") == "model"
    assert file_kind(Path("image.img.gz"), b"\x1f\x8b") == "disk-image"


def test_repository_data_is_protected(tmp_path):
    (tmp_path / ".git").mkdir()
    path = make_file(tmp_path / "assets" / "unique.bin", 1000)
    report = analyze_large_files([tmp_path], min_bytes=0)
    assert report["files"][0]["repository"] == str(tmp_path)
    assert report["files"][0]["path"] == str(path)
    assert report["files"][0]["decision"] == "protected"
    # Wellman may place pytest scratch inside the checkout's .subactor tree.
    assert report["files"][0]["rule_id"] in {"RECOVERY_OR_SOURCE", "REPOSITORY_DATA"}
    assert (
        decide_file(dict(report["files"][0], path="/code/repo/assets/unique.bin"))[
            "rule_id"
        ]
        == "REPOSITORY_DATA"
    )


def test_legacy_disk_analyzer_preserves_mib_boundary_and_metadata(tmp_path):
    from fixos.diagnostics.disk_analyzer import DiskAnalyzer

    path = make_file(tmp_path / "exact.bin", 1024**2)
    analyzer = DiskAnalyzer()
    rows = analyzer.get_large_files(tmp_path, min_size_mb=1)
    assert rows[0]["path"] == str(path)
    assert rows[0]["size_mb"] == 1
    assert "category" in rows[0] and "modified" in rows[0]
    assert analyzer.large_file_scan["status"] == "complete"


@pytest.mark.parametrize(
    "kwargs", [{"limit": 0}, {"min_bytes": -1}, {"max_seconds": 0}, {"max_entries": 0}]
)
def test_invalid_limits_rejected(tmp_path, kwargs):
    with pytest.raises(ValueError):
        analyze_large_files([tmp_path], **kwargs)


def test_proc_probe_reads_descriptors_maps_and_deleted_blocks_on_every_platform(
    tmp_path, monkeypatch
):
    process = tmp_path / "proc" / "123"
    process.mkdir(parents=True)
    (process / "maps").write_text("000-fff r--p 0 08:01 99 /data/mapped-model\n")
    info = SimpleNamespace(
        st_dev=17, st_ino=42, st_mode=stat.S_IFREG, st_nlink=0, st_blocks=8
    )
    descriptor = SimpleNamespace(stat=lambda **kwargs: info)

    @contextmanager
    def fixture_scandir(path):
        if str(path) == "/proc":
            yield iter([SimpleNamespace(name="123", path=str(process))])
        elif Path(path) == process / "fd":
            yield iter([descriptor])
        else:
            raise AssertionError(f"Unexpected process path {path}")

    monkeypatch.setattr(large_files.os, "scandir", fixture_scandir)
    monkeypatch.setattr(
        large_files.os, "makedev", lambda major, minor: 17, raising=False
    )
    result = OPEN_PROBE({(17, 42), (17, 99)}, time.monotonic() + 2)
    assert result["status"] == "complete"
    assert result["opened"][(17, 42)] == {123}
    assert result["opened"][(17, 99)] == {123}
    assert result["open_deleted_files"] == 1
    assert result["open_deleted_allocated_bytes"] == 4096


def test_proc_unavailable_is_explicit_on_every_platform(monkeypatch):
    def unavailable(path):
        raise FileNotFoundError(errno.ENOENT, "no proc filesystem")

    monkeypatch.setattr(large_files.os, "scandir", unavailable)
    result = OPEN_PROBE({(17, 42)}, time.monotonic() + 2)
    assert result["status"] == "unavailable"
    assert not result["opened"]
