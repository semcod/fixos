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


class TestMeasureBatchBudget:
    def test_no_python_fallback_returns_empty_without_native(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FIXOS_NATIVE", "off")
        walked = MagicMock()
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_python", walked)

        assert measure_batch([tmp_path], python_fallback=False) == {}
        walked.assert_not_called()

    def test_native_timeout_is_passed_through(self, tmp_path, monkeypatch):
        fake_bin = tmp_path / "fixos-native"
        fake_bin.touch(mode=0o755)
        monkeypatch.setenv("FIXOS_NATIVE_BIN", str(fake_bin))
        monkeypatch.setenv("FIXOS_NATIVE", "auto")
        seen = {}

        def slow_run(cmd, **kwargs):
            seen["timeout"] = kwargs["timeout"]
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

        monkeypatch.setattr("fixos.diagnostics.native_scan.subprocess.run", slow_run)

        assert measure_batch([tmp_path], timeout=3.0, python_fallback=False) == {}
        assert seen["timeout"] == 3.0


def _valid_measurement(bytes_val: int = 100, *, errors: list[str] | None = None) -> dict:
    return {
        "bytes": bytes_val,
        "entries": 2,
        "mtime_ns": 10,
        "atime_ns": 20,
        "errors": [] if errors is None else errors,
    }


class TestMeasureBatchContract:
    def test_partial_native_result_falls_back_for_missing_path_when_allowed(
        self, tmp_path, monkeypatch
    ):
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        (d2 / "payload.bin").write_bytes(b"a" * 2048)

        payload = {
            "protocol": PROTOCOL,
            "measurements": {str(d1.resolve()): _valid_measurement(4096)},
        }
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
        )

        res = measure_batch([d1, d2], python_fallback=True)
        assert set(res.keys()) == {str(d1.resolve()), str(d2.resolve())}
        assert res[str(d1.resolve())]["bytes"] == 4096
        assert res[str(d1.resolve())]["complete"] is True
        assert res[str(d2.resolve())]["bytes"] >= 2048
        assert res[str(d2.resolve())]["complete"] is True

    def test_partial_native_result_never_fabricates_missing_path_when_no_fallback(
        self, tmp_path, monkeypatch
    ):
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()

        payload = {
            "protocol": PROTOCOL,
            "measurements": {str(d1.resolve()): _valid_measurement(4096)},
        }
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
        )

        res = measure_batch([d1, d2], python_fallback=False)
        assert list(res.keys()) == [str(d1.resolve())]
        assert str(d2.resolve()) not in res

    def test_unsupported_cli_nonzero_exit_falls_back_safely(self, tmp_path, monkeypatch):
        d1 = tmp_path / "d1"
        d1.mkdir()
        (d1 / "item.bin").write_bytes(b"x" * 1024)

        def fail_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(2, cmd, stderr="unknown command")

        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )
        monkeypatch.setattr("fixos.diagnostics.native_scan.subprocess.run", fail_run)

        assert measure_batch([d1], python_fallback=False) == {}
        res = measure_batch([d1], python_fallback=True)
        assert res[str(d1.resolve())]["bytes"] >= 1024
        assert res[str(d1.resolve())]["complete"] is True

    def test_malformed_json_and_non_dict_entries_do_not_crash(self, tmp_path, monkeypatch):
        d1 = tmp_path / "d1"
        d1.mkdir()
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )

        bad_outputs = [
            "{not json",
            json.dumps({"protocol": "other/v0", "measurements": {str(d1.resolve()): _valid_measurement()}}),
            json.dumps({"protocol": PROTOCOL, "measurements": []}),
            json.dumps({"protocol": PROTOCOL, "measurements": {str(d1.resolve()): "not-a-dict"}}),
            json.dumps({"protocol": PROTOCOL, "measurements": {str(d1.resolve()): {**_valid_measurement(), "bytes": True}}}),
            json.dumps({"protocol": PROTOCOL, "measurements": {str(d1.resolve()): {**_valid_measurement(), "errors": "err"}}}),
            json.dumps({"protocol": PROTOCOL, "measurements": {str(tmp_path / "unexpected"): _valid_measurement()}}),
        ]
        for raw in bad_outputs:
            monkeypatch.setattr(
                "fixos.diagnostics.native_scan.subprocess.run",
                lambda *a, payload=raw, **kw: subprocess.CompletedProcess(a[0], 0, payload, ""),
            )
            assert measure_batch([d1], python_fallback=False) == {}, raw

    def test_non_empty_exclude_skips_native_batch_that_lacks_exclude_support(
        self, tmp_path, monkeypatch
    ):
        d1 = tmp_path / "d1"
        d1.mkdir()
        (d1 / "skip.bin").write_bytes(b"s" * 4096)
        (d1 / "keep.bin").write_bytes(b"k" * 512)
        called = MagicMock()
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )
        monkeypatch.setattr("fixos.diagnostics.native_scan.subprocess.run", called)

        assert measure_batch([d1], exclude=("skip.bin",), python_fallback=False) == {}
        called.assert_not_called()

        res = measure_batch([d1], exclude=("skip.bin",), python_fallback=True)
        called.assert_not_called()
        assert res[str(d1.resolve())]["complete"] is True
        assert res[str(d1.resolve())]["entries"] == 2

    def test_child_errors_preserve_incomplete_flag(self, tmp_path, monkeypatch):
        d1 = tmp_path / "d1"
        d1.mkdir()
        payload = {
            "protocol": PROTOCOL,
            "measurements": {
                str(d1.resolve()): _valid_measurement(512, errors=[f"{d1}/secret: Permission denied"])
            },
        }
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
        )

        res = measure_batch([d1], python_fallback=False)
        entry = res[str(d1.resolve())]
        assert entry["complete"] is False
        assert entry["errors"] == [f"{d1}/secret: Permission denied"]

    def test_python_fallback_permission_error_marks_incomplete(
        self, tmp_path, monkeypatch
    ):
        secret = tmp_path / "secret"
        secret.mkdir()
        (secret / "hidden.txt").write_text("hidden", encoding="utf-8")
        secret_resolved = secret.resolve()
        real_scandir = os.scandir

        def fake_scandir(path="."):
            if isinstance(path, (str, os.PathLike)) and Path(path).resolve() == secret_resolved:
                raise PermissionError(13, "Permission denied", str(path))
            return real_scandir(path)

        monkeypatch.setattr("fixos.diagnostics.native_scan.os.scandir", fake_scandir)
        res = measure_batch([tmp_path], native=False, python_fallback=True)
        entry = res[str(tmp_path.resolve())]
        assert entry["complete"] is False
        assert entry["errors"]


class TestScanDirNativeContract:
    def test_accepts_stash_v1_schema_with_path_and_errors(self, tmp_path, monkeypatch):
        sub = tmp_path / "uv"
        sub.mkdir()
        payload = {
            "protocol": PROTOCOL,
            "path": str(tmp_path.resolve()),
            "entries": [
                {
                    "name": "uv",
                    "path": str(sub.resolve()),
                    "bytes": 4096,
                    "entries": 3,
                    "mtime_ns": 100,
                    "atime_ns": 200,
                    "errors": [],
                }
            ],
        }
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
        )

        entries = scan_dir_native(tmp_path)
        assert entries is not None
        assert len(entries) == 1
        assert entries[0]["complete"] is True
        assert entries[0]["errors"] == []

    def test_rejects_failure_modes_without_fabricating_empty_success(
        self, tmp_path, monkeypatch
    ):
        sub = tmp_path / "a"
        sub.mkdir()
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )

        bad_payloads = [
            "{broken",
            json.dumps({"protocol": "wrong/v1", "path": str(tmp_path), "entries": []}),
            json.dumps({"protocol": PROTOCOL, "entries": []}),
            json.dumps({"protocol": PROTOCOL, "path": "/elsewhere", "entries": []}),
            json.dumps({"protocol": PROTOCOL, "path": str(tmp_path), "errors": ["read_dir failed"], "entries": []}),
            json.dumps({"protocol": PROTOCOL, "path": str(tmp_path), "entries": ["not-a-dict"]}),
            json.dumps({"protocol": PROTOCOL, "path": str(tmp_path), "entries": [{"name": "../escape", "path": str(tmp_path / "../escape"), "bytes": 10}]}),
            json.dumps({"protocol": PROTOCOL, "path": str(tmp_path), "entries": [{"name": "a", "path": "/wrong/a", "bytes": 10}]}),
            json.dumps({"protocol": PROTOCOL, "path": str(tmp_path), "entries": [{"name": "a", "path": str(sub), "bytes": True}]}),
            # Silent drop when min_bytes == 0 (`sub` is on disk but omitted from entries)
            json.dumps({"protocol": PROTOCOL, "path": str(tmp_path), "entries": []}),
        ]
        for raw in bad_payloads:
            monkeypatch.setattr(
                "fixos.diagnostics.native_scan.subprocess.run",
                lambda *a, payload=raw, **kw: subprocess.CompletedProcess(a[0], 0, payload, ""),
            )
            assert scan_dir_native(tmp_path) is None, raw

        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            MagicMock(side_effect=subprocess.TimeoutExpired("fixos-native", 5)),
        )
        assert scan_dir_native(tmp_path, timeout=5) is None

        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            MagicMock(side_effect=subprocess.CalledProcessError(2, ["fixos-native"])),
        )
        assert scan_dir_native(tmp_path) is None

    def test_root_and_child_permission_errors_return_none_when_omitted(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )

        # Unreadable child omitted by min_bytes filtering must not look complete.
        secret = tmp_path / "secret"
        secret.mkdir()
        secret_resolved = secret.resolve()
        real_access = os.access

        def fake_access(path, mode):
            if isinstance(path, (str, os.PathLike)) and Path(path).resolve() == secret_resolved:
                return False
            return real_access(path, mode)

        monkeypatch.setattr("fixos.diagnostics.native_scan.os.access", fake_access)
        payload = {"protocol": PROTOCOL, "path": str(tmp_path.resolve()), "entries": []}
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
        )
        assert scan_dir_native(tmp_path, min_bytes=1024) is None

        # Unreadable root returns None before trusting empty native results.
        root_dir = tmp_path / "locked_root"
        root_dir.mkdir()
        root_resolved = root_dir.resolve()
        real_scandir = os.scandir

        def fake_scandir(path="."):
            if isinstance(path, (str, os.PathLike)) and Path(path).resolve() == root_resolved:
                raise PermissionError(13, "Permission denied", str(path))
            return real_scandir(path)

        monkeypatch.setattr("fixos.diagnostics.native_scan.os.scandir", fake_scandir)
        assert scan_dir_native(root_dir) is None

    def test_child_entry_errors_mark_complete_false(self, tmp_path, monkeypatch):
        sub = tmp_path / "cache"
        sub.mkdir()
        payload = {
            "protocol": PROTOCOL,
            "path": str(tmp_path.resolve()),
            "entries": [
                {
                    "name": "cache",
                    "path": str(sub.resolve()),
                    "bytes": 2048,
                    "errors": [f"{sub}/locked: Permission denied"],
                }
            ],
        }
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.find_native_binary", lambda: Path("/bin/fake")
        )
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, json.dumps(payload), ""),
        )

        entries = scan_dir_native(tmp_path, min_bytes=1024)
        assert entries is not None
        assert len(entries) == 1
        assert entries[0]["complete"] is False
        assert entries[0]["errors"] == [f"{sub}/locked: Permission denied"]
