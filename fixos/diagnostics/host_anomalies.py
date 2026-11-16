"""Host anomalies that ordinary cache cleanup does not see.

Five read-only detectors, each grounded in a failure observed on a shared
build host: a service restarting in a loop, container logs growing without
rotation, large stale directories in tool state stores, regenerable IDE
indexes, and leaked or unreaped processes.

Detectors never mutate. Only :func:`remove_paths` deletes, and only paths that a
fresh scan still reports as removable inside the user's own state roots.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from fixos.diagnostics.artifact_store import is_protected_path, measure_tree

SCHEMA = "fixos.host-anomalies/v1"
RECEIPT_SCHEMA = "fixos.host-anomaly-removal/v1"
STATE_ROOTS = (".local/state", ".local/share")
REMOVABLE = frozenset({"stale-state", "ide-index"})
GIB = 1024**3
MIB = 1024**2

Runner = Callable[[Sequence[str]], str]
DU_TIMEOUT_SECONDS = 1800
ROTATION_HINT = (
    'dodaj do daemon.json: "log-driver": "json-file", '
    '"log-opts": {"max-size": "50m", "max-file": "3"}'
)


def _run(command: Sequence[str]) -> str:
    """Bounded command; an unavailable tool is an empty observation.

    ``du`` over a multi-hundred-gigabyte state store takes minutes on a busy
    host, so it gets a longer bound than the quick status queries.
    """
    timeout = DU_TIMEOUT_SECONDS if command and command[0] == "du" else 60
    try:
        done = subprocess.run(
            list(command), capture_output=True, text=True, check=False, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout


def _finding(category, severity, subject, detail, commands=(), **evidence) -> dict:
    return {
        "category": category,
        "severity": severity,
        "subject": str(subject),
        "detail": detail,
        "suggested_commands": list(commands),
        "removable": category in REMOVABLE and severity != "protected",
        "evidence": evidence,
    }


# --- 1. services restarting in a loop ---------------------------------------


def scan_restart_loops(*, run: Runner = _run, min_restarts: int = 50) -> list[dict]:
    """Units that systemd keeps restarting; each start costs CPU and log volume."""
    findings = []
    for scope in ("system", "user"):
        flag = ["--user"] if scope == "user" else []
        output = run(
            ["systemctl", *flag, "show", "*.service", "--no-pager"]
            + ["-p", "Id", "-p", "NRestarts", "-p", "ActiveState", "-p", "SubState"]
        )
        for block in output.split("\n\n"):
            unit = dict(
                line.split("=", 1) for line in block.splitlines() if "=" in line
            )
            try:
                restarts = int(unit.get("NRestarts", "0"))
            except ValueError:
                continue
            if restarts < min_restarts or not unit.get("Id"):
                continue
            looping = unit.get("SubState") == "auto-restart" or (
                unit.get("ActiveState") == "activating"
            )
            if not looping and restarts < min_restarts * 10:
                continue
            ctl = " ".join(["systemctl", *flag])
            findings.append(
                _finding(
                    "restart-loop",
                    "high" if looping else "medium",
                    unit["Id"],
                    f"{restarts} restartów, stan {unit.get('ActiveState')}/"
                    f"{unit.get('SubState')} ({scope}).",
                    [
                        " ".join(["journalctl", *flag, "-u", unit["Id"]])
                        + " -n 50 --no-pager",
                        f"{ctl} disable --now {unit['Id']}",
                    ],
                    scope=scope,
                    restarts=restarts,
                    looping=looping,
                )
            )
    return sorted(findings, key=lambda f: -f["evidence"]["restarts"])


# --- 2. container logs without rotation -------------------------------------


def scan_container_logs(
    *,
    containers_root: Path = Path("/var/lib/docker/containers"),
    daemon_json: Path = Path("/etc/docker/daemon.json"),
    min_bytes: int = 100 * MIB,
) -> list[dict]:
    """json-file logs grow forever unless the daemon sets ``log-opts.max-size``."""
    try:
        config = json.loads(daemon_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}
    driver = config.get("log-driver", "json-file")
    rotated = driver != "json-file" or bool(
        (config.get("log-opts") or {}).get("max-size")
    )
    logs, unreadable = [], False
    try:
        for entry in containers_root.iterdir():
            for log in entry.glob("*-json.log"):
                size = log.stat().st_size
                if size >= min_bytes:
                    logs.append((size, log))
    except PermissionError:
        unreadable = True
    except OSError:
        return []
    findings = []
    if not rotated and (logs or unreadable):
        findings.append(
            _finding(
                "container-logs",
                "medium",
                daemon_json,
                "Docker nie rotuje logów kontenerów (brak log-opts.max-size).",
                [
                    ROTATION_HINT,
                    f"dockerd --validate --config-file {daemon_json}",
                ],
                rotation_configured=False,
                unreadable=unreadable,
            )
        )
    for size, log in sorted(logs, reverse=True):
        findings.append(
            _finding(
                "container-logs",
                "low",
                log,
                f"Log kontenera {log.parent.name[:12]}: {size / MIB:.0f} MiB.",
                [f"truncate -s 0 {log}"],
                size_bytes=size,
            )
        )
    return findings


# --- 3. large stale directories in tool state stores ------------------------


def _is_stale(path: Path, cutoff: float) -> bool:
    """True when nothing below *path* changed after *cutoff*; stops at first hit."""
    try:
        for parent, _dirs, files in os.walk(path, followlinks=False):
            for name in files:
                if os.lstat(os.path.join(parent, name)).st_mtime > cutoff:
                    return False
    except OSError:
        return False
    return True


def _du(root: Path, depth: int, run: Runner) -> dict[Path, int]:
    sizes = {}
    output = run(["du", "-x", "-B1", f"--max-depth={depth}", str(root)])
    for line in output.splitlines():
        size, _, name = line.partition("\t")
        if size.isdigit() and name:
            sizes[Path(name)] = int(size)
    return sizes


def _visit_state(
    directory: Path,
    depth: int,
    *,
    sizes: dict[Path, int],
    home: Path,
    cutoff: float,
    min_bytes: int,
    min_age_days: int,
    max_depth: int,
    findings: list[dict],
) -> None:
    """Report the top-most wholly stale directory; descend only into live ones."""
    try:
        children = [c for c in directory.iterdir() if c.is_dir() and not c.is_symlink()]
    except OSError:
        return
    for child in sorted(children):
        size = sizes.get(child, 0)
        if size < min_bytes or child.is_mount():
            continue
        if is_protected_path(child, home=home):
            continue
        if _is_stale(child, cutoff):
            findings.append(
                _finding(
                    "stale-state",
                    "review",
                    child,
                    f"{size / GIB:.1f} GiB bez zmian od ponad {min_age_days} dni.",
                    [f"du -sh {child}", f"rm -rf {child}"],
                    size_bytes=size,
                )
            )
        elif depth < max_depth:
            _visit_state(
                child,
                depth + 1,
                sizes=sizes,
                home=home,
                cutoff=cutoff,
                min_bytes=min_bytes,
                min_age_days=min_age_days,
                max_depth=max_depth,
                findings=findings,
            )


def scan_stale_state(
    home: Path,
    *,
    run: Runner = _run,
    min_bytes: int = GIB,
    min_age_days: int = 14,
    max_depth: int = 4,
    now: float | None = None,
) -> list[dict]:
    """Largest untouched directories below ``~/.local/state`` and ``~/.local/share``.

    Reports the top-most directory that is wholly older than the threshold, so
    one abandoned run or backup is one candidate. Always a review decision:
    state stores hold evidence as well as waste.
    """
    cutoff = (now or time.time()) - min_age_days * 86400
    findings = []
    for relative in STATE_ROOTS:
        root = home / relative
        if root.is_symlink() or not root.is_dir():
            continue
        _visit_state(
            root,
            1,
            sizes=_du(root, max_depth, run),
            home=home,
            cutoff=cutoff,
            min_bytes=min_bytes,
            min_age_days=min_age_days,
            max_depth=max_depth,
            findings=findings,
        )
    return sorted(findings, key=lambda f: -f["evidence"]["size_bytes"])


# --- 4. regenerable IDE indexes ---------------------------------------------


def _running_commands(proc: Path) -> list[str]:
    commands = []
    try:
        entries = [e for e in proc.iterdir() if e.name.isdigit()]
    except OSError:
        return commands
    for entry in entries:
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        commands.append(raw.replace(b"\0", b" ").decode("utf-8", "replace"))
    return commands


def scan_ide_indexes(
    home: Path,
    *,
    run: Runner = _run,
    proc: Path = Path("/proc"),
    min_bytes: int = GIB,
) -> list[dict]:
    """JetBrains ``index`` directories are rebuilt on start; protect a running IDE."""
    root = home / ".cache" / "JetBrains"
    if root.is_symlink() or not root.is_dir():
        return []
    running = _running_commands(proc)
    findings = []
    for product in sorted(p for p in root.iterdir() if p.is_dir()):
        index = product / "index"
        if index.is_symlink() or not index.is_dir():
            continue
        size = _du(index, 0, run).get(index, 0)
        if size < min_bytes:
            continue
        in_use = any(product.name in command for command in running)
        findings.append(
            _finding(
                "ide-index",
                "protected" if in_use else "safe",
                index,
                f"Indeks {product.name}: {size / GIB:.1f} GiB"
                + (" (IDE działa, pominięto)." if in_use else ", odtwarzalny."),
                [] if in_use else [f"rm -rf {index}"],
                size_bytes=size,
                ide_running=in_use,
            )
        )
    return findings


# --- 5. leaked and unreaped processes ---------------------------------------


def scan_processes(
    *,
    proc: Path = Path("/proc"),
    min_group: int = 50,
    min_zombies: int = 10,
    min_age_seconds: int = 86400,
    uptime: float | None = None,
    ticks: int | None = None,
) -> list[dict]:
    """Zombies per parent and big groups of identical long-idle processes.

    A group is keyed by the complete command line: leaked helpers repeat one
    exact invocation, while daemons that merely share a name (one proxy per
    port, one shim per container) differ and are not reported.
    """
    try:
        ticks = ticks or os.sysconf("SC_CLK_TCK")
        if uptime is None:
            uptime = float((proc / "uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return []
    zombies: Counter[int] = Counter()
    idle: Counter[tuple[str, str, int]] = Counter()
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
        except OSError:
            continue
        comm = stat[stat.find("(") + 1 : stat.rfind(")")]
        fields = stat[stat.rfind(")") + 2 :].split()
        if len(fields) < 20:
            continue
        state, parent = fields[0], int(fields[1])
        age = uptime - int(fields[19]) / ticks
        if state == "Z":
            zombies[parent] += 1
        elif state == "S" and age >= min_age_seconds:
            try:
                cmdline = (entry / "cmdline").read_bytes()
            except OSError:
                continue
            if cmdline:
                text = cmdline.replace(b"\0", b" ").decode("utf-8", "replace")
                idle[(comm, text.strip(), parent)] += 1
    findings = []
    for parent, count in zombies.most_common():
        if count < min_zombies:
            break
        findings.append(
            _finding(
                "zombie-processes",
                "medium",
                f"pid {parent}",
                f"{count} procesów zombie: rodzic nie odbiera potomków "
                "(w kontenerze uruchom z init: true).",
                [f"ps -o pid,etimes,args -p {parent}"],
                parent_pid=parent,
                count=count,
            )
        )
    for (comm, cmdline, parent), count in idle.most_common():
        if count < min_group:
            break
        findings.append(
            _finding(
                "idle-process-group",
                "medium",
                comm,
                f"{count} uśpionych procesów o identycznym poleceniu, starszych "
                f"niż {min_age_seconds // 3600} h, pod rodzicem {parent}: "
                f"{cmdline[:120]}",
                [f"pgrep -a -x {comm} --older {min_age_seconds}"],
                parent_pid=parent,
                count=count,
            )
        )
    return findings


# --- aggregate and removal --------------------------------------------------


def scan_all(
    home: Path | None = None,
    *,
    run: Runner = _run,
    min_bytes: int = GIB,
    min_age_days: int = 14,
) -> dict:
    home = home or Path.home()
    findings = (
        scan_restart_loops(run=run)
        + scan_container_logs()
        + scan_stale_state(
            home, run=run, min_bytes=min_bytes, min_age_days=min_age_days
        )
        + scan_ide_indexes(home, run=run, min_bytes=min_bytes)
        + scan_processes()
    )
    return {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "findings": findings,
        "reclaimable_bytes": sum(
            f["evidence"].get("size_bytes", 0) for f in findings if f["removable"]
        ),
    }


def _remove_tree(path: Path) -> int | None:
    """Remove *path*; return the errno of the first entry that could not go.

    Trees copied from read-only stores keep directories without the owner
    write bit, so an entry owned by this user is made writable and retried
    once. Entries owned by somebody else stay, and the caller reports what is
    left instead of claiming either success or an untouched directory.
    """
    first_error: list[int] = []

    def retry(function, target, error) -> None:
        if isinstance(error, tuple):  # Python < 3.12 passes sys.exc_info()
            error = error[1]
        try:
            for entry in (os.path.dirname(target), target):
                if os.lstat(entry).st_uid == os.getuid() and not os.path.islink(entry):
                    os.chmod(entry, os.lstat(entry).st_mode | stat.S_IRWXU)
            function(target)
        except OSError as again:
            if not first_error:
                first_error.append(again.errno or getattr(error, "errno", 0) or 0)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)
    return first_error[0] if first_error else None


def remove_paths(
    paths: Sequence[Path],
    findings: Sequence[dict],
    *,
    home: Path | None = None,
    receipt_dir: Path | None = None,
) -> dict:
    """Delete only paths a current scan marks removable; write one receipt.

    A tree that could only be removed in part is listed under ``partial`` with
    the bytes that remain, never under ``removed`` or ``refused``.
    """
    home = home or Path.home()
    allowed = {f["subject"]: f for f in findings if f["removable"]}
    removed, refused, partial = [], [], []
    for path in paths:
        finding = allowed.get(str(path))
        reason = None
        if finding is None:
            reason = "not_a_current_removable_finding"
        elif path.is_symlink() or not path.is_dir():
            reason = "not_a_plain_directory"
        elif home.resolve() not in path.resolve().parents:
            reason = "outside_home"
        elif is_protected_path(path, home=home):
            reason = "protected_path"
        if reason:
            refused.append({"path": str(path), "reason": reason})
            continue
        size = finding["evidence"].get("size_bytes", 0)
        try:
            errno_left = _remove_tree(path)
        except OSError as error:
            errno_left = error.errno or 0
        if not path.exists():
            removed.append(
                {"path": str(path), "category": finding["category"], "size_bytes": size}
            )
            continue
        remaining = measure_tree(path)
        partial.append(
            {
                "path": str(path),
                "category": finding["category"],
                "reason": f"os_error:{errno_left}",
                "remaining_bytes": remaining,
                "freed_bytes": max(size - remaining, 0),
            }
        )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "removed": removed,
        "partial": partial,
        "refused": refused,
        "freed_bytes": sum(item["size_bytes"] for item in removed)
        + sum(item["freed_bytes"] for item in partial),
    }
    if receipt_dir is not None and (removed or partial):
        receipt_dir.mkdir(parents=True, exist_ok=True)
        name = f"host-anomaly-removal-{int(time.time())}.json"
        (receipt_dir / name).write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        receipt["receipt_path"] = str(receipt_dir / name)
    return receipt
