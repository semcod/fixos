"""Safety tests for repository-backed Docker startup optimization."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fixos.diagnostics.docker_startup_optimizer import DockerStartupOptimizer


NOW = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
OLD_COMMIT = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp())
RECENT_COMMIT = int(datetime(2026, 8, 18, tzinfo=timezone.utc).timestamp())


def _completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _container(
    container_id: str,
    repository: Path | None,
    *,
    name: str = "old-api-1",
    policy: str = "unless-stopped",
    status: str = "running",
    mounts: list[dict] | None = None,
) -> dict:
    labels = (
        {"com.docker.compose.project.working_dir": str(repository)}
        if repository
        else {}
    )
    return {
        "Id": container_id,
        "Name": f"/{name}",
        "Created": "2026-04-01T08:00:00.123456789Z",
        "Config": {"Labels": labels},
        "HostConfig": {"RestartPolicy": {"Name": policy}},
        "State": {
            "Status": status,
            "StartedAt": "2026-08-19T07:00:00Z",
        },
        "Mounts": mounts or [],
    }


class _Process:
    def __init__(self, **info):
        self.info = info


def _runner_for(
    containers: list[dict],
    roots: dict[str, str],
    *,
    dirty: set[str] | None = None,
    commits: dict[str, int] | None = None,
    commands: list[list[str]] | None = None,
    mutable: dict | None = None,
):
    dirty = dirty or set()
    commits = commits or {}
    container_ids = [item["Id"] for item in containers]

    def runner(command, **kwargs):
        if commands is not None:
            commands.append(command)
        if command == [
            "docker",
            "container",
            "ls",
            "--all",
            "--quiet",
            "--no-trunc",
        ]:
            return _completed(command, stdout="\n".join(container_ids))
        if command[:2] == ["docker", "inspect"]:
            requested = command[2:]
            selected = [item for item in containers if item["Id"] in requested]
            if len(requested) == 1 and mutable is not None:
                selected = [json.loads(json.dumps(selected[0]))]
                selected[0]["HostConfig"]["RestartPolicy"]["Name"] = mutable[
                    "policy"
                ]
                selected[0]["State"]["Status"] = mutable["status"]
            return _completed(command, stdout=json.dumps(selected))
        if command[:4] == ["git", "-C", command[2], "rev-parse"]:
            root = roots.get(command[2])
            if root:
                return _completed(command, stdout=f"{root}\n")
            return _completed(command, returncode=128, stderr="not a repository")
        if command[:4] == ["git", "-C", command[2], "status"]:
            output = " M active.py\n" if command[2] in dirty else ""
            return _completed(command, stdout=output)
        if command[:4] == ["git", "-C", command[2], "log"]:
            return _completed(
                command, stdout=f"{commits.get(command[2], OLD_COMMIT)}\n"
            )
        if command[:3] == ["docker", "update", "--restart=no"]:
            assert mutable is not None
            mutable["policy"] = "no"
            return _completed(command, stdout=f"{command[-1]}\n")
        if command[:2] == ["docker", "stop"]:
            assert mutable is not None
            mutable["status"] = "exited"
            return _completed(command, stdout=f"{command[-1]}\n")
        raise AssertionError(command)

    return runner


def test_scan_finds_stale_autostart_container_and_its_docker_exec_helper(tmp_path):
    repository = tmp_path / "old-repo"
    repository.mkdir()
    container_id = "a" * 64
    container = _container(container_id, repository)
    helper = _Process(
        pid=4100,
        ppid=143907,
        create_time=NOW.timestamp() - 3600,
        name="docker",
        cmdline=["/usr/bin/docker", "exec", "-i", container_id, "/bin/sh"],
    )
    optimizer = DockerStartupOptimizer(
        runner=_runner_for([container], {str(repository): str(repository)}),
        process_iter=lambda: [helper],
        now=lambda: NOW,
    )

    result = optimizer.scan(min_inactive_days=7)

    assert result["docker_exec_helper_count"] == 1
    assert [item["id"] for item in result["candidates"]] == [container_id]
    candidate = result["candidates"][0]
    assert candidate["repository"] == str(repository)
    assert candidate["repository_sources"] == ["compose-label"]
    assert candidate["inactivity_days"] == 19.3
    assert candidate["docker_exec_helpers"][0]["pid"] == 4100
    assert candidate["reasons"] == ["repository-inactive"]


def test_scan_protects_dirty_recent_unmapped_and_non_startup_containers(tmp_path):
    dirty_repo = tmp_path / "dirty"
    recent_repo = tmp_path / "recent"
    clean_repo = tmp_path / "clean"
    for repository in (dirty_repo, recent_repo, clean_repo):
        repository.mkdir()
    containers = [
        _container("a" * 64, dirty_repo, name="dirty"),
        _container("b" * 64, recent_repo, name="recent"),
        _container("c" * 64, None, name="unmapped"),
        _container("d" * 64, clean_repo, name="manual", policy="no"),
    ]
    roots = {str(item): str(item) for item in (dirty_repo, recent_repo, clean_repo)}
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            containers,
            roots,
            dirty={str(dirty_repo)},
            commits={str(recent_repo): RECENT_COMMIT},
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    result = optimizer.scan()
    reasons = {item["name"]: item["reasons"] for item in result["containers"]}

    assert result["candidates"] == []
    assert "repository-dirty" in reasons["dirty"]
    assert "repository-active" in reasons["recent"]
    assert "repository-not-found" in reasons["unmapped"]
    assert "restart-policy-not-startup-enabled" in reasons["manual"]


def test_scan_fails_closed_when_bind_mounts_resolve_to_multiple_repositories(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    container = _container(
        "a" * 64,
        None,
        mounts=[
            {"Type": "bind", "Source": str(first)},
            {"Type": "bind", "Source": str(second)},
        ],
    )
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            [container], {str(first): str(first), str(second): str(second)}
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    record = optimizer.scan()["containers"][0]

    assert record["candidate"] is False
    assert record["repository_state"] == "ambiguous"
    assert record["repository_candidates"] == sorted([str(first), str(second)])


def test_dry_run_plans_exact_change_without_mutating_docker(tmp_path):
    repository = tmp_path / "old"
    repository.mkdir()
    container_id = "a" * 64
    container = _container(container_id, repository)
    commands = []
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            [container], {str(repository): str(repository)}, commands=commands
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    result = optimizer.optimize([container_id])

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["planned"][0]["restart_policy"] == "no"
    assert result["changed"] == []
    assert not any(command[:2] in (["docker", "update"], ["docker", "stop"]) for command in commands)


def test_optimize_refuses_prefix_and_non_candidate_selection(tmp_path):
    repository = tmp_path / "recent"
    repository.mkdir()
    container_id = "a" * 64
    container = _container(container_id, repository)
    commands = []
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            [container],
            {str(repository): str(repository)},
            commits={str(repository): RECENT_COMMIT},
            commands=commands,
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    result = optimizer.optimize([container_id[:12], container_id], apply=True)

    assert result["success"] is False
    assert len(result["failed"]) == 2
    assert not any(command[:2] == ["docker", "update"] for command in commands)


def test_apply_disables_restart_policy_but_does_not_stop_by_default(tmp_path):
    repository = tmp_path / "old"
    repository.mkdir()
    container_id = "a" * 64
    container = _container(container_id, repository)
    commands = []
    mutable = {"policy": "unless-stopped", "status": "running"}
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            [container],
            {str(repository): str(repository)},
            commands=commands,
            mutable=mutable,
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    result = optimizer.optimize([container_id], apply=True)

    assert result["success"] is True
    assert result["changed"][0]["restart_policy"] == "no"
    assert ["docker", "update", "--restart=no", container_id] in commands
    assert not any(command[:2] == ["docker", "stop"] for command in commands)


def test_stop_is_separate_opt_in_and_uses_bounded_timeout(tmp_path):
    repository = tmp_path / "old"
    repository.mkdir()
    container_id = "a" * 64
    container = _container(container_id, repository)
    commands = []
    mutable = {"policy": "unless-stopped", "status": "running"}
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            [container],
            {str(repository): str(repository)},
            commands=commands,
            mutable=mutable,
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    result = optimizer.optimize(
        [container_id], apply=True, stop_running=True, stop_timeout_seconds=15
    )

    assert result["success"] is True
    assert result["changed"][0]["status"] == "exited"
    assert ["docker", "stop", "--time", "15", container_id] in commands
    assert not any("rm" in command for command in commands)


def test_stop_opt_in_also_closes_a_restarting_container(tmp_path):
    repository = tmp_path / "old"
    repository.mkdir()
    container_id = "a" * 64
    container = _container(container_id, repository, status="restarting")
    commands = []
    mutable = {"policy": "unless-stopped", "status": "restarting"}
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            [container],
            {str(repository): str(repository)},
            commands=commands,
            mutable=mutable,
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    result = optimizer.optimize([container_id], apply=True, stop_running=True)

    assert result["success"] is True
    assert result["changed"][0]["status"] == "exited"
    assert ["docker", "stop", "--time", "10", container_id] in commands


def test_unknown_docker_exec_options_are_not_misattributed():
    assert (
        DockerStartupOptimizer._docker_exec_container(
            ["docker", "exec", "--unknown", "container", "/bin/sh"]
        )
        is None
    )
    assert DockerStartupOptimizer._docker_exec_container(
        ["docker", "exec", "--user", "1000", "-it", "container", "bash"]
    ) == "container"


def test_scan_checks_shared_repository_activity_only_once(tmp_path):
    repository = tmp_path / "compose-project"
    repository.mkdir()
    containers = [
        _container("a" * 64, repository, name="api"),
        _container("b" * 64, repository, name="worker"),
    ]
    commands = []
    optimizer = DockerStartupOptimizer(
        runner=_runner_for(
            containers,
            {str(repository): str(repository)},
            commands=commands,
        ),
        process_iter=lambda: [],
        now=lambda: NOW,
    )

    result = optimizer.scan()

    git_statuses = [command for command in commands if command[-2:] == ["--porcelain", "--untracked-files=normal"]]
    git_logs = [command for command in commands if command[-2:] == ["-1", "--format=%ct"]]
    assert len(result["candidates"]) == 2
    assert len(git_statuses) == 1
    assert len(git_logs) == 1
