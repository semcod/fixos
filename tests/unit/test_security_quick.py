from __future__ import annotations

from fixos.diagnostics.checks import security


def test_security_does_not_recursively_walk_every_home(monkeypatch):
    commands: list[str] = []

    def fake_cmd(command, timeout=20):
        commands.append(command)
        return "ok"

    monkeypatch.setattr(security, "_cmd", fake_cmd)
    monkeypatch.setattr(security, "IS_LINUX", True)

    security.diagnose_security()

    authorized_keys = next(
        command for command in commands if "authorized_keys" in command
    )
    assert "find /home -name" not in authorized_keys
    assert "/home/*/.ssh" in authorized_keys
    assert "-maxdepth 1" in authorized_keys
