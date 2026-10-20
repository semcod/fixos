"""Tests for retention of date-partitioned state stores (fixos cleanup --state-old)."""

from __future__ import annotations

import json
import os
import time
from datetime import date
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from fixos.cli import _cleanup_space as space
from fixos.cli import cleanup_cmd
from fixos.diagnostics.state_retention import (
    find_partitioned_stores,
    remove_old_partitions,
    scan_state_retention,
)

TODAY = date(2026, 10, 20)
NOW = time.mktime((2026, 10, 20, 12, 0, 0, 0, 0, -1))
DAY = 86400


def _write(path: Path, size: int, age_days: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    stamp = NOW - age_days * DAY
    os.utime(path, (stamp, stamp))
    return path


def _age_dirs(root: Path, age_days: float) -> None:
    stamp = NOW - age_days * DAY
    for current, dirs, _files in os.walk(root):
        for name in dirs:
            os.utime(os.path.join(current, name), (stamp, stamp))


def _store(tmp_path: Path) -> Path:
    store = tmp_path / "state/collector/diagnostics/v1/processes"
    _write(store / "2026/09/01/00.jsonl", 1000, 49)
    _write(store / "2026/09/02/00.jsonl", 2000, 48)
    _write(store / "2026/10/19/00.jsonl", 4000, 1)
    _write(store / "checkpoint.sqlite3", 500, 60)
    _age_dirs(store / "2026/09", 48)
    return store


def _scan(tmp_path: Path, days: int = 14):
    return scan_state_retention(days, roots=[tmp_path / "state"], today=TODAY, now=NOW)


def test_finds_store_and_selects_only_old_day_partitions(tmp_path):
    store = _store(tmp_path)
    [found] = _scan(tmp_path)
    assert found.path == store
    assert [str(p.day) for p in found.old_days] == ["2026-09-01", "2026-09-02"]
    assert found.kept_days == 1
    assert found.apparent_bytes == found.reclaimable_bytes == 3000


def test_store_detection_does_not_descend_into_partitions(tmp_path):
    store = _store(tmp_path)
    _write(tmp_path / "state/other/notes.txt", 10, 100)
    assert find_partitioned_stores([tmp_path / "state"]) == [store]


def test_recent_write_into_old_named_partition_keeps_it(tmp_path):
    store = _store(tmp_path)
    _write(store / "2026/09/01/late.jsonl", 10, 0.1)
    [found] = _scan(tmp_path)
    assert [str(p.day) for p in found.old_days] == ["2026-09-02"]
    assert found.kept_days == 2


def test_current_day_cannot_be_selected(tmp_path):
    _store(tmp_path)
    with pytest.raises(ValueError):
        _scan(tmp_path, days=0)


def test_hardlink_shared_with_kept_data_is_not_reclaimable(tmp_path):
    store = _store(tmp_path)
    blob = _write(tmp_path / "state/blobs/a.blob", 5000, 60)
    os.link(blob, store / "2026/09/01/a.blob")
    os.utime(store / "2026/09/01", (NOW - 48 * DAY,) * 2)
    [found] = _scan(tmp_path)
    assert found.apparent_bytes == 8000
    assert found.reclaimable_bytes == 3000


def test_hardlinks_inside_selection_are_counted_once(tmp_path):
    store = _store(tmp_path)
    first = _write(store / "2026/09/01/b.blob", 7000, 49)
    os.link(first, store / "2026/09/01/b-copy.blob")
    os.link(first, store / "2026/09/02/b.blob")
    _age_dirs(store / "2026/09", 48)
    [found] = _scan(tmp_path)
    assert found.reclaimable_bytes == 3000 + 7000


def test_removal_keeps_checkpoint_recent_day_and_symlink_target(tmp_path):
    store = _store(tmp_path)
    outside = _write(tmp_path / "keep/precious.db", 10, 100)
    os.symlink(outside, store / "2026/09/02/link.db")
    os.utime(store / "2026/09/02/link.db", (NOW - 48 * DAY,) * 2, follow_symlinks=False)
    _age_dirs(store / "2026/09", 48)
    [found] = _scan(tmp_path)
    removed, errors = remove_old_partitions(found)
    assert (removed, errors) == (2, [])
    assert not (store / "2026/09").exists()
    assert (store / "2026/10/19/00.jsonl").is_file()
    assert (store / "checkpoint.sqlite3").is_file()
    assert outside.read_bytes() == b"x" * 10


def test_symlinked_store_root_is_ignored(tmp_path):
    real = tmp_path / "real"
    _write(real / "2026/09/01/00.jsonl", 10, 49)
    (tmp_path / "state").mkdir()
    os.symlink(real, tmp_path / "state/linked")
    assert _scan(tmp_path) == []


def _invoke(fn, *args, **kwargs):
    @click.command()
    def command():
        fn(*args, **kwargs)

    return CliRunner().invoke(command, input=kwargs.pop("input_text", ""))


def test_handler_json_reports_reclaimable_and_apparent(tmp_path, monkeypatch):
    _store(tmp_path)
    monkeypatch.setattr(
        "fixos.diagnostics.state_retention.time.time", lambda: NOW
    )
    monkeypatch.setattr(
        "fixos.diagnostics.state_retention.date",
        type("FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}),
    )
    result = _invoke(
        space._cleanup_state_old, True, False, False, False,
        days=14, roots=[tmp_path / "state"],
    )
    payload = json.loads(result.output)
    assert payload["total_bytes"] == 3000
    assert payload["candidates"][0]["partitions"] == 2


def test_cli_dry_run_lists_partitions_and_removes_nothing(tmp_path, monkeypatch):
    home = tmp_path / "home"
    _store(home / ".local")
    store = home / ".local/state/collector/diagnostics/v1/processes"
    monkeypatch.setenv("HOME", str(home))
    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services, ["--state-old", "--days", "14", "--dry-run", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert f"rm -rf {store / '2026/09/01'}" in result.output
    assert str(store / "2026/10/19") not in result.output
    assert (store / "2026/09/01/00.jsonl").is_file()


def test_policy_matrix_lists_state_old():
    ids = {policy["id"] for policy in space.CLEANUP_POLICIES}
    assert "state-old" in ids
