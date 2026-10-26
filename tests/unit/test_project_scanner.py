"""Testy jednostkowe dla project_scanner (skaner artefaktów projektów dev)."""

from __future__ import annotations

import os
import time
from datetime import timezone

from fixos.diagnostics import project_scanner as ps


def _make_git_project(base, name):
    proj = base / name
    (proj / ".git").mkdir(parents=True)
    return proj


class TestDiscoverProjectRoots:
    def test_finds_git_repo(self, tmp_path):
        proj = _make_git_project(tmp_path, "myrepo")

        roots = ps.discover_project_roots(tmp_path)

        assert roots == [proj]

    def test_finds_pyproject_toml_project(self, tmp_path):
        proj = tmp_path / "pylib"
        proj.mkdir()
        (proj / "pyproject.toml").write_text("[project]\nname='x'\n")

        roots = ps.discover_project_roots(tmp_path)

        assert roots == [proj]

    def test_does_not_descend_into_discovered_project(self, tmp_path):
        proj = _make_git_project(tmp_path, "outer")
        nested = proj / "vendor" / "nested"
        (nested / ".git").mkdir(parents=True)

        roots = ps.discover_project_roots(tmp_path)

        assert roots == [proj]

    def test_prunes_node_modules_from_search(self, tmp_path):
        proj = _make_git_project(tmp_path, "app")
        fake_nested_pkg = proj / "node_modules" / "some-lib"
        fake_nested_pkg.mkdir(parents=True)
        (fake_nested_pkg / "package.json").write_text("{}")

        roots = ps.discover_project_roots(tmp_path)

        # Only the real project, never something inside node_modules.
        assert roots == [proj]

    def test_respects_max_depth(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        (deep / ".git").mkdir(parents=True)

        assert ps.discover_project_roots(tmp_path, max_depth=2) == []
        assert ps.discover_project_roots(tmp_path, max_depth=10) == [deep]

    def test_returns_empty_for_missing_base(self, tmp_path):
        assert ps.discover_project_roots(tmp_path / "does-not-exist") == []


class TestArtifactVerification:
    def test_venv_requires_pyvenv_cfg(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        (proj / "venv").mkdir()  # no pyvenv.cfg -> not a real venv

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        artifacts = ps.scan_project_artifacts(proj, threshold_mb=1)

        assert artifacts == []

    def test_venv_with_pyvenv_cfg_is_reported(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        venv_dir = proj / "venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n")

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        artifacts = ps.scan_project_artifacts(proj, threshold_mb=1)

        assert len(artifacts) == 1
        assert artifacts[0].artifact_name == "venv"
        assert artifacts[0].risk_level == "safe"

    def test_target_requires_cargo_toml(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        (proj / "target").mkdir()  # no Cargo.toml -> ambiguous generic name

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        assert ps.scan_project_artifacts(proj, threshold_mb=1) == []

        (proj / "Cargo.toml").write_text("[package]\nname='x'\n")
        artifacts = ps.scan_project_artifacts(proj, threshold_mb=1)
        assert len(artifacts) == 1
        assert artifacts[0].artifact_name == "target"

    def test_node_modules_requires_package_json(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        (proj / "node_modules").mkdir()

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        assert ps.scan_project_artifacts(proj, threshold_mb=1) == []

        (proj / "package.json").write_text("{}")
        artifacts = ps.scan_project_artifacts(proj, threshold_mb=1)
        assert len(artifacts) == 1
        assert artifacts[0].artifact_name == "node_modules"

    def test_dist_and_build_are_review_risk(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        (proj / "dist").mkdir()
        (proj / "build").mkdir()

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        artifacts = ps.scan_project_artifacts(proj, threshold_mb=1)

        assert {a.artifact_name for a in artifacts} == {"dist", "build"}
        assert all(a.risk_level == "review" for a in artifacts)

    def test_threshold_filters_small_artifacts(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        venv_dir = proj / ".venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n")

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 10.0)

        assert ps.scan_project_artifacts(proj, threshold_mb=50) == []
        assert len(ps.scan_project_artifacts(proj, threshold_mb=5)) == 1

    def test_unknown_directory_name_is_ignored(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        (proj / "src").mkdir()
        (proj / "docs").mkdir()

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        assert ps.scan_project_artifacts(proj, threshold_mb=1) == []


class TestStaleness:
    def test_stale_flag_based_on_mtime(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        venv_dir = proj / ".venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n")

        old_time = time.time() - (120 * 86400)  # 120 days ago
        os.utime(venv_dir, (old_time, old_time))

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        artifacts = ps.scan_project_artifacts(proj, threshold_mb=1, stale_days=90)

        assert len(artifacts) == 1
        assert artifacts[0].stale is True
        assert artifacts[0].days_since_modified >= 119

    def test_recently_modified_is_not_stale(self, tmp_path, monkeypatch):
        proj = _make_git_project(tmp_path, "repo")
        venv_dir = proj / ".venv"
        venv_dir.mkdir()
        (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin\n")

        monkeypatch.setattr(ps, "_get_dir_size_mb", lambda p: 500.0)

        artifacts = ps.scan_project_artifacts(proj, threshold_mb=1, stale_days=90)

        assert artifacts[0].stale is False


class TestSummary:
    def test_find_duplicate_venvs(self, tmp_path):
        artifacts = [
            ps.ProjectArtifact(
                project_name="repo",
                project_path="/x/repo",
                artifact_name="venv",
                artifact_path="/x/repo/venv",
                size_mb=100,
                size_gb=0.1,
                description="",
                ecosystem="python",
                risk_level="safe",
                days_since_modified=1,
                stale=False,
                cleanup_command="rm -rf /x/repo/venv",
            ),
            ps.ProjectArtifact(
                project_name="repo",
                project_path="/x/repo",
                artifact_name=".venv",
                artifact_path="/x/repo/.venv",
                size_mb=100,
                size_gb=0.1,
                description="",
                ecosystem="python",
                risk_level="safe",
                days_since_modified=1,
                stale=False,
                cleanup_command="rm -rf /x/repo/.venv",
            ),
        ]

        assert ps.find_duplicate_venvs(artifacts) == ["/x/repo"]

    def test_summarize_totals(self):
        artifacts = [
            ps.ProjectArtifact(
                project_name="a",
                project_path="/a",
                artifact_name="venv",
                artifact_path="/a/venv",
                size_mb=1024,
                size_gb=1.0,
                description="",
                ecosystem="python",
                risk_level="safe",
                days_since_modified=200,
                stale=True,
                cleanup_command="rm -rf /a/venv",
            ),
            ps.ProjectArtifact(
                project_name="b",
                project_path="/b",
                artifact_name="dist",
                artifact_path="/b/dist",
                size_mb=512,
                size_gb=0.5,
                description="",
                ecosystem="generic",
                risk_level="review",
                days_since_modified=5,
                stale=False,
                cleanup_command="rm -rf /b/dist",
            ),
        ]

        stats = ps.summarize(artifacts)

        assert stats["total_gb"] == 1.5
        assert stats["safe_gb"] == 1.0
        assert stats["review_gb"] == 0.5
        assert stats["stale_gb"] == 1.0
        assert stats["projects_count"] == 2


class TestScanAll:
    def test_scan_all_sorts_by_size_descending(self, tmp_path, monkeypatch):
        small = _make_git_project(tmp_path, "small-repo")
        (small / "venv").mkdir()
        (small / "venv" / "pyvenv.cfg").write_text("home = /usr/bin\n")

        big = _make_git_project(tmp_path, "big-repo")
        (big / "node_modules").mkdir()
        (big / "package.json").write_text("{}")

        def fake_size(path):
            return 200.0 if "big-repo" in path else 50.0

        monkeypatch.setattr(ps, "_get_dir_size_mb", fake_size)

        results = ps.scan_all(tmp_path, threshold_mb=1)

        assert [a.project_name for a in results] == ["big-repo", "small-repo"]


class TestNativeScanProjectScanner:
    def test_get_dir_size_mb_uses_native_scan(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "node_modules"
        test_dir.mkdir()
        (test_dir / "file.js").write_text("console.log('hello');")

        from unittest.mock import MagicMock
        mock_measure = MagicMock(return_value={"bytes": 10485760})
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", mock_measure)

        size = ps._get_dir_size_mb(str(test_dir))
        assert size == 10.0
        mock_measure.assert_called_once()

    def test_get_dir_size_mb_falls_back_to_du(self, tmp_path, monkeypatch):
        test_dir = tmp_path / "venv"
        test_dir.mkdir()

        from unittest.mock import MagicMock
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", MagicMock(side_effect=OSError("binary unavailable")))

        fake_du = MagicMock(return_value=MagicMock(returncode=0, stdout="20480 /tmp/venv\n"))
        monkeypatch.setattr("subprocess.run", fake_du)

        size = ps._get_dir_size_mb(str(test_dir))
        assert size == 20.0
        fake_du.assert_called_once()

    def test_get_dir_size_mb_handles_nonexistent_path(self, tmp_path):
        assert ps._get_dir_size_mb(str(tmp_path / "nonexistent")) == 0.0


class TestDevProjectAnalyzerRegression:
    def test_get_dir_size_uses_native_scan(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from fixos.diagnostics.dev_project_analyzer import DevProjectAnalyzer

        test_dir = tmp_path / "node_modules"
        test_dir.mkdir()
        (test_dir / "pkg.json").write_text("{}")

        mock_measure = MagicMock(return_value={"bytes": 4194304, "mtime_ns": 1000})
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", mock_measure)

        analyzer = DevProjectAnalyzer(str(tmp_path))
        size = analyzer._get_dir_size(test_dir)
        assert size == 4194304
        mock_measure.assert_called_once()

    def test_get_dir_size_falls_back_to_du(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from fixos.diagnostics.dev_project_analyzer import DevProjectAnalyzer

        test_dir = tmp_path / "venv"
        test_dir.mkdir()

        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.measure_tree",
            MagicMock(side_effect=OSError("native unavailable")),
        )
        fake_du = MagicMock(
            return_value=MagicMock(returncode=0, stdout="8388608\t/fake/venv\n")
        )
        monkeypatch.setattr("subprocess.run", fake_du)

        analyzer = DevProjectAnalyzer(str(tmp_path))
        size = analyzer._get_dir_size(test_dir)
        assert size == 8388608
        fake_du.assert_called_once()

    def test_7d_staleness_reporting_in_summary(self, tmp_path, monkeypatch):
        from datetime import datetime, timedelta

        from fixos.diagnostics.dev_project_analyzer import (
            DevProjectAnalyzer,
            ProjectDependency,
        )

        analyzer = DevProjectAnalyzer(str(tmp_path))

        stale_dep = ProjectDependency(
            name="node_modules",
            path=str(tmp_path / "old_proj" / "node_modules"),
            size_bytes=100 * 1024 * 1024,
            dep_type="node_modules",
            project_name="old_proj",
            last_modified=datetime.now() - timedelta(days=8),
            can_recreate=True,
            recreate_command="npm install",
        )
        fresh_dep = ProjectDependency(
            name="venv",
            path=str(tmp_path / "new_proj" / "venv"),
            size_bytes=50 * 1024 * 1024,
            dep_type="venv",
            project_name="new_proj",
            last_modified=datetime.now() - timedelta(days=2),
            can_recreate=True,
            recreate_command="python -m venv venv",
        )
        deps = [stale_dep, fresh_dep]
        monkeypatch.setattr(
            analyzer,
            "analyze",
            lambda: {
                "dependencies": [d.to_dict() for d in deps],
                "total_size": sum(d.size_bytes for d in deps),
                "total_size_human": "150.0 MB",
                "projects_affected": 2,
            },
        )
        analyzer.dependencies = deps
        analyzer.total_size = sum(d.size_bytes for d in deps)

        summary = analyzer.get_summary()
        assert "[8d old]" in summary
        assert "old_proj" in summary
        assert "new_proj" in summary
        assert "[2d old]" not in summary

    def test_git_activity_updates_last_modified(self, tmp_path, monkeypatch):
        from datetime import datetime

        from fixos.diagnostics.dev_project_analyzer import DevProjectAnalyzer

        project = tmp_path / "my_project"
        git_dir = project / ".git"
        git_dir.mkdir(parents=True)
        dep_dir = project / "node_modules"
        dep_dir.mkdir()
        (project / "package.json").write_text("{}")

        old_mtime = time.time() - (20 * 86400)
        os.utime(dep_dir, (old_mtime, old_mtime))

        git_index = git_dir / "index"
        git_index.write_text("dummy")
        recent_mtime = time.time() - 3600
        os.utime(git_index, (recent_mtime, recent_mtime))

        monkeypatch.setattr(DevProjectAnalyzer, "_get_dir_size", lambda self, path: 1024)

        analyzer = DevProjectAnalyzer(str(tmp_path))
        dep = analyzer._check_dependency_folder(dep_dir)
        assert dep is not None
        assert dep.last_modified is not None
        assert (datetime.now() - dep.last_modified).days == 0

    def test_batch_measure_caches_results(self, tmp_path, monkeypatch):
        from unittest.mock import MagicMock

        from fixos.diagnostics.dev_project_analyzer import DevProjectAnalyzer

        d1 = tmp_path / "d1"
        d1.mkdir()
        d2 = tmp_path / "d2"
        d2.mkdir()

        mock_batch = MagicMock(
            return_value={
                str(d1.resolve()): {"bytes": 1000, "mtime_ns": 100},
                str(d2.resolve()): {"bytes": 2000, "mtime_ns": 200},
            }
        )
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_batch", mock_batch)

        analyzer = DevProjectAnalyzer(str(tmp_path))
        results = analyzer._batch_measure([d1, d2])
        assert len(results) == 2
        mock_batch.assert_called_once()
        assert analyzer._get_dir_size(d1) == 1000
        assert analyzer._get_dir_size(d2) == 2000


class TestDiskAnalyzerBoundedExecution:
    def test_newest_file_date_uses_measure_tree(self, tmp_path, monkeypatch):
        from datetime import datetime
        from unittest.mock import MagicMock

        from fixos.diagnostics.disk_analyzer import DiskAnalyzer

        test_dir = tmp_path / "logs"
        test_dir.mkdir()

        ts_ns = int(
            datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc).timestamp() * 1e9
        )
        mock_measure = MagicMock(return_value={"mtime_ns": ts_ns})
        monkeypatch.setattr("fixos.diagnostics.native_scan.measure_tree", mock_measure)

        analyzer = DiskAnalyzer()
        res = analyzer._get_newest_file_date(test_dir)
        assert "2026-10-20" in res
        mock_measure.assert_called_once()

    def test_bounded_walk_never_calls_rglob(self, tmp_path, monkeypatch):
        from pathlib import Path
        from unittest.mock import MagicMock

        from fixos.diagnostics.disk_analyzer import DiskAnalyzer

        test_dir = tmp_path / "deep_logs"
        test_dir.mkdir()
        (test_dir / "test.log").write_text("log line")

        def fail_rglob(*args, **kwargs):
            raise AssertionError("rglob must not be called")

        monkeypatch.setattr(Path, "rglob", fail_rglob)
        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.measure_tree",
            MagicMock(side_effect=OSError("no native")),
        )

        analyzer = DiskAnalyzer()
        oldest = analyzer._get_oldest_file_date(test_dir)
        newest = analyzer._get_newest_file_date(test_dir)
        assert oldest != "unknown"
        assert newest != "unknown"

    def test_bounded_walk_respects_max_depth_and_max_files(
        self, tmp_path, monkeypatch
    ):
        from unittest.mock import MagicMock

        from fixos.diagnostics.disk_analyzer import DiskAnalyzer

        monkeypatch.setattr(
            "fixos.diagnostics.native_scan.measure_tree",
            MagicMock(side_effect=OSError("no native")),
        )
        base = tmp_path / "logs"
        deep = base / "l1" / "l2" / "l3" / "l4" / "l5"
        deep.mkdir(parents=True)
        (deep / "very_deep.log").write_text("deep")

        analyzer = DiskAnalyzer()
        res = analyzer._get_oldest_file_date(base, max_depth=2)
        assert res == "unknown"

        res = analyzer._get_oldest_file_date(base, max_depth=6)
        assert res != "unknown"

