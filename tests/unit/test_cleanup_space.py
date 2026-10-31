"""Tests for fixos.cli._cleanup_space disk-reclaim handlers."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from fixos.cli import _cleanup_space as space
from fixos.cli import cleanup_cmd


def _cp(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def _invoke(fn, *args, input_text=""):
    @click.command()
    def command():
        fn(*args)

    return CliRunner().invoke(command, input=input_text)


# ── snap ─────────────────────────────────────────────────────────────────

SNAP_LIST = (
    "Name       Version  Rev   Tracking       Publisher   Notes\n"
    "core22     20240101 1122  latest/stable  canonical** -\n"
    "core22     20240201 1380  latest/stable  canonical** disabled\n"
    "firefox    130.0    5000  latest/stable  mozilla**   -\n"
    "firefox    129.0    4900  latest/stable  mozilla**   disabled\n"
)


def _snap_runner(calls):
    def runner(argv, timeout=60):
        calls.append(list(argv))
        if argv[:3] == ["snap", "list", "--all"]:
            return _cp(stdout=SNAP_LIST)
        return _cp(stdout="")

    return runner


def test_snap_old_lists_only_disabled_revisions(monkeypatch, tmp_path):
    monkeypatch.setattr(space, "_run_cmd", _snap_runner([]))
    result = _invoke(
        space._cleanup_snap_old, False, False, True, False
    )
    assert result.exit_code == 0
    assert "core22 (rewizja 1380)" in result.output
    assert "firefox (rewizja 4900)" in result.output
    assert "rewizja 1122" not in result.output
    assert "rewizja 5000" not in result.output


def test_snap_old_removes_selected_via_snap_remove(monkeypatch):
    calls = []
    monkeypatch.setattr(space, "_run_cmd", _snap_runner(calls))
    result = _invoke(
        space._cleanup_snap_old, False, False, False, False,
        input_text="1\ny\n",
    )
    assert result.exit_code == 0
    assert ["sudo", "snap", "remove", "core22", "--revision", "1380"] in calls


def test_snap_old_dry_run_never_removes(monkeypatch):
    calls = []
    monkeypatch.setattr(space, "_run_cmd", _snap_runner(calls))
    result = _invoke(
        space._cleanup_snap_old, False, True, False, False,
        input_text="all\n",
    )
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output
    assert not any(c[:2] == ["sudo", "snap"] for c in calls)


def test_snap_old_json(monkeypatch):
    monkeypatch.setattr(space, "_run_cmd", _snap_runner([]))
    result = _invoke(space._cleanup_snap_old, True, False, False, False)
    assert result.exit_code == 0
    assert '"description": "core22 (rewizja 1380)"' in result.output


# ── journal ──────────────────────────────────────────────────────────────


def test_journal_reports_usage_and_vacuums(monkeypatch):
    calls = []

    def runner(argv, timeout=60):
        calls.append(list(argv))
        if argv == ["journalctl", "--disk-usage"]:
            return _cp(
                stdout="Archived and active journals take up 5.9G in the file system.\n"
            )
        return _cp(stdout="Vacuuming done, freed 4G\n")

    monkeypatch.setattr(space, "_run_cmd", runner)
    result = _invoke(
        space._cleanup_journal, False, False, False, False,
        input_text="200M\ny\n",
    )
    assert result.exit_code == 0
    assert "5.9G" in result.output
    assert ["sudo", "journalctl", "--vacuum-size=200M"] in calls


def test_journal_dry_run_shows_command_only(monkeypatch):
    calls = []

    def runner(argv, timeout=60):
        calls.append(list(argv))
        return _cp(stdout="Archived and active journals take up 1G in the file system.\n")

    monkeypatch.setattr(space, "_run_cmd", runner)
    result = _invoke(space._cleanup_journal, False, True, False, True)
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output
    assert not any(c[0] == "sudo" for c in calls)


# ── user cache ────────────────────────────────────────────────────────────


def _fake_dir_size(sizes):
    def measure(path):
        return sizes.get(str(path), 0)

    return measure


def test_user_cache_yes_removes_only_known_safe(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cache = home / ".cache"
    for name in ("pip", "uv", "strange-app"):
        (cache / name).mkdir(parents=True)
        (cache / name / "blob").write_text("x")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(
        space, "_dir_size", _fake_dir_size({str(cache / n): 100 for n in ("pip", "uv", "strange-app")})
    )
    result = _invoke(space._cleanup_user_cache, False, False, False, True)
    assert result.exit_code == 0
    assert not (cache / "pip").exists()
    assert not (cache / "uv").exists()
    assert (cache / "strange-app").exists()
    assert "pomija 1 pozycji" in result.output


def test_user_cache_manual_selection_removes_unsafe(monkeypatch, tmp_path):
    home = tmp_path / "home"
    cache = home / ".cache"
    (cache / "weird").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(space, "_dir_size", _fake_dir_size({str(cache / "weird"): 50}))
    result = _invoke(
        space._cleanup_user_cache, False, False, False, False,
        input_text="1\ny\n",
    )
    assert result.exit_code == 0
    assert not (cache / "weird").exists()


# ── jetbrains ─────────────────────────────────────────────────────────────


def test_jetbrains_keeps_newest_toolbox_channel(monkeypatch, tmp_path):
    home = tmp_path / "home"
    apps = home / ".local/share/JetBrains/Toolbox/apps/PyCharm"
    for ch in ("ch-0", "ch-1", "ch-2"):
        (apps / ch).mkdir(parents=True)
    cache = home / ".cache/JetBrains/PyCharm2025.1"
    cache.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    sizes = {str(apps / "ch-0"): 10, str(apps / "ch-1"): 20, str(apps / "ch-2"): 30, str(cache): 5}
    monkeypatch.setattr(space, "_dir_size", _fake_dir_size(sizes))
    result = _invoke(space._cleanup_jetbrains, False, False, True, False)
    assert result.exit_code == 0
    assert "PyCharm ch-0" in result.output
    assert "PyCharm ch-1" in result.output
    assert "ch-2" not in result.output
    assert "LocalHistory" in result.output


@pytest.mark.parametrize("cache_name", ["PyCharm2026.3", "unknown-system-data"])
def test_jetbrains_yes_preserves_system_cache_and_local_history(
    monkeypatch, tmp_path, cache_name
):
    home = tmp_path / "home"
    apps = home / ".local/share/JetBrains/Toolbox/apps/PyCharm"
    for channel in ("ch-0", "ch-1", "ch-2"):
        (apps / channel).mkdir(parents=True)
    history = home / ".cache/JetBrains" / cache_name / "LocalHistory/revisions.bin"
    history.parent.mkdir(parents=True)
    history.write_bytes(b"only local revision")
    download = home / ".cache/JetBrains/Toolbox/download/installer.tar.gz"
    download.parent.mkdir(parents=True)
    download.write_bytes(b"toolbox state")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(space, "_dir_size", lambda _path: 10)

    result = _invoke(space._cleanup_jetbrains, False, False, False, True)

    assert result.exit_code == 0, result.output
    assert history.read_bytes() == b"only local revision"
    assert download.read_bytes() == b"toolbox state"
    assert not (apps / "ch-0").exists()
    assert not (apps / "ch-1").exists()
    assert (apps / "ch-2").is_dir()


def test_jetbrains_json_does_not_offer_bulk_system_cache(monkeypatch, tmp_path):
    cache_root = tmp_path / ".cache/JetBrains"
    (cache_root / "PyCharm2026.3/LocalHistory").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(space, "_dir_size", lambda _path: 10)

    result = _invoke(space._cleanup_jetbrains, True, False, False, True)

    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert not any(
        Path(item["path"]).is_relative_to(cache_root)
        for item in plan["candidates"]
    )
    assert "LocalHistory" in " ".join(plan["advisories"])


# ── libvirt ───────────────────────────────────────────────────────────────


def _virsh_runner(attached: list[str], domains=("vm1",), fail=False):
    def runner(argv, timeout=60):
        if fail:
            return _cp(returncode=1, stderr="no virsh")
        if argv[:3] == ["virsh", "-c", "qemu:///system"]:
            return _cp(returncode=1, stderr="denied")
        if argv[3:] == ["list", "--all", "--name"]:
            return _cp(stdout="\n".join(domains) + "\n")
        if "domblklist" in argv:
            lines = ["Type   Device   Target   Source", "-" * 40]
            lines += [f"file   disk     vda      {src}" for src in attached]
            return _cp(stdout="\n".join(lines) + "\n")
        return _cp(stdout="")

    return runner


def test_libvirt_excludes_attached_disks(monkeypatch, tmp_path):
    home = tmp_path / "home"
    images = home / ".local/share/libvirt/images"
    images.mkdir(parents=True)
    used = images / "used.qcow2"
    free = images / "free.qcow2"
    used.write_bytes(b"1")
    free.write_bytes(b"2")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(space, "_run_cmd", _virsh_runner([str(used)]))
    result = _invoke(space._cleanup_libvirt, False, False, True, False)
    assert result.exit_code == 0
    assert "free.qcow2" in result.output
    assert "used.qcow2" not in result.output


def test_libvirt_without_virsh_never_auto_removes(monkeypatch, tmp_path):
    home = tmp_path / "home"
    images = home / ".local/share/libvirt/images"
    images.mkdir(parents=True)
    (images / "orphan.qcow2").write_bytes(b"x")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(space, "_run_cmd", _virsh_runner([], fail=True))
    result = _invoke(space._cleanup_libvirt, False, False, False, True)
    assert result.exit_code == 0
    assert (images / "orphan.qcow2").exists()
    assert "Nie udało się zweryfikować" in result.output


# ── gitive ────────────────────────────────────────────────────────────────


def test_gitive_protects_container_bound_workspace(monkeypatch, tmp_path):
    home = tmp_path / "home"
    root = home / ".local/share/gitive-isolated/github/.digitaltwin"
    bound = root / "atlas-api-278b89df/rootfs"
    loose = root / "old-proj-deadbeef/rootfs"
    bound.mkdir(parents=True)
    loose.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(
        space,
        "_dir_size",
        _fake_dir_size({str(bound.parent): 10, str(loose.parent): 20}),
    )
    monkeypatch.setattr(
        space,
        "_gitive_container_names",
        lambda: {"gitive-project-atlas-api-278b89df"},
    )
    result = _invoke(space._cleanup_gitive, False, False, False, True)
    assert result.exit_code == 0
    assert bound.parent.exists()
    assert not loose.parent.exists()


# ── CLI routing ───────────────────────────────────────────────────────────


def test_cli_routes_snap_old_flag(monkeypatch):
    called = []
    monkeypatch.setattr(
        cleanup_cmd, "_cleanup_snap_old", lambda *a: called.append(a)
    )
    result = CliRunner().invoke(cleanup_cmd.cleanup_services, ["--snap-old"])
    assert result.exit_code == 0
    assert called == [(False, False, False, False)]


def test_cli_routes_cleanup_alias_gitive(monkeypatch):
    called = []
    monkeypatch.setattr(
        cleanup_cmd, "_cleanup_gitive", lambda *a: called.append(a)
    )
    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services, ["-c", "gitive", "--list"]
    )
    assert result.exit_code == 0
    assert called == [(False, False, True, False)]


def test_cli_rejects_combined_space_actions(monkeypatch):
    monkeypatch.setattr(space, "_run_cmd", _snap_runner([]))
    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services, ["--snap-old", "--journal"]
    )
    assert result.exit_code == 0
    assert "osobną, pojedynczą akcję" in result.output


def test_cli_rejects_space_flag_with_foreign_cleanup(monkeypatch):
    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services, ["--snap-old", "-c", "docker"]
    )
    assert result.exit_code == 0
    assert "osobną, pojedynczą akcję" in result.output


# ── unused projects (> 7 days) ────────────────────────────────────────────


def _make_unused_project(base: Path, name: str, age_days: float) -> Path:

    proj = base / name
    (proj / ".git").mkdir(parents=True)
    (proj / "pyproject.toml").write_text("[project]\nname='demo'\n")
    (proj / "package.json").write_text("{}")
    (proj / "src").mkdir()
    (proj / "src" / "main.py").write_text("print('hi')\n")
    venv = proj / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")
    (venv / "blob.bin").write_bytes(b"a" * 4096)
    node_modules = proj / "node_modules"
    node_modules.mkdir()
    (node_modules / "pkg.js").write_bytes(b"b" * 2048)
    dist = proj / "dist"
    dist.mkdir()
    (dist / "bundle.js").write_bytes(b"c" * 1024)

    stamp = time.time() - age_days * 86400.0
    for root, dirs, files in os.walk(proj):
        for entry in files + dirs:
            os.utime(Path(root) / entry, (stamp, stamp), follow_symlinks=False)
    os.utime(proj, (stamp, stamp))
    return proj


def test_projects_old_reclaims_only_unused_7d_safe_artifacts(monkeypatch, tmp_path):

    from fixos.diagnostics import venv_cleanup as vc

    monkeypatch.setattr(vc, "active_paths", lambda: (set(), []))
    monkeypatch.setenv("FIXOS_NATIVE", "off")

    stale_proj = _make_unused_project(tmp_path, "stale-app", age_days=10)
    fresh_proj = _make_unused_project(tmp_path, "fresh-app", age_days=10)
    now = time.time()
    os.utime(fresh_proj / "src" / "main.py", (now, now))

    active_proj = _make_unused_project(tmp_path, "active-app", age_days=12)
    monkeypatch.setattr(
        vc, "active_paths", lambda: ({active_proj / ".venv" / "bin" / "python"}, [])
    )

    candidates = space._scan_unused_projects(days=7, base_dir=tmp_path)
    paths = {c["path"] for c in candidates}
    assert paths == {
        stale_proj / ".venv",
        stale_proj / "node_modules",
    }
    # dist is 'review' risk, never selected in safe auto cleanup
    assert (stale_proj / "dist") not in paths

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--projects-old", "--projects-path", str(tmp_path), "--yes"],
    )
    assert result.exit_code == 0, result.output
    assert not (stale_proj / ".venv").exists()
    assert not (stale_proj / "node_modules").exists()
    assert (stale_proj / "dist" / "bundle.js").is_file()
    assert (stale_proj / "src" / "main.py").is_file()
    assert (fresh_proj / ".venv").is_dir()
    assert (active_proj / ".venv").is_dir()


def test_project_artifact_allowed_validation(tmp_path, monkeypatch):
    proj = tmp_path / "myproj"
    proj.mkdir()
    (proj / ".git").mkdir()
    (proj / "node_modules").mkdir()
    (proj / "src").mkdir()
    (proj / "file.txt").write_text("hello")

    # Valid artifact
    assert space._project_artifact_allowed(proj / "node_modules", proj) is True
    # Dict input
    assert space._project_artifact_allowed({"path": proj / "node_modules", "project": proj}) is True
    assert space._project_artifact_allowed({"path": proj / "node_modules"}) is True

    # Project root itself
    assert space._project_artifact_allowed(proj, proj) is False
    # Parent of project root
    assert space._project_artifact_allowed(proj.parent, proj) is False
    # Regular file
    assert space._project_artifact_allowed(proj / "file.txt", proj) is False
    # Forbidden .git directory
    assert space._project_artifact_allowed(proj / ".git", proj) is False
    # Non-existent directory
    assert space._project_artifact_allowed(proj / "nonexistent", proj) is False

    # Direct symlink
    sym = proj / "symlink_art"
    sym.symlink_to(tmp_path)
    assert space._project_artifact_allowed(sym, proj) is False

    # Symlink pointing inside project
    sym_inside = proj / "symlink_inside"
    sym_inside.symlink_to(proj / "node_modules")
    assert space._project_artifact_allowed(sym_inside, proj) is False

    # Intermediate symlink directory
    sym_parent = proj / "sym_parent"
    real_target = tmp_path / "real_target"
    real_target.mkdir()
    (real_target / "nested_art").mkdir()
    sym_parent.symlink_to(real_target)
    assert space._project_artifact_allowed(sym_parent / "nested_art", proj) is False

    # Mount point checks
    orig_is_mount = Path.is_mount
    monkeypatch.setattr(
        Path, "is_mount", lambda p: p == (proj / "node_modules") or orig_is_mount(p)
    )
    assert space._project_artifact_allowed(proj / "node_modules", proj) is False

    # Child mount point inside artifact
    child_dir = proj / "node_modules" / "submount"
    child_dir.mkdir(parents=True)
    monkeypatch.setattr(
        Path, "is_mount", lambda p: p == child_dir or orig_is_mount(p)
    )
    assert space._project_artifact_allowed(proj / "node_modules", proj) is False


def test_projects_old_permission_error_with_sudo_success(monkeypatch, tmp_path):
    from fixos.diagnostics import venv_cleanup as vc

    monkeypatch.setattr(vc, "active_paths", lambda: (set(), []))
    monkeypatch.setenv("FIXOS_NATIVE", "off")

    stale_proj = _make_unused_project(tmp_path, "stale-app", age_days=10)
    target_art = stale_proj / "node_modules"

    orig_rmtree = shutil.rmtree

    def mock_rmtree(path, *args, **kwargs):
        if Path(path) == target_art:
            raise PermissionError(f"[Errno 13] Permission denied: '{path}'")
        return orig_rmtree(path, *args, **kwargs)

    calls = []

    def runner(argv, timeout=60):
        calls.append(list(argv))
        if argv[:4] == ["sudo", "-n", "rm", "-rf"]:
            orig_rmtree(target_art, ignore_errors=True)
            return _cp(stdout="", returncode=0)
        return _cp(stdout="")

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/sudo" if cmd == "sudo" else None)
    monkeypatch.setattr(space, "_run_cmd", runner)

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--projects-old", "--projects-path", str(tmp_path), "--yes"],
    )
    assert result.exit_code == 0, result.output
    assert any(
        c[:4] == ["sudo", "-n", "rm", "-rf"] and str(target_art) in c
        for c in calls
    )
    assert "Usunięto przez sudo (projekty)" in result.output
    assert not target_art.exists()
    assert not (stale_proj / ".venv").exists()


def test_projects_old_permission_error_without_sudo_reports_and_remediates(monkeypatch, tmp_path):
    from fixos.diagnostics import venv_cleanup as vc

    monkeypatch.setattr(vc, "active_paths", lambda: (set(), []))
    monkeypatch.setenv("FIXOS_NATIVE", "off")

    stale_proj = _make_unused_project(tmp_path, "stale-app", age_days=10)
    target_art = stale_proj / "node_modules"

    orig_rmtree = shutil.rmtree

    def mock_rmtree(path, *args, **kwargs):
        if Path(path) == target_art:
            raise PermissionError(f"[Errno 13] Permission denied: '{path}'")
        return orig_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--projects-old", "--projects-path", str(tmp_path), "--yes"],
    )
    assert "Brak uprawnień (PermissionError)" in result.output
    assert "node_modules" in result.output
    assert "Polecenie naprawcze" in result.output
    assert f"sudo rm -rf -- '{target_art}'" in result.output or f"sudo rm -rf -- {target_art}" in result.output


def test_projects_old_permission_error_sudo_fails_reports_and_remediates(monkeypatch, tmp_path):
    from fixos.diagnostics import venv_cleanup as vc

    monkeypatch.setattr(vc, "active_paths", lambda: (set(), []))
    monkeypatch.setenv("FIXOS_NATIVE", "off")

    stale_proj = _make_unused_project(tmp_path, "stale-app", age_days=10)
    target_art = stale_proj / "node_modules"

    orig_rmtree = shutil.rmtree

    def mock_rmtree(path, *args, **kwargs):
        if Path(path) == target_art:
            raise PermissionError(f"[Errno 13] Permission denied: '{path}'")
        return orig_rmtree(path, *args, **kwargs)

    calls = []

    def runner(argv, timeout=60):
        calls.append(list(argv))
        if argv[:4] == ["sudo", "-n", "rm", "-rf"]:
            return _cp(returncode=1, stderr="sudo: a password is required")
        return _cp(stdout="")

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/sudo" if cmd == "sudo" else None)
    monkeypatch.setattr(space, "_run_cmd", runner)

    result = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--projects-old", "--projects-path", str(tmp_path), "--yes"],
    )
    assert any(
        c[:4] == ["sudo", "-n", "rm", "-rf"] and str(target_art) in c
        for c in calls
    )
    assert "Brak uprawnień (PermissionError)" in result.output
    assert "Polecenie naprawcze" in result.output
    assert f"sudo rm -rf -- {target_art}" in result.output or f"sudo rm -rf -- '{target_art}'" in result.output


def test_projects_old_permission_error_never_sudo_removes_unallowed_artifacts(monkeypatch, tmp_path):
    proj = tmp_path / "demo_proj"
    proj.mkdir()
    sym_art = proj / "node_modules"
    sym_art.symlink_to(tmp_path)

    calls = []
    monkeypatch.setattr(space, "_run_cmd", lambda argv, timeout=60: (calls.append(list(argv)), _cp())[1])

    candidates = [
        {
            "description": "demo/node_modules (node)",
            "path": sym_art,
            "project": proj,
            "artifact_name": "node_modules",
            "size_bytes": 1024,
        }
    ]

    monkeypatch.setattr(space, "_remove_path", lambda p: (False, "PERMISSION_DENIED:[Errno 13] Permission denied"))

    space._remove_selected(candidates, [0])

    assert not any(c[:2] == ["sudo", "-n"] for c in calls)


