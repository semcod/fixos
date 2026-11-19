"""Cross-platform integration tests for quick scan, cache classification, and Windows/macOS portability."""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from click.testing import CliRunner

from fixos import mcp_receipts, poa_grants
from fixos.cli.quick_cmd import quick as quick_cli
from fixos.diagnostics import cache_discovery, quick_snapshot
from fixos.diagnostics.service_scanner import ServiceType


def _write_blob(directory: Path, name: str = "blob.bin", size_bytes: int = 8192) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_bytes(b"x" * size_bytes)
    return target


class TestLiveHostNativeQuickScanIntegration:
    """Runs unmocked on the native runner OS (Linux, macOS, and Windows in CI)."""

    def test_live_quick_snapshot_and_cli_json_on_native_host(self, tmp_path):
        state_dir = tmp_path / "state"
        home_dir = tmp_path / "home"
        sys_name = platform.system()

        if sys_name == "Darwin":
            pip_dir = home_dir / "Library" / "Caches" / "pip"
            jb_dir = home_dir / "Library" / "Caches" / "JetBrains" / "IdeaIC2026"
        elif sys_name == "Windows":
            pip_dir = home_dir / "AppData" / "Local" / "pip" / "Cache"
            jb_dir = home_dir / "AppData" / "Local" / "JetBrains" / "IdeaIC2026"
        else:
            pip_dir = home_dir / ".cache" / "pip"
            jb_dir = home_dir / ".cache" / "JetBrains" / "IdeaIC2026"

        _write_blob(pip_dir, size_bytes=16384)
        _write_blob(jb_dir, size_bytes=32768)

        snap = quick_snapshot.collect_quick_snapshot(
            state_dir=state_dir,
            home=home_dir,
            cwd=tmp_path,
            save=True,
        )
        assert snap["$schema"] == "fixos-quick-snapshot-v1"
        assert snap["context"]["os"] == sys_name
        assert (state_dir / "quick-history.json").is_file()

        safe_ids = {item["id"] for item in snap["safe_reclaim"]["items"]}
        review_ids = {item["id"] for item in snap["review"]}
        assert "pip" in safe_ids
        assert "jetbrains" in review_ids
        assert "jetbrains" not in safe_ids

        runner = CliRunner()
        env = dict(os.environ)
        env["FIXOS_STATE_DIR"] = str(state_dir)
        res = runner.invoke(quick_cli, ["--json", "--no-save"], env=env)
        assert res.exit_code == 0, res.output
        cli_payload = json.loads(res.output)
        assert cli_payload["$schema"] == "fixos-quick-snapshot-v1"
        assert cli_payload["resources"]["disk"]["total_bytes"] > 0


class TestMacOsAndWindowsCacheClassification:
    """Verify cache rules and generic/Electron cache classification for Darwin and Windows."""

    def test_macos_library_caches_and_application_support_electron_classification(
        self, monkeypatch, tmp_path
    ):
        home = tmp_path / "Users" / "dev"
        lib_caches = home / "Library" / "Caches"
        app_support = home / "Library" / "Application Support"

        # Rebuildable bundle cache under ~/Library/Caches
        _write_blob(lib_caches / "com.custom.buildtool")
        # Protected Apple system caches must be skipped
        _write_blob(lib_caches / "com.apple.Safari")
        _write_blob(lib_caches / "CloudKit")
        # Dedicated scanner cache (pip) must be skipped by generic discovery
        _write_blob(lib_caches / "pip")
        # Electron cache under ~/Library/Application Support/Linear/Cache
        _write_blob(app_support / "Linear" / "Cache")
        # Non-cache Application Support user data must NEVER be picked up
        _write_blob(app_support / "Linear" / "Local Storage" / "leveldb")
        _write_blob(app_support / "Obsidian" / "vaults")

        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setattr(
            cache_discovery.os.path,
            "expanduser",
            lambda p: p.replace("~", str(home)),
        )

        discovered = cache_discovery.discover_additional_caches(
            get_size_mb=lambda _p: 1500.0,
            threshold_mb=500,
            covered_paths=set(),
            system_name="Darwin",
        )
        by_name = {item.name: item for item in discovered}
        assert "Cache: com.custom.buildtool" in by_name
        assert by_name["Cache: com.custom.buildtool"].safe_to_cleanup is True
        assert "Linear cache" in by_name
        assert by_name["Linear cache"].service_type == ServiceType.ELECTRON
        assert by_name["Linear cache"].safe_to_cleanup is True

        discovered_paths = {Path(item.path) for item in discovered}
        assert (lib_caches / "com.apple.Safari") not in discovered_paths
        assert (lib_caches / "CloudKit") not in discovered_paths
        assert (lib_caches / "pip") not in discovered_paths
        assert not any("Obsidian" in str(p) for p in discovered_paths)
        assert not any("Local Storage" in str(p) for p in discovered_paths)

    def test_windows_localappdata_and_appdata_strict_cache_classification(
        self, monkeypatch, tmp_path
    ):
        home = tmp_path / "Users" / "winuser"
        local_app = home / "AppData" / "Local"
        roaming_app = home / "AppData" / "Roaming"

        # Explicit cache directory & <App>/Cache under %LOCALAPPDATA%
        _write_blob(local_app / "custom-shader-cache")
        _write_blob(local_app / "Figma" / "Cache")
        # Non-cache app state under %LOCALAPPDATA% must NOT be selected!
        _write_blob(local_app / "Figma" / "settings")
        _write_blob(local_app / "MyDatabaseApp" / "data")
        _write_blob(local_app / "Programs" / "Python")
        _write_blob(local_app / "Packages" / "CanonicalGroupLimited")
        # Electron GPUCache under %APPDATA%
        _write_blob(roaming_app / "Postman" / "GPUCache")

        monkeypatch.setenv("LOCALAPPDATA", str(local_app))
        monkeypatch.setenv("APPDATA", str(roaming_app))
        monkeypatch.setattr(
            cache_discovery.os.path,
            "expanduser",
            lambda p: p.replace("~", str(home)),
        )

        discovered = cache_discovery.discover_additional_caches(
            get_size_mb=lambda _p: 1500.0,
            threshold_mb=500,
            covered_paths=set(),
            system_name="Windows",
        )
        names = {item.name for item in discovered}
        paths = {Path(item.path) for item in discovered}

        assert "Cache: custom-shader-cache" in names
        assert "Cache: Figma" in names or "Figma cache" in names
        assert "Postman cache" in names
        assert (local_app / "MyDatabaseApp") not in paths
        assert (local_app / "MyDatabaseApp" / "data") not in paths
        assert not any("Programs" in str(p) for p in paths)
        assert not any("Packages" in str(p) for p in paths)
        assert not any("settings" in str(p) for p in paths)

    def test_windows_and_macos_quick_snapshot_rules_and_covered_paths(
        self, monkeypatch, tmp_path
    ):
        assert cache_discovery.is_generic_cache_safe(r"C:\Users\dev\AppData\Local\foo-cache\\")
        assert not cache_discovery.is_generic_cache_safe(r"C:\Users\dev\AppData\Local\MyAppData\\")

        win_home = tmp_path / "winhome"
        _write_blob(win_home / "AppData" / "Local" / "Yarn" / "Cache", size_bytes=4096)
        _write_blob(win_home / "AppData" / "Local" / "pypoetry" / "Cache", size_bytes=4096)
        _write_blob(win_home / "AppData" / "Local" / "pnpm" / "store", size_bytes=4096)
        _write_blob(win_home / "AppData" / "Local" / "ms-playwright", size_bytes=4096)

        snap = quick_snapshot.collect_quick_snapshot(
            state_dir=tmp_path / "winstate",
            home=win_home,
            cwd=tmp_path,
            save=False,
        )
        safe_ids = {item["id"] for item in snap["safe_reclaim"]["items"]}
        review_ids = {item["id"] for item in snap["review"]}
        assert {"yarn", "poetry", "pnpm"} <= safe_ids
        assert "playwright" in review_ids

        # State/cache path defaults per OS when XDG vars are unset
        monkeypatch.delenv("FIXOS_STATE_DIR", raising=False)
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(win_home / "AppData" / "Local"))
        monkeypatch.setattr(quick_snapshot.platform, "system", lambda: "Windows")
        assert "AppData" in str(quick_snapshot._state_dir())
        assert "AppData" in str(quick_snapshot._docker_cache_path())

        monkeypatch.setattr(quick_snapshot.platform, "system", lambda: "Darwin")
        assert "Library" in str(quick_snapshot._state_dir())
        assert "Library" in str(quick_snapshot._docker_cache_path())


class TestPortableLockingFallbackWithoutFcntl:
    """Verify MCP receipts and POA grants remain functional when fcntl is unavailable."""

    def test_mcp_receipt_and_poa_grant_work_when_fcntl_is_none(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(mcp_receipts, "fcntl", None)
        monkeypatch.setattr(poa_grants, "fcntl", None)

        receipt_path = tmp_path / "receipts" / "test.json"
        mcp_receipts.atomic_write_json(receipt_path, {"ok": True})
        assert json.loads(receipt_path.read_text(encoding="utf-8")) == {"ok": True}

        with mcp_receipts._single_flight_lock(tmp_path / "locks", "req-win-01"):
            assert (tmp_path / "locks" / "req-win-01.lock").exists()

        plan = poa_grants.compile_poa_plan(
            operation_id="fixos://cleanup/auto",
            registry_digest="a" * 64,
            normalized_input={"categories": ["pip"], "dry_run": False},
            target={"host": "local", "categories": ["pip"]},
            effects=["local_write"],
            observation={"free_gb": 20.0},
        )
        grant = poa_grants.issue_poa_grant(plan, store_dir=tmp_path / "grants")
        consumed = poa_grants.verify_and_consume_poa_grant(
            grant_id=grant["grantId"],
            plan_hash=plan["plan_hash"],
            operation_id="fixos://cleanup/auto",
            caller_registry_digest="a" * 64,
            current_registry_digest="a" * 64,
            normalized_input={"categories": ["pip"], "dry_run": False},
            target={"host": "local", "categories": ["pip"]},
            store_dir=tmp_path / "grants",
        )
        assert consumed["grantId"] == grant["grantId"]
