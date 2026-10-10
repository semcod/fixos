"""Unit tests for native Rust scanning acceleration and Python fallbacks."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from fixos.diagnostics.native_scan import (
    PROTOCOL,
    find_native_binary,
    measure_batch,
    measure_python,
    measure_tree,
    scan_dir_native,
)


class TestFindNativeBinary:
    def test_honors_env_off(self, monkeypatch):
        monkeypatch.setenv("FIXOS_NATIVE", "off")
        assert find_native_binary() is None

    def test_honors_env_bin_path(self, monkeypatch, tmp_path):
        fake_bin = tmp_path / "custom-native-bin"
        fake_bin.touch(mode=0o755)
        monkeypatch.setenv("FIXOS_NATIVE_BIN", str(fake_bin))
        monkeypatch.setenv("FIXOS_NATIVE", "auto")
        assert find_native_binary() == fake_bin

    def test_finds_system_or_returns_none(self, monkeypatch):
        monkeypatch.delenv("FIXOS_NATIVE_BIN", raising=False)
        monkeypatch.setenv("FIXOS_NATIVE", "auto")
        bin_path = find_native_binary()
        if bin_path is not None:
            assert isinstance(bin_path, Path)
            assert bin_path.is_file()
            assert os.access(bin_path, os.X_OK)


class TestMeasurePython:
    def test_measures_empty_directory(self, tmp_path):
        res = measure_python(tmp_path)
        assert res["protocol"] == PROTOCOL
        assert res["path"] == str(tmp_path)
        assert res["bytes"] >= 0
        assert res["entries"] == 1
        assert res["errors"] == []

    def test_measures_files_and_subdirectories(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        f1 = tmp_path / "file1.txt"
        f1.write_bytes(b"hello world")
        f2 = sub / "file2.bin"
        f2.write_bytes(b"1234567890" * 100)

        res = measure_python(tmp_path)
        assert res["entries"] == 4  # tmp_path (root), sub, f1, f2
        assert res["bytes"] >= 1011

    def test_excludes_specified_names(self, tmp_path):
        f1 = tmp_path / "keep.txt"
        f1.write_bytes(b"keep me")
        f2 = tmp_path / "skip.txt"
        f2.write_bytes(b"skip me please")

        res = measure_python(tmp_path, exclude=("skip.txt",))
        assert res["entries"] == 2  # dir + keep.txt


class TestMeasureTree:
    def test_measure_tree_falls_back_to_python_on_subprocess_error(self, tmp_path, monkeypatch):
        (tmp_path / "test.txt").write_bytes(b"data")

        def fake_run(*args, **kwargs):
            raise subprocess.SubprocessError("Native failure")

        monkeypatch.setattr("fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake"))
        monkeypatch.setattr("subprocess.run", fake_run)

        res = measure_tree(tmp_path, native=True)
        assert res["protocol"] == PROTOCOL
        assert res["bytes"] >= 4
        assert res["entries"] >= 2

    def test_measure_tree_uses_native_output_when_valid(self, tmp_path, monkeypatch):
        mock_output = {
            "protocol": PROTOCOL,
            "path": str(tmp_path),
            "bytes": 42000,
            "entries": 5,
            "mtime_ns": 1000,
            "atime_ns": 2000,
            "errors": [],
        }

        mock_proc = MagicMock()
        mock_proc.stdout = json.dumps(mock_output)

        monkeypatch.setattr("fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake"))
        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: mock_proc)

        res = measure_tree(tmp_path, native=True)
        assert res["bytes"] == 42000
        assert res["entries"] == 5


class TestMeasureBatch:
    def test_empty_paths_returns_empty_dict(self):
        assert measure_batch([]) == {}

    def test_batch_fallback_to_python(self, tmp_path, monkeypatch):
        d1 = tmp_path / "d1"
        d1.mkdir()
        (d1 / "f.txt").write_bytes(b"alpha")
        d2 = tmp_path / "d2"
        d2.mkdir()
        (d2 / "f.txt").write_bytes(b"beta")

        # Disable native to force Python path
        res = measure_batch([d1, d2], native=False)
        assert str(d1.resolve()) in res
        assert str(d2.resolve()) in res
        assert res[str(d1.resolve())]["bytes"] >= 5
        assert res[str(d2.resolve())]["bytes"] >= 4

    def test_batch_native_mock(self, tmp_path, monkeypatch):
        d1 = tmp_path / "d1"
        d1.mkdir()

        mock_output = {
            "protocol": PROTOCOL,
            "measurements": {
                str(d1.resolve()): {
                    "bytes": 9999,
                    "entries": 2,
                    "mtime_ns": 1,
                    "atime_ns": 2,
                    "errors": [],
                }
            },
        }
        mock_proc = MagicMock()
        mock_proc.stdout = json.dumps(mock_output)

        monkeypatch.setattr("fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake"))
        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: mock_proc)

        res = measure_batch([d1], native=True)
        assert str(d1.resolve()) in res
        assert res[str(d1.resolve())]["bytes"] == 9999


class TestScanDirNative:
    def test_returns_none_for_non_directory(self, tmp_path):
        f = tmp_path / "file.txt"
        f.touch()
        assert scan_dir_native(f) is None

    def test_returns_none_when_binary_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fixos.diagnostics.native_scan.find_native_binary", lambda: None)
        assert scan_dir_native(tmp_path) is None

    def test_parses_native_scan_dir_output(self, tmp_path, monkeypatch):
        mock_output = {
            "protocol": PROTOCOL,
            "base": str(tmp_path),
            "entries": [
                {"name": "pip", "path": str(tmp_path / "pip"), "bytes": 50000000},
                {"name": "npm", "path": str(tmp_path / "npm"), "bytes": 20000000},
            ],
        }
        mock_proc = MagicMock()
        mock_proc.stdout = json.dumps(mock_output)

        monkeypatch.setattr("fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake"))
        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: mock_proc)

        entries = scan_dir_native(tmp_path)
        assert entries is not None
        assert len(entries) == 2
        assert entries[0]["name"] == "pip"
        assert entries[0]["bytes"] == 50000000
