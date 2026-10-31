"""Docker cleanup estimates must distinguish logical size from reclaimability."""

import subprocess

import pytest
from click.testing import CliRunner

from fixos.cli import _cleanup_space as cleanup

IMAGE_A = "sha256:" + "a" * 64
IMAGE_B = "sha256:" + "b" * 64
CONTAINER = "c" * 64


def stub_docker(monkeypatch, *, containers="", inspected="", failure=None):
    calls = []

    def run(argv, timeout=60):
        calls.append(argv)
        if argv[:2] == ["docker", "images"]:
            output = f"{IMAGE_A}\t7GB\n{IMAGE_B}\t7GB\n"
        elif argv[:3] == ["docker", "container", "ls"]:
            output = containers
        elif argv[:3] == ["docker", "container", "inspect"]:
            if failure is not None:
                if isinstance(failure, Exception):
                    raise failure
                return subprocess.CompletedProcess(argv, failure, "", "unavailable")
            output = inspected
        else:
            raise AssertionError(argv)
        return subprocess.CompletedProcess(argv, 0, output, "")

    monkeypatch.setattr(cleanup, "_run_cmd", run)
    return calls


def test_images_referenced_by_any_container_are_excluded(monkeypatch):
    calls = stub_docker(monkeypatch, containers=CONTAINER + "\n", inspected=IMAGE_A + "\n")
    result = cleanup._dangling_images()
    assert result["count"] == 1
    assert result["bytes"] == 7_000_000_000
    assert result["usage_known"] is True
    assert ["docker", "container", "ls", "--all", "--quiet", "--no-trunc"] in calls
    assert any("--no-trunc" in argv for argv in calls if argv[1] == "images")


@pytest.mark.parametrize("failure", [1, OSError("unavailable"), subprocess.TimeoutExpired("docker", 60)])
def test_failed_container_inspection_keeps_usage_unknown(monkeypatch, failure):
    stub_docker(monkeypatch, containers=CONTAINER + "\n", failure=failure)
    result = cleanup._dangling_images()
    assert result["usage_known"] is False
    assert result["count"] == 2


def test_no_containers_needs_no_inspection(monkeypatch):
    calls = stub_docker(monkeypatch)
    result = cleanup._dangling_images()
    assert result["usage_known"] is True
    assert result["count"] == 2
    assert not any("inspect" in argv for argv in calls)


def test_image_totals_do_not_claim_shared_layers_as_reclaimable(monkeypatch):
    stub_docker(monkeypatch)
    monkeypatch.setattr(cleanup, "_docker_buildx_builders", list)
    target = cleanup._docker_buildcache_scan()["targets"][0]
    assert target["total_bytes"] == 14_000_000_000
    assert target["reclaimable_bytes"] is None
    assert target["command"] == ["docker", "image", "prune", "--force"]


def test_all_referenced_images_produce_no_prune_target(monkeypatch):
    stub_docker(monkeypatch, containers=f"{CONTAINER}\n{'d' * 64}\n", inspected=f"{IMAGE_A}\n{IMAGE_B}\n")
    monkeypatch.setattr(cleanup, "_docker_buildx_builders", list)
    assert cleanup._docker_buildcache_scan()["targets"] == []


def test_missing_builder_reclaimable_measurement_is_unknown(monkeypatch):
    monkeypatch.setattr(cleanup, "_run_cmd", lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "Total: 14GB\n", ""))
    assert cleanup._builder_cache_bytes("default") == (14_000_000_000, None)


def test_measured_zero_reclaimable_stays_zero(monkeypatch):
    monkeypatch.setattr(cleanup, "_run_cmd", lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "Reclaimable: 0B\nTotal: 14GB\n", ""))
    assert cleanup._builder_cache_bytes("default") == (14_000_000_000, 0)


def test_cli_labels_unknown_reclaimability(monkeypatch):
    import click

    stub_docker(monkeypatch)
    monkeypatch.setattr(cleanup, "_docker_buildx_builders", list)

    @click.command()
    def command():
        cleanup._cleanup_docker_buildcache(False, True, False, False)

    result = CliRunner().invoke(command)
    assert result.exit_code == 0, result.output
    assert "odzyskiwalny rozmiar nieznany" in result.output
    assert "suma rozmiarów obrazów" in result.output
    assert "docker image prune --force" in result.output
