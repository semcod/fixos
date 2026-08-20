import json
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace

from fixos.diagnostics.orphaned_workloads import OrphanedWorkloadCleaner
from fixos.diagnostics.process_chains import ProcessRecord


NOW = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
NOW_EPOCH = NOW.timestamp()


def _container(
    name: str,
    *,
    working_dir: str,
    age_days: int = 5,
    restart: str = "unless-stopped",
    status: str = "running",
) -> dict:
    container_id = (name.encode().hex() * 64)[:64]
    return {
        "Id": container_id,
        "Name": f"/{name}",
        "Created": datetime.fromtimestamp(
            NOW_EPOCH - age_days * 86400, timezone.utc
        ).isoformat(),
        "Config": {
            "Labels": {
                "com.docker.compose.project": name.split("-")[0],
                "com.docker.compose.project.working_dir": working_dir,
            }
        },
        "HostConfig": {"RestartPolicy": {"Name": restart}},
        "State": {"Status": status},
    }


def _record(
    pid: int,
    ppid: int,
    name: str,
    command: tuple[str, ...],
    *,
    hours: float = 24,
    username: str = "tom",
) -> ProcessRecord:
    return ProcessRecord(
        pid=pid,
        ppid=ppid,
        name=name,
        cmdline=command,
        create_time=NOW_EPOCH - hours * 3600,
        username=username,
    )


def _runner_for(containers: list[dict], calls: list[list[str]]):
    by_id = {item["Id"]: item for item in containers}

    def runner(command, **kwargs):
        calls.append(command)
        if command[:4] == ["docker", "container", "ls", "--all"]:
            return subprocess.CompletedProcess(command, 0, "\n".join(by_id), "")
        if command[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([by_id[item] for item in command[2:]]),
                "",
            )
        if command[:3] == ["docker", "update", "--restart=no"]:
            by_id[command[3]]["HostConfig"]["RestartPolicy"]["Name"] = "no"
            return subprocess.CompletedProcess(command, 0, command[3], "")
        if command[:2] == ["docker", "stop"]:
            by_id[command[-1]]["State"]["Status"] = "exited"
            return subprocess.CompletedProcess(command, 0, command[-1], "")
        raise AssertionError(command)

    return runner


def _cleaner(*, containers=(), records=(), connections=(), **kwargs):
    calls: list[list[str]] = []
    return (
        OrphanedWorkloadCleaner(
            runner=_runner_for(list(containers), calls),
            process_provider=lambda: list(records),
            connection_provider=lambda: list(connections),
            cwd_provider=lambda pid: f"/work/{pid}",
            rss_provider=lambda pid: pid * 1024,
            path_exists=lambda path: path == "/work/existing",
            now=lambda: NOW,
            self_pid=900,
            **kwargs,
        ),
        calls,
    )


def test_scan_only_selects_old_missing_absolute_startup_enabled_compose_paths():
    containers = [
        _container("missing", working_dir="/work/gone"),
        _container("existing", working_dir="/work/existing"),
        _container("young", working_dir="/work/young", age_days=1),
        _container("relative", working_dir="work/gone"),
        _container("manual", working_dir="/work/gone", restart="no"),
    ]
    cleaner, _ = _cleaner(containers=containers)

    scan = cleaner.scan(min_age_days=3, min_process_hours=12)

    assert [item["name"] for item in scan["docker_candidates"]] == ["missing"]
    rejected = {item["name"]: item["reasons"] for item in scan["docker"]}
    assert "compose-working-directory-exists" in rejected["existing"]
    assert "container-too-young" in rejected["young"]
    assert "compose-working-directory-unsafe" in rejected["relative"]
    assert "restart-policy-not-startup-enabled" in rejected["manual"]


def test_scan_reports_stale_agent_and_client_free_server_with_evidence():
    records = [
        _record(10, 1, "pycharm", ("/snap/bin/pycharm",), hours=72),
        _record(20, 10, "cursor-agent", ("cursor-agent", "acp"), hours=48),
        _record(21, 20, "mcp", ("mcp",), hours=47),
        _record(22, 20, "php", ("php", "-S", "127.0.0.1:8781"), hours=47),
        _record(30, 1, "node", ("node", "/tmp/server.mjs"), hours=20),
    ]
    connections = [
        SimpleNamespace(pid=22, status="LISTEN", laddr=("127.0.0.1", 8781)),
        SimpleNamespace(pid=30, status="LISTEN", laddr=("127.0.0.1", 8793)),
    ]
    cleaner, _ = _cleaner(records=records, connections=connections)

    scan = cleaner.scan(min_process_hours=12)

    assert {item["root_pid"] for item in scan["process_candidates"]} == {20, 30}
    agent = next(item for item in scan["process_candidates"] if item["root_pid"] == 20)
    server = next(item for item in scan["process_candidates"] if item["root_pid"] == 30)
    assert agent["member_pids"] == [20, 22, 21]
    assert agent["listen_ports"] == [8781]
    assert agent["process_count"] == 3
    assert server["listen_ports"] == [8793]
    assert not any(item["root_pid"] == 22 for item in scan["processes"])


def test_scan_reports_connected_agent_and_protects_current_ancestry():
    records = [
        _record(10, 1, "pycharm", ("/snap/bin/pycharm",), hours=72),
        _record(20, 10, "cursor-agent", ("cursor-agent", "acp"), hours=48),
        _record(800, 1, "node", ("node", "/tmp/server.mjs"), hours=48),
        _record(900, 800, "fixos", ("fixos",), hours=24),
    ]
    connections = [
        SimpleNamespace(pid=20, status="ESTABLISHED", laddr=("127.0.0.1", 9000))
    ]
    cleaner, _ = _cleaner(records=records, connections=connections)

    scan = cleaner.scan(min_process_hours=12)

    connected = next(item for item in scan["processes"] if item["root_pid"] == 20)
    assert connected["candidate"] is True
    assert connected["established_connections"] == 1
    protected = next(item for item in scan["processes"] if item["root_pid"] == 800)
    assert protected["protected"] is True
    assert [item["root_pid"] for item in scan["process_candidates"]] == [20]


def test_cleanup_disables_restart_stops_exact_container_and_keeps_objects():
    container = _container("missing", working_dir="/work/gone")
    cleaner, calls = _cleaner(containers=[container])

    result = cleaner.cleanup(
        docker_ids=[container["Id"]],
        min_age_days=3,
        min_process_hours=12,
        apply=True,
    )

    assert result["success"] is True
    assert result["docker_changed"][0]["restart_policy"] == "no"
    assert result["docker_changed"][0]["status"] == "exited"
    assert ["docker", "update", "--restart=no", container["Id"]] in calls
    assert ["docker", "stop", "--time", "10", container["Id"]] in calls
    assert not any(command[1] in {"rm", "rmi", "volume", "network"} for command in calls)


def test_cleanup_processes_leaves_first_after_exact_identity_revalidation():
    records = [
        _record(10, 1, "pycharm", ("/snap/bin/pycharm",), hours=72),
        _record(20, 10, "cursor-agent", ("cursor-agent", "acp"), hours=48),
        _record(21, 20, "mcp", ("mcp",), hours=47),
        _record(22, 21, "php", ("php", "-S", "127.0.0.1:8781"), hours=46),
    ]
    identities = {item.pid: item.create_time for item in records}
    alive = set(identities)
    terminated: list[tuple[int, bool]] = []

    def terminate(pid: int, force: bool) -> None:
        terminated.append((pid, force))
        alive.discard(pid)

    cleaner, _ = _cleaner(
        records=records,
        identity_provider=identities.get,
        alive_provider=lambda pid, created: pid in alive,
        terminator=terminate,
    )

    result = cleaner.cleanup(
        process_identities=[(20, identities[20])],
        min_process_hours=12,
        apply=True,
        grace_seconds=0,
    )

    assert result["success"] is True
    assert terminated == [(22, False), (21, False), (20, False)]
    assert result["processes_changed"][0]["surviving_pids"] == []


def test_cleanup_rejects_pid_reuse_before_signalling():
    records = [
        _record(10, 1, "pycharm", ("/snap/bin/pycharm",), hours=72),
        _record(20, 10, "cursor-agent", ("cursor-agent", "acp"), hours=48),
    ]
    signalled: list[int] = []
    cleaner, _ = _cleaner(
        records=records,
        identity_provider=lambda pid: records[-1].create_time + 10 if pid == 20 else None,
        terminator=lambda pid, force: signalled.append(pid),
    )

    result = cleaner.cleanup(
        process_identities=[(20, records[-1].create_time)],
        min_process_hours=12,
        apply=True,
        grace_seconds=0,
    )

    assert result["success"] is False
    assert result["failed"][0]["error"] == "root PID identity changed"
    assert signalled == []
