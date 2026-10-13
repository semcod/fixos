"""fixos cleanup --docker-volumes: listing, selection safety and re-check."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import click
from click.testing import CliRunner

from fixos.cli import _cleanup_docker_volumes as volumes
from fixos.cli import _cleanup_space as space
from fixos.diagnostics.storage_analyzer import (
    StorageAnalyzer,  # loads the mixins in order
)

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)
INSPECT = [
    {"Name": "llmass_huggingface-cache", "CreatedAt": "2025-10-06T10:00:00Z",
     "Labels": {"com.docker.compose.project": "llmass"}, "Mountpoint": "/v/hf"},
    {"Name": "ifuri-onedev_mirror-data", "CreatedAt": "2026-07-20T10:00:00Z",
     "Labels": {"com.docker.compose.project": "ifuri-onedev"}, "Mountpoint": "/v/mirror"},
    {"Name": "chat_ollama_data", "CreatedAt": "2026-10-10T10:00:00Z",
     "Labels": None, "Mountpoint": "/v/chat"},
]


class FakeDocker:
    """Answers the docker/du/sudo commands the module issues."""

    def __init__(self, dangling=None, in_use=()):
        self.dangling = list(dangling or [v["Name"] for v in INSPECT])
        self.in_use = set(in_use)
        self.calls: list[list[str]] = []

    def __call__(self, argv, timeout=60):
        self.calls.append(argv)
        out, code = "", 0
        if argv[:5] == ["docker", "volume", "ls", "-q", "-f"]:
            names = self.dangling
            if len(argv) > 6:
                wanted = argv[-1].split("=", 1)[1].strip("^$")
                names = [n for n in names if n == wanted]
            out = "\n".join(names)
        elif argv[:3] == ["docker", "volume", "inspect"]:
            out = json.dumps([v for v in INSPECT if v["Name"] in argv[3:]])
        elif argv[:3] == ["docker", "ps", "-aq"]:
            name = argv[-1].split("=", 1)[1]
            out = "c1" if name in self.in_use else ""
        elif argv[:2] == ["du", "-sbl0"] or argv[:3] == ["sudo", "-n", "du"]:
            sizes = {"/v/hf": 23_500_000_000, "/v/mirror": 7_400_000_000}
            out = "".join(f"{sizes[p]}\t{p}\0" for p in argv if p in sizes)
        elif argv[:3] == ["docker", "volume", "rm"]:
            self.dangling.remove(argv[3])
        return SimpleNamespace(returncode=code, stdout=out, stderr="")


def _invoke(fn, *args, input_text="", **kwargs):
    @click.command()
    def command():
        fn(*args, **kwargs)

    return CliRunner().invoke(command, input=input_text)


def test_lists_name_project_age_and_sorts_by_size(monkeypatch):
    monkeypatch.setattr(space, "_run_cmd", FakeDocker())

    found = volumes._unused_volumes(None, [], now=NOW)

    assert [c["name"] for c in found] == [
        "llmass_huggingface-cache", "ifuri-onedev_mirror-data", "chat_ollama_data",
    ]
    assert found[0]["project"] == "llmass" and round(found[0]["age_days"]) == 372
    assert found[2]["size_known"] is False
    assert [c["protected"] for c in found] == [False, True, False]


def test_match_and_days_filter(monkeypatch):
    monkeypatch.setattr(space, "_run_cmd", FakeDocker())

    found = volumes._unused_volumes(30, ["ollama", "huggingface"], now=NOW)

    assert [c["name"] for c in found] == ["llmass_huggingface-cache"]


def test_yes_never_removes_data_looking_volumes(monkeypatch):
    docker = FakeDocker()
    monkeypatch.setattr(space, "_run_cmd", docker)

    result = _invoke(volumes._cleanup_docker_volumes, False, False, False, True)

    removed = [c[3] for c in docker.calls if c[:3] == ["docker", "volume", "rm"]]
    assert result.exit_code == 0
    assert "ifuri-onedev_mirror-data" not in removed
    assert set(removed) == {"llmass_huggingface-cache", "chat_ollama_data"}


def test_volume_in_use_at_removal_time_is_skipped(monkeypatch):
    docker = FakeDocker(in_use={"chat_ollama_data"})
    monkeypatch.setattr(space, "_run_cmd", docker)

    _invoke(volumes._cleanup_docker_volumes, False, False, False, False, input_text="3\ny\n")

    assert not any(c[:3] == ["docker", "volume", "rm"] for c in docker.calls)


def test_dry_run_and_list_do_not_remove(monkeypatch):
    docker = FakeDocker()
    monkeypatch.setattr(space, "_run_cmd", docker)

    _invoke(volumes._cleanup_docker_volumes, False, True, False, True)
    _invoke(volumes._cleanup_docker_volumes, False, False, True, False)

    assert not any(c[:3] == ["docker", "volume", "rm"] for c in docker.calls)


def test_full_analysis_never_prunes_volumes(monkeypatch):
    from fixos.diagnostics._storage_container_mixin import _ContainerAnalyzerMixin

    assert issubclass(StorageAnalyzer, _ContainerAnalyzerMixin)

    class Analyzer(_ContainerAnalyzerMixin):
        def __init__(self):
            self.items = []

        def _get_dir_size(self, path):
            return 300 * 1024**3

    analyzer = Analyzer()
    analyzer._add_docker_total_item(10, 2)

    command = analyzer.items[0].cleanup_command
    assert "--volumes" not in command and "system prune" not in command
    assert command == "docker builder prune --force --filter until=168h"


def test_app_data_volumes_are_protected():
    for name in ("mcp_openwebui-data", "proxy_open-webui-data", "n8n_storage", "mcp_git-repo-storage"):
        assert volumes._DATA_TOKENS.search(name), name
    for name in ("llmass_huggingface-cache", "chat_ollama_data", "if-uri_trivy-cache"):
        assert not volumes._DATA_TOKENS.search(name), name


def test_sizes_split_into_parallel_batches_without_unreadable_partial_sizes(monkeypatch):
    calls = []

    def fake_run(argv, timeout=60):
        calls.append(argv)
        paths = argv[argv.index("--") + 1 :]
        return SimpleNamespace(returncode=0, stdout="".join(f"10\t{p}\0" for p in paths), stderr="")

    monkeypatch.setattr(space, "_run_cmd", fake_run)
    mountpoints = [f"/nonexistent/v{i}" for i in range(20)]

    sizes = volumes._volume_sizes(mountpoints)

    assert sizes == dict.fromkeys(mountpoints, 10)
    assert len(calls) == volumes._SIZE_WORKERS
    assert all(call[:3] == ["sudo", "-n", "du"] for call in calls)
