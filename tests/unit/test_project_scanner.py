"""Testy jednostkowe dla project_scanner (skaner artefaktów projektów dev)."""

from __future__ import annotations

import os
import time

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
