"""Destructive cleanup contract exercised only against disposable fixtures."""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from fixos.cli.cleanup_cmd import cleanup_services
from fixos.diagnostics import native_scan as ns
from fixos.diagnostics import venv_cleanup as vc

_REAL_ACTIVE_PATHS = vc.active_paths


@pytest.fixture(autouse=True)
def isolated_observation(monkeypatch):
    monkeypatch.setattr(vc, "active_paths", lambda: (set(), []))
    monkeypatch.setenv("FIXOS_NATIVE", "off")


def age(path, days=45):
    timestamp = time.time_ns() - days * 86400 * 10**9
    for root, dirs, files in os.walk(path):
        for name in files + dirs:
            os.utime(
                Path(root) / name, ns=(timestamp, timestamp), follow_symlinks=False
            )
    os.utime(path, ns=(timestamp, timestamp))


def project(base, name="old", env=".venv"):
    root = base / name
    (root / env / "lib").mkdir(parents=True)
    (root / "pyproject.toml").write_text("")
    (root / "src").mkdir()
    (root / "src/app.py").write_text("print('hello')")
    (root / env / "pyvenv.cfg").write_text("home = /usr/bin")
    (root / env / "lib/package.py").write_bytes(b"x" * 8192)
    age(root)
    return root


def args(base, *extra):
    return ["--venvs-old", "--projects-path", str(base), *extra]


def test_inventory_counts_all_sizes_and_both_env_names(tmp_path):
    p = project(tmp_path)
    q = project(tmp_path, "other", "venv")
    result = vc.scan_venvs(tmp_path)
    assert result["found"] == result["eligible"] == 2
    assert result["bytes"] == sum(
        ns.measure_python(x)["bytes"] for x in (p / ".venv", q / "venv")
    )


@pytest.mark.parametrize(
    "change", ["source", "environment", "access", "process", "unknown", "marker"]
)
def test_recent_active_or_unknown_projects_are_protected(tmp_path, monkeypatch, change):
    root = project(tmp_path)
    if change == "source":
        (root / "src/app.py").touch()
    if change == "environment":
        (root / ".venv/lib/package.py").touch()
    if change == "access":
        p = root / "src/app.py"
        os.utime(p, ns=(time.time_ns(), p.stat().st_mtime_ns))
    if change == "process":
        monkeypatch.setattr(
            vc, "active_paths", lambda: ({root / ".venv/bin/python"}, [])
        )
    if change == "unknown":
        monkeypatch.setattr(vc, "active_paths", lambda: (set(), ["denied"]))
    if change == "marker":
        (root / ".venv/pyvenv.cfg").unlink()
    expected_eligible = 1 if change in ("unknown", "access") else 0
    assert vc.scan_venvs(tmp_path)["eligible"] == expected_eligible


def test_period_is_applied_to_project_and_environment(tmp_path):
    project(tmp_path)
    assert vc.scan_venvs(tmp_path, 60)["eligible"] == 0
    assert vc.scan_venvs(tmp_path, 30)["eligible"] == 1


def test_symlinks_are_never_deleted_or_followed(tmp_path):
    root = project(tmp_path)
    external = tmp_path / "elsewhere"
    external.mkdir()
    (external / "precious").write_text("keep")
    (root / "venv").symlink_to(external, target_is_directory=True)
    (root / ".venv/lib/loop").symlink_to(root, target_is_directory=True)
    age(root)
    report = vc.scan_venvs(tmp_path)
    linked = next(v for v in report["items"] if v["path"] == str(root / "venv"))
    assert not linked["eligible"]
    item = next(v for v in report["items"] if v["path"] == str(root / ".venv"))
    vc.remove_venv(item, 30)
    assert (external / "precious").read_text() == "keep"
    assert (root / "src/app.py").exists()


def test_revalidation_rejects_new_nested_activity(tmp_path):
    root = project(tmp_path)
    item = vc.scan_venvs(tmp_path)["items"][0]
    (root / ".venv/lib/new.py").write_text("new")
    with pytest.raises(ValueError, match="zmienił"):
        vc.remove_venv(item, 30)
    assert (root / ".venv").exists()


def test_revalidation_rejects_replaced_environment(tmp_path):
    root = project(tmp_path)
    item = vc.scan_venvs(tmp_path)["items"][0]
    (root / ".venv").rename(root / "preserved")
    (root / ".venv").symlink_to(root / "preserved", target_is_directory=True)
    with pytest.raises(ValueError):
        vc.remove_venv(item, 30)
    assert (root / "preserved/pyvenv.cfg").exists()


@pytest.mark.parametrize(
    "options", [["--dry-run"], ["--list"], ["--json"], ["--yes", "--dry-run"]]
)
def test_readonly_modes_never_delete(tmp_path, options):
    root = project(tmp_path)
    r = CliRunner().invoke(cleanup_services, args(tmp_path, *options))
    assert r.exit_code == 0, r.output
    assert (root / ".venv").exists()
    if "--json" in options:
        assert json.loads(r.output)["eligible"] == 1


def test_confirmed_selection_removes_only_selected_after_summary(tmp_path):
    first = project(tmp_path, "a")
    second = project(tmp_path, "b")
    r = CliRunner().invoke(cleanup_services, args(tmp_path), input="1\ny\n")
    assert r.exit_code == 0, r.output
    assert r.output.index("Znaleziono środowisk") < r.output.index("Wybierz numery")
    assert r.output.index("Do usunięcia: 2") < r.output.index("Usunąć 1")
    assert sum((p / ".venv").exists() for p in [first, second]) == 1


def test_decline_and_invalid_period(tmp_path):
    root = project(tmp_path)
    r = CliRunner().invoke(cleanup_services, args(tmp_path), input="all\nn\n")
    assert r.exit_code == 0 and (root / ".venv").exists()
    for days in ("0", "-5"):
        r = CliRunner().invoke(
            cleanup_services, args(tmp_path, "--days", days, "--yes")
        )
        assert r.exit_code != 0 and (root / ".venv").exists()


def test_conflicting_action_rejected_before_any_cleanup(tmp_path):
    root = project(tmp_path)
    r = CliRunner().invoke(cleanup_services, args(tmp_path, "--docker-all", "--yes"))
    assert r.exit_code != 0 and (root / ".venv").exists()


def test_menu_and_interactive_period(tmp_path, monkeypatch):
    from contextlib import redirect_stdout
    from io import StringIO

    from fixos.cli import _cleanup_venvs as cli
    from fixos.cli.shell_cmd import MENU_SHORTCUTS, print_interactive_menu

    assert MENU_SHORTCUTS["23"] == "cleanup --venvs-old"
    output = StringIO()
    with redirect_stdout(output):
        print_interactive_menu()
    assert "[23]" in output.getvalue() and "venvs-old" in output.getvalue()
    project(tmp_path)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    import click

    @click.command()
    def command():
        cli._cleanup_venvs(False, False, False, False, path=str(tmp_path))

    # CliRunner replaces stdin, so patch the interactive check inside the command.
    @click.command()
    def interactive():
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
        cli._cleanup_venvs(False, False, False, False, path=str(tmp_path))

    r = CliRunner().invoke(interactive, input="60\n")
    assert r.exit_code == 0, r.output
    assert "okres: > 60 dni" in r.output and "Do usunięcia: 0" in r.output

    @click.command()
    def interactive_prompt_path():
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
        cli._cleanup_venvs(False, False, False, False)

    r_path = CliRunner().invoke(interactive_prompt_path, input=f"60\n{tmp_path}\n")
    assert r_path.exit_code == 0, r_path.output
    assert "okres: > 60 dni" in r_path.output and "Do usunięcia: 0" in r_path.output
    assert str(tmp_path) in r_path.output
    assert "Ścieżka do katalogu projektów" in r_path.output

    r_cancel = CliRunner().invoke(interactive_prompt_path, input=f"45\n{tmp_path}\n0\n")
    assert r_cancel.exit_code == 0, r_cancel.output
    assert "Do usunięcia: 1" in r_cancel.output and "Anulowano" in r_cancel.output


def test_measure_sparse_hardlinks_exclusions(tmp_path):
    root = project(tmp_path)
    file = root / "sparse"
    with file.open("wb") as f:
        f.truncate(10_000_000)
    before = ns.measure_python(root)
    os.link(file, root / "hard")
    after = ns.measure_python(root)
    assert before["bytes"] == after["bytes"]
    assert after["bytes"] < 10_000_000
    assert ns.measure_python(root, (".venv",))["entries"] < after["entries"]


def test_native_failure_and_malformed_data_fall_back(tmp_path, monkeypatch):
    project(tmp_path)
    monkeypatch.setenv("FIXOS_NATIVE", "auto")
    monkeypatch.setenv("FIXOS_NATIVE_BIN", "/fake/native")
    for text in ("{}", "[]", "invalid"):
        monkeypatch.setattr(
            ns.subprocess,
            "run",
            lambda *a, payload=text, **kw: subprocess.CompletedProcess(
                a, 0, payload, ""
            ),
        )
        assert ns.measure_tree(tmp_path) == ns.measure_python(tmp_path)


def test_native_backend_parity_or_python_fallback(tmp_path, monkeypatch):
    binary = os.environ.get("FIXOS_TEST_NATIVE_BIN")
    root = project(tmp_path, 'quote"-ż')
    from fixos.diagnostics.project_scanner import discover_project_roots

    if binary:
        os.link(root / ".venv/lib/package.py", root / ".venv/lib/hard.py")
        (root / ".venv/lib/symlink").symlink_to(root, target_is_directory=True)
        monkeypatch.setenv("FIXOS_NATIVE", "auto")
        monkeypatch.setenv("FIXOS_NATIVE_BIN", binary)
        monkeypatch.setenv("FIXOS_NATIVE_DISCOVERY", "1")
        direct = json.loads(
            subprocess.check_output([binary, "measure", str(root)], text=True)
        )
        assert direct == ns.measure_python(root)
        assert ns.measure_tree(root) == direct
    else:
        monkeypatch.setenv("FIXOS_NATIVE", "auto")
        monkeypatch.setenv("FIXOS_NATIVE_BIN", "/missing/fixos-native")
        monkeypatch.setenv("FIXOS_NATIVE_DISCOVERY", "1")
        assert ns.measure_tree(root) == ns.measure_python(root)

    assert discover_project_roots(tmp_path) == [root]


def test_both_sibling_environments_can_be_removed_in_one_selection(tmp_path):
    root = project(tmp_path)
    (root / "venv").mkdir()
    (root / "venv/pyvenv.cfg").write_text("home = /usr/bin")
    age(root)
    result = CliRunner().invoke(cleanup_services, args(tmp_path, "--yes"))
    assert result.exit_code == 0, result.output
    assert not (root / "venv").exists() and not (root / ".venv").exists()
    assert (root / "src/app.py").exists()


def test_replacement_at_root_open_is_preserved(tmp_path, monkeypatch):
    root = project(tmp_path)
    item = vc.scan_venvs(tmp_path)["items"][0]
    real_open = vc.os.open

    def swapped(path, *a, **kw):
        if path == ".venv":
            (root / ".venv").rename(root / "original")
            (root / ".venv").mkdir()
            (root / ".venv/precious").write_text("keep")
        return real_open(path, *a, **kw)

    monkeypatch.setattr(vc.os, "open", swapped)
    with pytest.raises(ValueError):
        vc.remove_venv(item, 30)
    assert (root / ".venv/precious").read_text() == "keep"
    assert (root / "original/pyvenv.cfg").exists()


@pytest.mark.parametrize(
    "signal", ["cwd", "exe", "cmdline", "open_files", "environ", "denied"]
)
def test_process_observer_detects_actual_activity_signals(
    tmp_path, monkeypatch, signal
):
    from types import SimpleNamespace

    root = project(tmp_path)

    class Process:
        pid = 123

        def username(self):
            return "tester"

        def cwd(self):
            return str(root) if signal == "cwd" else "/elsewhere"

        def exe(self):
            return (
                str(root / ".venv/bin/python") if signal == "exe" else "/usr/bin/python"
            )

        def cmdline(self):
            return [str(root / "src/app.py")] if signal == "cmdline" else []

        def open_files(self):
            return (
                [SimpleNamespace(path=str(root / "src/app.py"))]
                if signal == "open_files"
                else []
            )

        def environ(self):
            if signal == "denied":
                raise vc.psutil.AccessDenied(self.pid)
            return {"VIRTUAL_ENV": str(root / ".venv")} if signal == "environ" else {}

    monkeypatch.setattr(vc.psutil, "Process", Process)
    monkeypatch.setattr(vc.psutil, "process_iter", lambda: iter([Process()]))
    monkeypatch.setattr(vc, "active_paths", _REAL_ACTIVE_PATHS)
    report = vc.scan_venvs(tmp_path)
    assert report["eligible"] == (1 if signal == "denied" else 0)
    if signal == "denied":
        assert report["errors"]


def test_unreadable_tree_does_not_become_deletable(tmp_path, monkeypatch):
    root = project(tmp_path)
    other = project(tmp_path, "readable")
    real_scandir = ns.os.scandir

    def denied(path):
        if path == root / ".venv/lib":
            raise PermissionError("test denied")
        return real_scandir(path)

    monkeypatch.setattr(ns.os, "scandir", denied)
    result = vc.scan_venvs(tmp_path)
    assert result["found"] == 2 and result["eligible"] == 1
    assert result["unknown_sizes"] == 1
    unreadable = next(item for item in result["items"] if item["project"] == str(root))
    assert not unreadable["eligible"]
    assert "niepełna" in " ".join(unreadable["reasons"])
    assert next(item for item in result["items"] if item["project"] == str(other))["eligible"]


def test_exact_cutoff_is_not_older(tmp_path):
    root = project(tmp_path)
    latest = ns.measure_python(root)["mtime_ns"]
    now = latest + 30 * 86400 * 10**9
    assert not vc.inspect_project(root, 30, set(), now_ns=now)[0]["eligible"]


def test_partial_process_observation_keeps_readable_paths_and_other_projects(
    tmp_path, monkeypatch
):
    first = project(tmp_path, "active")
    second = project(tmp_path, "old")
    monkeypatch.setattr(
        vc,
        "active_paths",
        lambda: ({first / ".venv/bin/python"}, ["PID 4 cwd: AccessDenied"]),
    )

    report = vc.scan_venvs(tmp_path)

    assert report["found"] == 2
    assert report["eligible"] == 1
    assert report["errors"] == ["PID 4 cwd: AccessDenied"]
    protected = next(item for item in report["items"] if item["project"] == str(first))
    candidate = next(item for item in report["items"] if item["project"] == str(second))
    assert not protected["eligible"]
    assert "projekt lub środowisko używane przez proces" in protected["reasons"]
    assert candidate["eligible"]

    vc.remove_venv(candidate, 30)
    assert not (second / ".venv").exists()
    assert (first / ".venv").exists()


def test_process_fields_are_observed_independently(tmp_path, monkeypatch):
    root = project(tmp_path)
    current_user = vc.psutil.Process().username()

    class Process:
        pid = 17

        def username(self):
            return current_user

        def cwd(self):
            raise vc.psutil.AccessDenied(self.pid)

        def exe(self):
            return "/usr/bin/python3"

        def cmdline(self):
            return ["python", str(root / "src/app.py")]

        def open_files(self):
            raise vc.psutil.AccessDenied(self.pid)

        def environ(self):
            raise vc.psutil.AccessDenied(self.pid)

    monkeypatch.setattr(vc.psutil, "process_iter", lambda: iter([Process()]))
    monkeypatch.setattr(vc, "active_paths", _REAL_ACTIVE_PATHS)
    paths, errors = vc.active_paths()

    assert root / "src/app.py" in paths
    assert len(errors) == 3
    assert all("AccessDenied" in error for error in errors)


def test_cli_reports_partial_observation_without_blocking_all_candidates(
    tmp_path, monkeypatch
):
    project(tmp_path)
    monkeypatch.setattr(vc, "active_paths", lambda: (set(), ["PID 4 cwd: AccessDenied"]))

    result = CliRunner().invoke(cleanup_services, args(tmp_path, "--dry-run"))

    assert result.exit_code == 0, result.output
    assert "Do usunięcia: 1" in result.output
    assert "skanowano dalej" in result.output
    assert "usuwanie zablokowane" not in result.output


def test_native_discovery_rejects_escape_and_symlink(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.setenv("FIXOS_NATIVE", "auto")
    monkeypatch.setenv("FIXOS_NATIVE_DISCOVERY", "1")
    monkeypatch.setenv("FIXOS_NATIVE_BIN", "/fake/native")
    for value in [str(tmp_path / ".." / "outside"), "/outside"]:
        data = {
            "protocol": ns.PROTOCOL,
            "path": str(tmp_path),
            "errors": [],
            "roots": [value],
        }
        monkeypatch.setattr(
            ns.subprocess,
            "run",
            lambda *a, data=data, **kw: subprocess.CompletedProcess(
                a, 0, json.dumps(data), ""
            ),
        )
        assert ns.discover_native(tmp_path, 4, (".git",), frozenset()) is None
    (tmp_path / "link").symlink_to(root, target_is_directory=True)
    data["roots"] = [str(tmp_path / "link")]
    assert ns.discover_native(tmp_path, 4, (".git",), frozenset()) is None


@pytest.mark.parametrize("nested", [False, True])
def test_mounts_and_bind_mounts_are_protected(tmp_path, monkeypatch, nested):
    from types import SimpleNamespace

    root = project(tmp_path)
    mount = root / ".venv/lib" if nested else root / ".venv"
    monkeypatch.setattr(
        vc.psutil,
        "disk_partitions",
        lambda **kw: [SimpleNamespace(mountpoint=str(mount))],
    )
    result = vc.scan_venvs(tmp_path)
    assert result["eligible"] == 0
    assert "montowania" in " ".join(result["items"][0]["reasons"])


def test_access_time_does_not_falsely_protect_stale_venv(tmp_path):
    root = project(tmp_path)
    # Simulate desktop indexer / IDE reading files (bumping atime to now)
    p = root / "src/app.py"
    os.utime(p, ns=(time.time_ns(), p.stat().st_mtime_ns))
    pkg = root / ".venv/lib/package.py"
    os.utime(pkg, ns=(time.time_ns(), pkg.stat().st_mtime_ns))
    cfg = root / ".venv/pyvenv.cfg"
    os.utime(cfg, ns=(time.time_ns(), cfg.stat().st_mtime_ns))

    report = vc.scan_venvs(tmp_path, 30)
    assert report["eligible"] == 1


def test_metadata_and_governance_sync_does_not_protect_stale_project(tmp_path):
    root = project(tmp_path)
    # Touch .git, .idea, .cursor, .planfile, .github, .aider.conf.yml, CLAUDE.md, GEMINI.md, AGENTS.md
    for d in (".git", ".idea", ".cursor", ".planfile", ".github"):
        (root / d).mkdir(parents=True, exist_ok=True)
        (root / d / "recent.log").write_text("recent")
    for f in (".aider.conf.yml", "CLAUDE.md", "GEMINI.md", "AGENTS.md"):
        (root / f).write_text("recent policy")

    report = vc.scan_venvs(tmp_path, 30)
    assert report["eligible"] == 1


def test_revalidation_survives_benign_access_time_change(tmp_path):
    root = project(tmp_path)
    item = vc.scan_venvs(tmp_path)["items"][0]
    # Simulate a file being read after scan (updating atime)
    p = root / ".venv/lib/package.py"
    os.utime(p, ns=(time.time_ns(), p.stat().st_mtime_ns))

    vc.remove_venv(item, 30)
    assert not (root / ".venv").exists()


def test_process_observer_ignores_zombies_and_non_user_processes(monkeypatch):
    class ZombieProcess:
        pid = 101

        def status(self):
            return vc.psutil.STATUS_ZOMBIE

    class OtherUserProcess:
        pid = 102

        def status(self):
            return vc.psutil.STATUS_RUNNING

        def uids(self):
            class Uids:
                real = os.getuid() + 999
            return Uids()

    class MyRunningProcess:
        pid = 103

        def status(self):
            return vc.psutil.STATUS_RUNNING

        def uids(self):
            class Uids:
                real = os.getuid()
            return Uids()

        def cwd(self):
            return "/home/tom/github/semcod"

        def exe(self):
            return "/usr/bin/python3"

        def cmdline(self):
            return ["python3"]

        def open_files(self):
            return []

        def environ(self):
            return {}

    monkeypatch.setattr(
        vc.psutil,
        "process_iter",
        lambda: iter([ZombieProcess(), OtherUserProcess(), MyRunningProcess()]),
    )
    monkeypatch.setattr(vc, "active_paths", _REAL_ACTIVE_PATHS)

    paths, errors = vc.active_paths()
    assert Path("/home/tom/github/semcod") in paths
    assert errors == []

