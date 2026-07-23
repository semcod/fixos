from __future__ import annotations

import threading

from fixos.diagnostics import system_checks


def test_quick_diagnostics_skip_expensive_file_inventory(monkeypatch):
    called: list[str] = []

    def probe(name):
        def run():
            called.append(name)
            return {"name": name}

        return run

    modules = {
        "system": ("system", probe("system")),
        "audio": ("audio", probe("audio")),
        "files": ("files", probe("files")),
    }
    monkeypatch.setattr(system_checks, "DIAGNOSTIC_MODULES", modules)
    monkeypatch.setattr(
        system_checks, "DEFAULT_DIAGNOSTIC_MODULES", ("system", "audio")
    )

    result = system_checks.get_full_diagnostics(
        list(system_checks.DEFAULT_DIAGNOSTIC_MODULES)
    )

    assert list(result) == ["system", "audio"]
    assert set(called) == {"system", "audio"}


def test_all_modules_run_concurrently_and_keep_requested_order(monkeypatch):
    barrier = threading.Barrier(3, timeout=2)

    def probe(name):
        def run():
            barrier.wait()
            return {"name": name}

        return run

    modules = {
        "one": ("one", probe("one")),
        "two": ("two", probe("two")),
        "files": ("files", probe("files")),
    }
    monkeypatch.setattr(system_checks, "DIAGNOSTIC_MODULES", modules)

    result = system_checks.get_full_diagnostics(["all"])

    assert list(result) == ["one", "two", "files"]
    assert [value["name"] for value in result.values()] == ["one", "two", "files"]
