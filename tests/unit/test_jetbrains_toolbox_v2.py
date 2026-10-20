"""JetBrains cleanup with the flat Toolbox layout and installs registered in state.json."""

from __future__ import annotations

import json
from pathlib import Path

from fixos.cli import _cleanup_space as space


def _install(root: Path, name: str, data_dir: str) -> Path:
    location = root / name
    location.mkdir(parents=True)
    (location / "product-info.json").write_text(
        json.dumps({"dataDirectoryName": data_dir}), encoding="utf-8"
    )
    return location


def _home(tmp_path: Path, tools: list[dict]) -> Path:
    toolbox = tmp_path / ".local/share/JetBrains/Toolbox"
    toolbox.mkdir(parents=True, exist_ok=True)
    (toolbox / "state.json").write_text(json.dumps({"tools": tools}), encoding="utf-8")
    for name in ("WebStorm2025.3", "WebStorm2026.2", "PyCharm2026.2", "PyCharm2026.3", "Webstorm"):
        (tmp_path / ".local/share/JetBrains" / name).mkdir()
        (tmp_path / ".local/share/JetBrains" / name / "data").write_bytes(b"x" * 10)
    return tmp_path


def _tools(tmp_path: Path) -> list[dict]:
    apps = tmp_path / ".local/share/JetBrains/Toolbox/apps"
    snap = tmp_path / "snap/pycharm-professional/686"
    return [
        {"toolId": "WebStorm", "buildNumber": "262.1", "displayVersion": "2026.2.3",
         "installLocation": str(_install(apps, "webstorm", "WebStorm2026.2"))},
        {"toolId": "WebStorm", "buildNumber": "262.1", "displayVersion": "2026.2.3",
         "installLocation": str(_install(apps, "webstorm-3", "WebStorm2026.2"))},
        {"toolId": "PyCharm-P", "buildNumber": "263.7", "displayVersion": "2026.3",
         "installLocation": str(_install(apps, "pycharm-2", "PyCharm2026.3"))},
        {"toolId": "PyCharm-P", "buildNumber": "262.9", "displayVersion": "2026.2.3",
         "installLocation": str(_install(snap.parent, snap.name, "PyCharm2026.2"))},
    ]


def test_only_superseded_unused_version_data_is_a_candidate(tmp_path):
    home = _home(tmp_path, _tools(tmp_path))
    names = [c["description"] for c in space._jetbrains_stale_data_dirs(home, space._toolbox_installs(home))]
    # PyCharm2026.2 is older than 2026.3 but the snap install still uses it.
    assert names == ["WebStorm2025.3"]


def test_unreadable_install_fails_closed(tmp_path):
    tools = _tools(tmp_path)
    tools.append({"toolId": "Gateway", "buildNumber": "1", "installLocation": str(tmp_path / "missing")})
    home = _home(tmp_path, tools)
    assert space._toolbox_installs(home) is None
    assert space._jetbrains_stale_data_dirs(home, None) == []


def test_duplicate_registered_installs_are_advised_not_deleted(tmp_path):
    home = _home(tmp_path, _tools(tmp_path))
    [advisory] = space._toolbox_duplicate_installs(space._toolbox_installs(home))
    assert "WebStorm 2026.2.3 (262.1) zainstalowany 2×" in advisory
    assert "Toolbox" in advisory


def test_jetbrains_candidates_include_stale_data_without_touching_installs(tmp_path, monkeypatch):
    home = _home(tmp_path, _tools(tmp_path))
    monkeypatch.setattr(space.Path, "home", classmethod(lambda cls: home))
    paths = {c["path"] for c in space._jetbrains_candidates()}
    assert home / ".local/share/JetBrains/WebStorm2025.3" in paths
    assert not any("Toolbox/apps" in str(path) for path in paths)
