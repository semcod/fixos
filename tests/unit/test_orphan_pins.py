import json
import os
import subprocess
from datetime import datetime, timezone

import pytest
from click.testing import CliRunner

from fixos.cli import cleanup_cmd
from fixos.cli.main import cli
from fixos.diagnostics.orphaned_workloads import OrphanedWorkloadCleaner
from fixos.orphan_pins import (
    PIN_SCHEMA,
    OrphanProjectPinError,
    OrphanProjectPins,
    normalize_project_path,
)


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def test_pin_store_is_atomic_private_idempotent_and_reversible(tmp_path):
    store = OrphanProjectPins(tmp_path / "fixos" / "pins.json", now=lambda: NOW)

    first, changed = store.pin("/gone/project/../project")
    repeated, repeated_changed = store.pin("/gone/project")

    assert changed is True
    assert repeated_changed is False
    assert repeated == first
    assert store.paths() == ("/gone/project",)
    assert json.loads(store.path.read_text())["schema"] == PIN_SCHEMA
    assert os.stat(store.path).st_mode & 0o777 == 0o600
    assert not list(store.path.parent.glob(f".{store.path.name}.*"))

    assert store.unpin("/gone/project/") is True
    assert store.unpin("/gone/project") is False
    assert store.paths() == ()


@pytest.mark.parametrize("value", ["relative/project", "/"])
def test_pin_store_rejects_ambiguous_or_broad_paths(value):
    with pytest.raises(ValueError):
        normalize_project_path(value)


def test_pin_store_fails_closed_on_untrusted_state(tmp_path):
    path = tmp_path / "pins.json"
    path.write_text('{"schema": "wrong", "pins": []}', encoding="utf-8")

    with pytest.raises(OrphanProjectPinError, match="invalid.*schema"):
        OrphanProjectPins(path).paths()


def test_pinned_compose_path_remains_visible_but_cannot_be_cleaned():
    container_id = "a" * 64
    container = {
        "Id": container_id,
        "Name": "/relcom-api",
        "Created": "2026-08-10T12:00:00+00:00",
        "Config": {
            "Labels": {
                "com.docker.compose.project": "relcom",
                "com.docker.compose.project.working_dir": "/gone/relcom",
            }
        },
        "HostConfig": {"RestartPolicy": {"Name": "unless-stopped"}},
        "State": {"Status": "running"},
    }
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[:4] == ["docker", "container", "ls", "--all"]:
            return subprocess.CompletedProcess(command, 0, f"{container_id}\n", "")
        if command[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(command, 0, json.dumps([container]), "")
        raise AssertionError(command)

    cleaner = OrphanedWorkloadCleaner(
        runner=runner,
        process_provider=lambda: [],
        connection_provider=lambda: [],
        pinned_paths_provider=lambda: ["/gone/relcom/"],
        path_exists=lambda path: False,
        now=lambda: NOW,
        self_pid=900,
    )

    scan = cleaner.scan(min_age_days=3)
    result = cleaner.cleanup(docker_ids=[container_id], min_age_days=3, apply=True)

    assert scan["docker_candidates"] == []
    assert [item["id"] for item in scan["pinned_docker"]] == [container_id]
    assert scan["pinned_docker"][0]["candidate"] is False
    assert "compose-working-directory-pinned" in scan["pinned_docker"][0]["reasons"]
    assert result["success"] is False
    assert result["failed"][0]["error"] == "not an exact candidate in the fresh scan"
    assert not any(
        command[:2] in (["docker", "update"], ["docker", "stop"]) for command in calls
    )


def test_cleanup_help_and_welcome_expose_persistent_orphan_pin_management():
    help_result = CliRunner().invoke(cleanup_cmd.cleanup_services, ["--help"])
    welcome_result = CliRunner().invoke(cli, [])

    assert help_result.exit_code == welcome_result.exit_code == 0
    assert "--pin-orphan-project ABSOLUTE_PATH" in help_result.output
    assert "--unpin-orphan-project ABSOLUTE_PATH" in help_result.output
    assert "--list-orphan-pins" in help_result.output
    assert "fixos cleanup --list-orphan-pins" in welcome_result.output


def test_orphan_pin_cli_persists_lists_and_unpins_without_scanning(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    pinned = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--pin-orphan-project", "/gone/relcom", "--json"],
    )
    listed = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--list-orphan-pins", "--json"],
    )
    unpinned = CliRunner().invoke(
        cleanup_cmd.cleanup_services,
        ["--unpin-orphan-project", "/gone/relcom", "--json"],
    )

    assert pinned.exit_code == listed.exit_code == unpinned.exit_code == 0
    assert json.loads(pinned.output)["changed"] is True
    assert json.loads(listed.output)["pins"][0]["path"] == "/gone/relcom"
    assert json.loads(unpinned.output)["pins"] == []
