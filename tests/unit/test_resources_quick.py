from __future__ import annotations

from fixos.diagnostics.checks import resources


def test_quick_resources_does_not_recursively_scan_root_or_home(monkeypatch):
    commands: list[str] = []

    def fake_cmd(command, timeout=20):
        commands.append(command)
        return "ok"

    monkeypatch.setattr(resources, "_cmd", fake_cmd)
    monkeypatch.setattr(resources, "IS_LINUX", True)

    result = resources.diagnose_resources()

    combined = "\n".join(commands)
    assert "du -sh /home" not in combined
    assert "find / -xdev" not in combined
    assert "--modules files" in result["large_files"]
