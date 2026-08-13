"""Testy bezpiecznego czyszczenia sieci Docker."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

from fixos.diagnostics.docker_network_cleanup import DockerNetworkCleaner


def _completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _network(
    network_id: str,
    name: str,
    created: str,
    *,
    containers: dict | None = None,
    labels: dict | None = None,
    subnet: str | None = None,
) -> dict:
    return {
        "Name": name,
        "Id": network_id,
        "Created": created,
        "Driver": "bridge",
        "Scope": "local",
        "Containers": containers or {},
        "Labels": labels,
        "IPAM": {"Config": [{"Subnet": subnet}]} if subnet else {"Config": []},
    }


def test_list_unused_protects_active_builtin_and_recent_networks():
    old_id = "a" * 64
    recent_id = "b" * 64
    active_id = "c" * 64
    bridge_id = "d" * 64
    payload = [
        _network(old_id, "old_default", "2026-07-01T10:00:00.123456789Z"),
        _network(recent_id, "recent_default", "2026-08-08T10:00:00Z"),
        _network(
            active_id,
            "active_default",
            "2026-07-01T10:00:00Z",
            containers={"container-id": {"Name": "app"}},
        ),
        _network(bridge_id, "bridge", "2026-07-01T10:00:00Z"),
    ]
    commands = []

    def runner(command, **kwargs):
        commands.append(command)
        if command[:3] == ["docker", "network", "ls"]:
            return _completed(
                command, stdout="\n".join([old_id, recent_id, active_id, bridge_id])
            )
        if command[:3] == ["docker", "network", "inspect"]:
            return _completed(command, stdout=json.dumps(payload))
        raise AssertionError(command)

    cleaner = DockerNetworkCleaner(
        runner=runner,
        now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
    )

    result = cleaner.list_unused(min_age_days=7)

    assert [item["name"] for item in result] == ["old_default"]
    assert result[0]["short_id"] == old_id[:12]
    assert commands[0] == [
        "docker",
        "network",
        "ls",
        "--filter",
        "dangling=true",
        "--quiet",
    ]


def test_dry_run_lists_exact_targets_without_mutating_or_probing():
    cleaner = DockerNetworkCleaner(runner=lambda *args, **kwargs: None)
    candidate = {
        "id": "a" * 64,
        "short_id": "a" * 12,
        "name": "old_default",
        "driver": "bridge",
        "scope": "local",
        "created": "2026-07-01T10:00:00+00:00",
        "age_days": 39.0,
    }
    cleaner.list_unused = lambda min_age_days=0: [candidate]
    cleaner.probe_address_pool = lambda: (_ for _ in ()).throw(
        AssertionError("dry-run must not create a probe network")
    )

    result = cleaner.cleanup(dry_run=True)

    assert result["success"] is True
    assert result["candidates"] == [candidate]
    assert result["removed"] == []
    assert result["pool_probe"]["available"] is None


def test_list_unused_filters_by_exact_compose_project_label():
    matching_id = "a" * 64
    other_id = "b" * 64
    unlabeled_id = "c" * 64
    payload = [
        _network(
            matching_id,
            "oldapp_default",
            "2026-07-01T10:00:00Z",
            labels={"com.docker.compose.project": "oldapp"},
            subnet="10.64.1.0/24",
        ),
        _network(
            other_id,
            "other_default",
            "2026-07-01T10:00:00Z",
            labels={"com.docker.compose.project": "other"},
        ),
        _network(unlabeled_id, "oldapp_manual", "2026-07-01T10:00:00Z"),
    ]

    def runner(command, **kwargs):
        if command[:3] == ["docker", "network", "ls"]:
            return _completed(
                command, stdout="\n".join([matching_id, other_id, unlabeled_id])
            )
        if command[:3] == ["docker", "network", "inspect"]:
            return _completed(command, stdout=json.dumps(payload))
        raise AssertionError(command)

    cleaner = DockerNetworkCleaner(
        runner=runner,
        now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
    )

    result = cleaner.list_unused(compose_projects={"oldapp"})

    assert [network["id"] for network in result] == [matching_id]
    assert result[0]["compose_project"] == "oldapp"
    assert result[0]["subnets"] == ["10.64.1.0/24"]


def test_cleanup_removes_exact_ids_and_verifies_address_pool():
    commands = []
    candidate = {
        "id": "a" * 64,
        "short_id": "a" * 12,
        "name": "old_default",
        "driver": "bridge",
        "scope": "local",
        "created": "2026-07-01T10:00:00+00:00",
        "age_days": 39.0,
    }

    def runner(command, **kwargs):
        commands.append(command)
        return _completed(command, stdout=f"{command[-1]}\n")

    cleaner = DockerNetworkCleaner(runner=runner)
    cleaner.list_unused = lambda min_age_days=0: [candidate]

    result = cleaner.cleanup()

    assert result["success"] is True
    assert result["removed"] == [candidate]
    assert result["recovered_network_slots"] == 1
    assert result["pool_probe"]["available"] is True
    assert ["docker", "network", "rm", candidate["id"]] in commands
    create = next(command for command in commands if command[2] == "create")
    probe_name = create[-1]
    assert create[3:5] == ["--label", "dev.fixos.cleanup-probe=true"]
    assert ["docker", "network", "rm", probe_name] in commands


def test_cleanup_limits_removal_to_previewed_network_ids():
    commands = []
    selected = {
        "id": "a" * 64,
        "short_id": "a" * 12,
        "name": "selected_default",
        "driver": "bridge",
        "scope": "local",
        "created": "2026-07-01T10:00:00+00:00",
        "age_days": 39.0,
    }
    newly_dangling = {**selected, "id": "b" * 64, "name": "new_default"}

    def runner(command, **kwargs):
        commands.append(command)
        return _completed(command, stdout=f"{command[-1]}\n")

    cleaner = DockerNetworkCleaner(runner=runner)
    cleaner.list_unused = lambda min_age_days=0, **kwargs: [
        selected,
        newly_dangling,
    ]

    result = cleaner.cleanup(
        compose_projects={"oldapp"},
        network_ids=[selected["id"]],
        verify_pool=False,
    )

    assert result["removed"] == [selected]
    assert ["docker", "network", "rm", selected["id"]] in commands
    assert ["docker", "network", "rm", newly_dangling["id"]] not in commands


def test_cleanup_reports_race_when_network_gains_an_endpoint():
    candidate = {
        "id": "a" * 64,
        "short_id": "a" * 12,
        "name": "raced_default",
        "driver": "bridge",
        "scope": "local",
        "created": "2026-07-01T10:00:00+00:00",
        "age_days": 39.0,
    }

    def runner(command, **kwargs):
        if command == ["docker", "network", "rm", candidate["id"]]:
            return _completed(
                command, returncode=1, stderr="network has active endpoints"
            )
        return _completed(command, stdout=f"{command[-1]}\n")

    cleaner = DockerNetworkCleaner(runner=runner)
    cleaner.list_unused = lambda min_age_days=0: [candidate]

    result = cleaner.cleanup()

    assert result["success"] is False
    assert result["removed"] == []
    assert result["failed"][0]["name"] == "raced_default"
    assert "active endpoints" in result["failed"][0]["error"]
    assert result["pool_probe"]["available"] is True


def test_cleanup_fails_closed_when_address_pool_probe_cannot_be_created():
    def runner(command, **kwargs):
        if command[2] == "create":
            return _completed(
                command,
                returncode=1,
                stderr="all predefined address pools have been fully subnetted",
            )
        raise AssertionError(command)

    cleaner = DockerNetworkCleaner(runner=runner)
    cleaner.list_unused = lambda min_age_days=0: []

    result = cleaner.cleanup()

    assert result["success"] is False
    assert result["pool_probe"]["available"] is False
    assert "fully subnetted" in result["pool_probe"]["error"]


def test_cleanup_reports_missing_docker_without_traceback():
    def runner(command, **kwargs):
        raise FileNotFoundError("docker")

    result = DockerNetworkCleaner(runner=runner).cleanup(dry_run=True)

    assert result["success"] is False
    assert result["candidates"] == []
    assert "docker network ls unavailable" in result["error"]
