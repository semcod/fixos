from __future__ import annotations

import base64
import subprocess
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from fixos.cli.printers_cmd import printers as printers_cli
from fixos.plugins.base import DiagnosticResult, Finding, Severity
from fixos.plugins.builtin import printer_repairs
from fixos.plugins.builtin.printer_repairs import (
    InvalidRepairError,
    build_repair_steps,
    execute_repair,
    validate_printer_address,
    validate_queue_name,
)


def _decode_ps(argv: list[str]) -> str:
    assert argv[:4] == [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
    ]
    return base64.b64decode(argv[4]).decode("utf-16le")


def test_validate_queue_name_accepts_safe_names():
    assert validate_queue_name("HL-L5200DW-2", "linux") == "HL-L5200DW-2"
    assert validate_queue_name("Office_Printer.1", "darwin") == "Office_Printer.1"
    assert (
        validate_queue_name("Brother HL-L5200DW (Copy 1)", "windows")
        == "Brother HL-L5200DW (Copy 1)"
    )


@pytest.mark.parametrize(
    ("queue", "system"),
    [
        ("", "linux"),
        ("-p", "linux"),
        ("--option=evil", "linux"),
        ("HL; touch /tmp/pwned", "linux"),
        ("HL$(id)", "linux"),
        ("HL`id`", "linux"),
        ("HL|cat", "linux"),
        ("../etc/passwd", "linux"),
        ("HL\nname", "linux"),
        ("-Name", "windows"),
        ("Printer;Calc", "windows"),
        ("Printer$env:USERNAME", "windows"),
        ("Printer`nCalc", "windows"),
        ("Printer| Out-File x", "windows"),
        ("Printer\\Share", "windows"),
    ],
)
def test_validate_queue_name_rejects_hostile_inputs(queue: str, system: str):
    with pytest.raises(InvalidRepairError):
        validate_queue_name(queue, system=system)


def test_validate_printer_address_ipv4_ipv6_and_malformed():
    assert validate_printer_address("192.168.188.158") == (
        "192.168.188.158",
        "192.168.188.158",
    )
    assert validate_printer_address("2001:db8::10") == (
        "2001:db8::10",
        "[2001:db8::10]",
    )
    assert validate_printer_address("[2001:db8::10]") == (
        "2001:db8::10",
        "[2001:db8::10]",
    )

    for bad in (
        "",
        "   ",
        "BRN3C2AF4E8C6F8",
        "192.168.1.999",
        "192.168.1.10; id",
        "192.168.1.10/24",
        "http://192.168.1.10",
    ):
        with pytest.raises(InvalidRepairError):
            validate_printer_address(bad)


def test_build_repair_steps_linux_macos_and_windows():
    assert build_repair_steps({"op": "enable_cups", "system": "linux"}) == [
        ["sudo", "systemctl", "enable", "--now", "cups"]
    ]

    spooler_steps = build_repair_steps({"op": "restart_spooler", "system": "windows"})
    assert len(spooler_steps) == 1
    assert "Restart-Service -Name 'Spooler' -Force" == _decode_ps(spooler_steps[0])

    assert build_repair_steps(
        {"op": "resume_queue", "system": "linux", "queue": "HL"}
    ) == [
        ["sudo", "cupsenable", "HL"],
        ["sudo", "cupsaccept", "HL"],
    ]

    win_resume = build_repair_steps(
        {"op": "resume_queue", "system": "windows", "queue": "Bob's Printer"}
    )
    assert _decode_ps(win_resume[0]) == "Resume-Printer -Name 'Bob''s Printer'"

    assert build_repair_steps(
        {"op": "clear_jobs", "system": "darwin", "queue": "HL"}
    ) == [["cancel", "-a", "HL"]]

    win_clear = build_repair_steps(
        {"op": "clear_jobs", "system": "windows", "queue": "Brother"}
    )
    assert (
        _decode_ps(win_clear[0])
        == "Get-PrintJob -PrinterName 'Brother' | Remove-PrintJob"
    )

    linux_repoint = build_repair_steps(
        {
            "op": "repoint_queue",
            "system": "linux",
            "queue": "HL",
            "address": "192.168.188.158",
        },
        timestamp="20261118120000",
    )
    assert linux_repoint == [
        [
            "sudo",
            "cp",
            "/etc/cups/printers.conf",
            "/etc/cups/printers.conf.bak-20261118120000",
        ],
        [
            "sudo",
            "lpadmin",
            "-p",
            "HL",
            "-E",
            "-v",
            "ipp://192.168.188.158/ipp/print",
            "-m",
            "everywhere",
        ],
        ["sudo", "cupsenable", "HL"],
        ["sudo", "cupsaccept", "HL"],
    ]

    mac_repoint = build_repair_steps(
        {
            "op": "repoint_queue",
            "system": "darwin",
            "queue": "HL",
            "address": "2001:db8::5",
        }
    )
    assert mac_repoint[0] == [
        "sudo",
        "lpadmin",
        "-p",
        "HL",
        "-E",
        "-v",
        "ipp://[2001:db8::5]/ipp/print",
        "-m",
        "everywhere",
    ]
    assert len(mac_repoint) == 3

    win_repoint = build_repair_steps(
        {
            "op": "repoint_queue",
            "system": "windows",
            "queue": "Brother",
            "address": "192.168.188.158",
        }
    )
    decoded = _decode_ps(win_repoint[0])
    assert "Add-PrinterPort -Name 'IP_192.168.188.158'" in decoded
    assert "Set-Printer -Name 'Brother' -PortName 'IP_192.168.188.158'" in decoded


def test_default_runner_uses_shell_false_and_stops_on_failure(monkeypatch):
    calls: list[tuple[list[str], bool]] = []

    def fake_subprocess_run(argv, **kwargs):
        calls.append((list(argv), kwargs.get("shell")))
        if argv[1] == "cupsaccept":
            return SimpleNamespace(returncode=1, stdout="", stderr="permission denied")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    ok, rc, err = execute_repair(
        {"op": "resume_queue", "system": "linux", "queue": "HL"}
    )
    assert not ok
    assert rc == 1
    assert "permission denied" in err
    assert calls == [
        (["sudo", "cupsenable", "HL"], False),
        (["sudo", "cupsaccept", "HL"], False),
    ]


def test_execute_repair_rejects_missing_or_hostile_spec_without_invoking_runner():
    invoked = []
    ok, rc, err = execute_repair(None, runner=lambda argv: invoked.append(argv) or (0, "", ""))
    assert not ok and rc == 2 and not invoked
    assert "Brak" in err

    ok, rc, err = execute_repair(
        {"op": "clear_jobs", "system": "linux", "queue": "HL; rm -rf /"},
        runner=lambda argv: invoked.append(argv) or (0, "", ""),
    )
    assert not ok and rc == 2 and not invoked


def test_cli_printers_fix_preserves_confirmation_and_reports_failure(monkeypatch):
    import fixos.plugins.builtin.printers as printers_mod

    fake_result = DiagnosticResult(
        plugin_name="printers",
        status=Severity.WARNING,
        findings=[
            Finding(
                title="HL: kolejka wstrzymana",
                severity=Severity.WARNING,
                description="wstrzymana",
                command="sudo cupsenable HL && sudo cupsaccept HL",
                data={"repair": {"op": "resume_queue", "system": "linux", "queue": "HL"}},
            ),
            Finding(
                title="Evil: wstrzymana",
                severity=Severity.CRITICAL,
                description="hostile queue",
                command="sudo cupsenable 'Evil;id'",
                data={
                    "repair": {
                        "op": "resume_queue",
                        "system": "linux",
                        "queue": "Evil;id",
                    }
                },
            ),
        ],
        raw_data={"queues": []},
    )

    class DummyPlugin:
        def __init__(self, sweep: bool = False) -> None:
            self.sweep = sweep

        def diagnose(self) -> DiagnosticResult:
            return fake_result

    executed: list[list[str]] = []

    def fake_runner(argv: list[str]) -> tuple[int, str, str]:
        executed.append(argv)
        return 0, "", ""

    monkeypatch.setattr(printers_mod, "Plugin", DummyPlugin)
    monkeypatch.setattr(printer_repairs, "_default_argv_runner", fake_runner)

    # First finding accepted ("y"), second hostile finding accepted ("y") -> fails validation (exit 1)
    runner = CliRunner()
    res = runner.invoke(printers_cli, ["--fix"], input="y\ny\n")
    assert res.exit_code == 1
    assert "OK" in res.output
    assert "FAIL (2)" in res.output
    assert executed == [
        ["sudo", "cupsenable", "HL"],
        ["sudo", "cupsaccept", "HL"],
    ]

    # Declining confirmation ("n\nn\n") executes nothing and exits 0
    executed.clear()
    res_declined = runner.invoke(printers_cli, ["--fix"], input="n\nn\n")
    assert res_declined.exit_code == 0
    assert executed == []
