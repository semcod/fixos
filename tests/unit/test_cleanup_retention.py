"""Tests for cleanup retention duration parsing, Trash, Thumbnails, and policy transparency."""

from __future__ import annotations

import json
import os
import time

import click
import pytest
from click.testing import CliRunner

from fixos.cli import _cleanup_space as space
from fixos.cli import cleanup_cmd
from fixos.diagnostics.service_cleanup import ServiceCleaner


def _invoke(fn, *args, **kwargs):
    input_text = kwargs.pop("input_text", "")

    @click.command()
    def command():
        fn(*args, **kwargs)

    return CliRunner().invoke(command, input=input_text)


class TestParseRetentionDays:
    def test_default_and_none(self):
        assert space.parse_retention_days(None) == 1.0
        assert space.parse_retention_days(None, default_days=7.0) == 7.0
        assert space.parse_retention_days("", default_days=14.0) == 14.0
        assert space.parse_retention_days("   ", default_days=30.0) == 30.0

    def test_numeric_inputs(self):
        assert space.parse_retention_days(3) == 3.0
        assert space.parse_retention_days(2.5) == 2.5
        assert space.parse_retention_days("5") == 5.0
        assert space.parse_retention_days("10.5") == 10.5

    def test_hours_units(self):
        assert space.parse_retention_days("24h") == 1.0
        assert space.parse_retention_days("12h") == 0.5
        assert space.parse_retention_days("48hr") == 2.0
        assert space.parse_retention_days("6hours") == 0.25
        assert space.parse_retention_days("24 godz") == 1.0

    def test_days_units(self):
        assert space.parse_retention_days("1d") == 1.0
        assert space.parse_retention_days("7d") == 7.0
        assert space.parse_retention_days("14 days") == 14.0
        assert space.parse_retention_days("30 dni") == 30.0
        assert space.parse_retention_days("2 doby") == 2.0

    def test_weeks_units(self):
        assert space.parse_retention_days("1w") == 7.0
        assert space.parse_retention_days("2w") == 14.0
        assert space.parse_retention_days("3 weeks") == 21.0
        assert space.parse_retention_days("4 tygodnie") == 28.0

    def test_minutes_and_seconds(self):
        assert space.parse_retention_days("1440m") == 1.0
        assert pytest.approx(space.parse_retention_days("30min"), 0.0001) == 30 / 1440.0
        assert space.parse_retention_days("86400s") == 1.0

    def test_invalid_units(self):
        with pytest.raises(ValueError, match="Nieznana jednostka retencji"):
            space.parse_retention_days("5years")

        with pytest.raises(ValueError, match="Nieprawidłowy format retencji"):
            space.parse_retention_days("invalid-retention")


class TestCleanupPoliciesMatrix:
    def test_policies_contain_required_targets(self):
        ids = {p["id"] for p in space.CLEANUP_POLICIES}
        assert "tmp" in ids
        assert "trash" in ids
        assert "thumbnails" in ids
        assert "docker-buildcache" in ids
        assert "docker-old" in ids
        assert "docker-networks" in ids

    def test_policy_fields_are_well_formed(self):
        for p in space.CLEANUP_POLICIES:
            assert "id" in p
            assert p["flag"].startswith("--")
            assert "name" in p
            assert isinstance(p["direct"], bool)
            assert "default_retention" in p
            assert p["risk_level"] in ("safe", "review", "dangerous")
            assert isinstance(p["default_safe"], bool)
            assert "description" in p
            assert "protected" in p
            assert "example" in p

    def test_display_cleanup_policies_table(self):
        result = _invoke(space._display_cleanup_policies, json_output=False)
        assert result.exit_code == 0
        assert "POLITYKA RETENCJI I BEZPOŚREDNIEGO CZYSZCZENIA" in result.output
        assert "--tmp" in result.output
        assert "--trash" in result.output
        assert "--thumbnails" in result.output

    def test_display_cleanup_policies_json(self):
        result = _invoke(space._display_cleanup_policies, json_output=True)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "policies" in data
        assert len(data["policies"]) >= 10
        tmp_pol = next(p for p in data["policies"] if p["id"] == "tmp")
        assert tmp_pol["flag"] == "--tmp"
        assert tmp_pol["direct"] is True


class TestTrashCleanup:
    def test_scan_trash_filtering(self, tmp_path):
        trash_dir = tmp_path / "Trash"
        files_dir = trash_dir / "files"
        info_dir = trash_dir / "info"
        files_dir.mkdir(parents=True)
        info_dir.mkdir(parents=True)

        now = time.time()
        old_time = now - 20 * 86400  # 20 days ago
        recent_time = now - 2 * 86400  # 2 days ago

        # Old file
        old_file = files_dir / "old_doc.pdf"
        old_file.write_text("old pdf content")
        os.utime(old_file, (old_time, old_time))
        old_info = info_dir / "old_doc.pdf.trashinfo"
        old_info.write_text("[Trash Info]\nPath=/home/tom/old_doc.pdf\n")

        # Recent file
        recent_file = files_dir / "recent.txt"
        recent_file.write_text("recent content")
        os.utime(recent_file, (recent_time, recent_time))
        recent_info = info_dir / "recent.txt.trashinfo"
        recent_info.write_text("[Trash Info]\nPath=/home/tom/recent.txt\n")

        # Scan with 14 days retention
        candidates = space._scan_trash(days=14.0, trash_dir=trash_dir)
        cand_names = [c["name"] for c in candidates]
        assert "old_doc.pdf" in cand_names
        assert "recent.txt" not in cand_names

    def test_cleanup_trash_dry_run_and_execution(self, tmp_path):
        trash_dir = tmp_path / "Trash"
        files_dir = trash_dir / "files"
        info_dir = trash_dir / "info"
        files_dir.mkdir(parents=True)
        info_dir.mkdir(parents=True)

        now = time.time()
        old_time = now - 20 * 86400

        old_file = files_dir / "stale.zip"
        old_file.write_text("zip data")
        os.utime(old_file, (old_time, old_time))
        old_info = info_dir / "stale.zip.trashinfo"
        old_info.write_text("[Trash Info]\nPath=/home/tom/stale.zip\n")

        # Dry run
        dry_res = _invoke(
            space._cleanup_trash,
            False,
            True,
            False,
            True,
            days=14.0,
            trash_dir=trash_dir,
        )
        assert dry_res.exit_code == 0
        assert "DRY-RUN" in dry_res.output
        assert old_file.exists()
        assert old_info.exists()

        # Real execution with yes
        exec_res = _invoke(
            space._cleanup_trash,
            False,
            False,
            False,
            True,
            days=14.0,
            trash_dir=trash_dir,
        )
        assert exec_res.exit_code == 0
        assert "usunięto" in exec_res.output
        assert not old_file.exists()
        assert not old_info.exists()


class TestThumbnailsCleanup:
    def test_scan_thumbnails_filtering(self, tmp_path):
        thumb_dir = tmp_path / "thumbnails"
        normal_dir = thumb_dir / "normal"
        large_dir = thumb_dir / "large"
        normal_dir.mkdir(parents=True)
        large_dir.mkdir(parents=True)

        now = time.time()
        old_time = now - 40 * 86400  # 40 days ago
        recent_time = now - 5 * 86400  # 5 days ago

        old_thumb1 = normal_dir / "abc123.png"
        old_thumb1.write_bytes(b"\x89PNG\r\n\x1a\n")
        os.utime(old_thumb1, (old_time, old_time))

        old_thumb2 = large_dir / "def456.png"
        old_thumb2.write_bytes(b"\x89PNG\r\n\x1a\n")
        os.utime(old_thumb2, (old_time, old_time))

        recent_thumb = normal_dir / "new.png"
        recent_thumb.write_bytes(b"\x89PNG\r\n\x1a\n")
        os.utime(recent_thumb, (recent_time, recent_time))

        candidates = space._scan_thumbnails(days=30.0, thumbnails_dir=thumb_dir)
        assert len(candidates) == 2  # normal and large categories
        all_paths = [p for c in candidates for p in c["paths"]]
        assert old_thumb1 in all_paths
        assert old_thumb2 in all_paths
        assert recent_thumb not in all_paths

    def test_cleanup_thumbnails_execution(self, tmp_path):
        thumb_dir = tmp_path / "thumbnails"
        normal_dir = thumb_dir / "normal"
        normal_dir.mkdir(parents=True)

        now = time.time()
        old_time = now - 40 * 86400

        old_thumb = normal_dir / "cached.png"
        old_thumb.write_bytes(b"\x89PNG\r\n\x1a\n")
        os.utime(old_thumb, (old_time, old_time))

        # Dry run
        dry_res = _invoke(
            space._cleanup_thumbnails,
            False,
            True,
            False,
            True,
            days=30.0,
            thumbnails_dir=thumb_dir,
        )
        assert dry_res.exit_code == 0
        assert "DRY-RUN" in dry_res.output
        assert old_thumb.exists()

        # Execute
        exec_res = _invoke(
            space._cleanup_thumbnails,
            False,
            False,
            False,
            True,
            days=30.0,
            thumbnails_dir=thumb_dir,
        )
        assert exec_res.exit_code == 0
        assert "usunięto" in exec_res.output
        assert not old_thumb.exists()


class FakeScanner:
    threshold_mb = 100

    def __init__(self):
        self.SERVICE_PATHS = {}

    def scan_all_services(self):
        return []

    def scan_service(self, service_type):
        return []


class TestServiceCleanerRetention:
    def test_cleaner_trash_and_thumbnails_methods(self, tmp_path):
        cleaner = ServiceCleaner(FakeScanner())

        trash_dir = tmp_path / "Trash"
        files_dir = trash_dir / "files"
        files_dir.mkdir(parents=True)

        now = time.time()
        old_file = files_dir / "abandoned.log"
        old_file.write_text("log content")
        os.utime(old_file, (now - 20 * 86400, now - 20 * 86400))

        candidates = cleaner.scan_trash_candidates(days=14.0, trash_dir=trash_dir)
        assert len(candidates) == 1

        dry_res = cleaner.cleanup_trash(days=14.0, dry_run=True, trash_dir=trash_dir)
        assert dry_res["success"] is True
        assert "[DRY RUN]" in dry_res["output"]
        assert old_file.exists()

        exec_res = cleaner.cleanup_trash(days=14.0, dry_run=False, trash_dir=trash_dir)
        assert exec_res["success"] is True
        assert not old_file.exists()

        # Thumbnails
        thumb_dir = tmp_path / "thumbnails"
        normal_dir = thumb_dir / "normal"
        normal_dir.mkdir(parents=True)
        old_thumb = normal_dir / "old.png"
        old_thumb.write_bytes(b"\x89PNG\r\n\x1a\n")
        os.utime(old_thumb, (now - 45 * 86400, now - 45 * 86400))

        t_candidates = cleaner.scan_thumbnails_candidates(days=30.0, thumbnails_dir=thumb_dir)
        assert len(t_candidates) == 1

        t_dry = cleaner.cleanup_thumbnails(days=30.0, dry_run=True, thumbnails_dir=thumb_dir)
        assert t_dry["success"] is True
        assert "[DRY RUN]" in t_dry["output"]
        assert old_thumb.exists()

        t_exec = cleaner.cleanup_thumbnails(days=30.0, dry_run=False, thumbnails_dir=thumb_dir)
        assert t_exec["success"] is True
        assert not old_thumb.exists()

    def test_cleaner_build_safe_age_actions_includes_trash_and_thumbnails(self, monkeypatch):
        cleaner = ServiceCleaner(FakeScanner())

        monkeypatch.setattr(
            cleaner,
            "scan_trash_candidates",
            lambda days=14.0: [{"name": "item", "size_bytes": 1024 * 1024}],
        )
        monkeypatch.setattr(
            cleaner,
            "scan_thumbnails_candidates",
            lambda days=30.0: [{"name": "normal", "items_count": 5, "size_bytes": 2 * 1024 * 1024}],
        )

        actions = cleaner.build_safe_age_actions()
        kinds = [a["cleanup_kind"] for a in actions]
        assert "trash" in kinds
        assert "thumbnails" in kinds


class TestCliRetentionAndPolicyOptions:
    def test_cli_policy_flag(self):
        runner = CliRunner()
        result = runner.invoke(cleanup_cmd.cleanup_services, ["--policy"])
        assert result.exit_code == 0
        assert "POLITYKA RETENCJI" in result.output

    def test_cli_policy_json_flag(self):
        runner = CliRunner()
        result = runner.invoke(cleanup_cmd.cleanup_services, ["--policy", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "policies" in data

    def test_cli_trash_flag(self):
        runner = CliRunner()
        result = runner.invoke(cleanup_cmd.cleanup_services, ["--trash", "--list"])
        assert result.exit_code == 0

    def test_cli_thumbnails_flag(self):
        runner = CliRunner()
        result = runner.invoke(cleanup_cmd.cleanup_services, ["--thumbnails", "--list"])
        assert result.exit_code == 0

    def test_cli_tmp_with_retention_flag(self):
        runner = CliRunner()
        result = runner.invoke(
            cleanup_cmd.cleanup_services, ["--tmp", "--retention", "24h", "--list"]
        )
        assert result.exit_code == 0

    def test_cli_tmp_with_hours_flag(self):
        runner = CliRunner()
        result = runner.invoke(
            cleanup_cmd.cleanup_services, ["--tmp", "--hours", "12", "--list"]
        )
        assert result.exit_code == 0
