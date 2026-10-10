from fixos.diagnostics.disk_analyzer import DiskAnalyzer


def test_cleanup_suggestions_are_age_bounded_and_do_not_prune_docker_volumes():
    analyzer = DiskAnalyzer()
    suggestions = analyzer.suggest_cleanup_actions(
        analyzer.base_path,
        cache_dirs=[
            {
                "path": "/tmp/cache with spaces",
                "size_mb": 101,
                "size_gb": 0.1,
                "cache_type": "npm",
            }
        ],
        log_dirs=[
            {
                "path": "/tmp/logs with spaces",
                "size_mb": 101,
                "size_gb": 0.1,
            }
        ],
        temp_dirs=[
            {
                "path": "/tmp/temp with spaces",
                "size_mb": 101,
                "size_gb": 0.1,
                "temp_type": "system_temp",
            }
        ],
        large_files=[],
    )

    by_type = {item["type"]: item for item in suggestions}
    assert "--volumes" not in by_type["docker_cleanup"]["command"]
    assert "-mtime +7" in by_type["cache_cleanup"]["command"]
    assert "rm -rf" not in by_type["cache_cleanup"]["command"]
    assert "-mtime +30" in by_type["log_cleanup"]["command"]
    assert "rm -rf" not in by_type["temp_cleanup"]["command"]


def test_cleanup_suggestion_paths_are_shell_quoted():
    analyzer = DiskAnalyzer()
    suggestions = analyzer.suggest_cleanup_actions(
        analyzer.base_path,
        cache_dirs=[
            {
                "path": "/tmp/cache; touch SHOULD_NOT_RUN",
                "size_mb": 101,
                "size_gb": 0.1,
                "cache_type": "npm",
            }
        ],
        log_dirs=[],
        temp_dirs=[],
        large_files=[],
    )

    command = next(item["command"] for item in suggestions if item["type"] == "cache_cleanup")
    assert "'" in command


class TestDiskAnalyzerNativeScan:
    def test_get_dir_size_mb_uses_native_scan(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "cache"
        test_dir.mkdir()
        (test_dir / "data.bin").write_bytes(b"0" * 1024)

        from unittest.mock import MagicMock
        mock_measure = MagicMock(return_value={"bytes": 20971520, "files": 42})
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", mock_measure)

        analyzer = DiskAnalyzer()
        size = analyzer._get_dir_size_mb(test_dir)
        assert size == 20.0
        mock_measure.assert_called_once()

    def test_count_files_fast_uses_native_scan(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "cache"
        test_dir.mkdir()

        from unittest.mock import MagicMock
        mock_measure = MagicMock(return_value={"bytes": 1024, "files": 15})
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", mock_measure)

        analyzer = DiskAnalyzer()
        count = analyzer._count_files_fast(test_dir)
        assert count == 15
        mock_measure.assert_called_once()

    def test_get_dir_size_mb_falls_back_to_du(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "cache"
        test_dir.mkdir()

        from unittest.mock import MagicMock
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", MagicMock(side_effect=OSError("not found")))

        fake_du = MagicMock(return_value=MagicMock(returncode=0, stdout="10485760\t/cache\n"))
        monkeypatch.setattr("subprocess.run", fake_du)

        analyzer = DiskAnalyzer()
        size = analyzer._get_dir_size_mb(test_dir)
        assert round(size, 2) == 10.0
        fake_du.assert_called_once()

    def test_count_files_fast_falls_back_to_find(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "cache"
        test_dir.mkdir()

        from unittest.mock import MagicMock
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", MagicMock(side_effect=OSError("not found")))

        fake_find = MagicMock(return_value=MagicMock(returncode=0, stdout="f1\nf2\nf3\n"))
        monkeypatch.setattr("subprocess.run", fake_find)

        analyzer = DiskAnalyzer()
        count = analyzer._count_files_fast(test_dir)
        assert count == 3
        fake_find.assert_called_once()

    def test_nonexistent_paths_handled_gracefully(self, tmp_path):
        analyzer = DiskAnalyzer()
        nonexistent = tmp_path / "nope"
        assert analyzer._get_dir_size_mb(nonexistent) == 0.0
        assert analyzer._count_files_fast(nonexistent) == 0

