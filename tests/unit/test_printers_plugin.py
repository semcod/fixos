from __future__ import annotations

import json
import time

from fixos.plugins.base import Severity
from fixos.plugins.builtin import printers
from fixos.plugins.builtin.printers import (
    Plugin,
    PrinterQueue,
    active_fault_reasons,
    find_ip_by_mac,
    mac_hint_from_hostname,
    parse_ipp_attributes,
    parse_lpstat_v,
    parse_neighbors,
)

IPP_OUT = """
    Get printer attributes using get-printer-attributes                  [PASS]
        printer-make-and-model (textWithoutLanguage) = Brother HL-L5200DW series
        printer-state (enum) = idle
        printer-state-reasons (keyword) = none
        document-format-supported (1setOf mimeMediaType) = application/octet-stream,image/urf,image/pwg-raster
"""


def make_runner(responses: dict[str, str], calls: list[str] | None = None):
    def run(cmd, timeout=120):
        if calls is not None:
            calls.append(cmd)
        for key, value in responses.items():
            if key in cmd:
                return True, value, "", 0
        return True, "", "", 0

    return run


def cups_responses(
    uri: str, model: str = "Generic PCL 6/PCL XL Printer Foomatic/pxlcolor"
):
    return {
        "systemctl is-active cups": "active",
        "lpstat -v": f"device for HL: {uri}",
        "lpstat -p": "printer HL is idle.  enabled since Fri 13 Nov 2026",
        "lpstat -a": "HL accepting requests since Fri 13 Nov 2026",
        "lpoptions": f"device-uri={uri} printer-make-and-model='{model}'",
        "ip neigh": "192.168.188.158 dev enp90s0 lladdr 3c:2a:f4:e8:c6:f8 REACHABLE",
        "ipptool": IPP_OUT,
    }


def test_mac_hint_from_vendor_hostnames():
    assert mac_hint_from_hostname("BRN3C2AF4E8C6F8") == "3c2af4e8c6f8"
    assert mac_hint_from_hostname("BRW3C2AF4E8C6F8.local") == "3c2af4e8c6f8"
    assert mac_hint_from_hostname("NPI8A1B2C") == "8a1b2c"
    assert mac_hint_from_hostname("office-printer") is None


def test_parse_neighbors_linux_mac_and_windows():
    linux = (
        "192.168.1.5 dev eth0 lladdr 3c:2a:f4:e8:c6:f8 REACHABLE\n10.0.0.1 dev x FAILED"
    )
    mac = "? (192.168.1.6) at 3c:2a:f4:e8:c6:f9 on en0 ifscope [ethernet]"
    win = "  192.168.1.7          3c-2a-f4-e8-c6-fa     dynamic"
    table = parse_neighbors(f"{linux}\n{mac}\n{win}")
    assert table == {
        "3c2af4e8c6f8": "192.168.1.5",
        "3c2af4e8c6f9": "192.168.1.6",
        "3c2af4e8c6fa": "192.168.1.7",
    }
    assert find_ip_by_mac("e8c6f9", table) == "192.168.1.6"


def test_parse_lpstat_v_and_ipp():
    assert parse_lpstat_v(
        "device for HL-2: lpd://BRN1/BINARY_P1\ndevice for U: usb://Brother/HL"
    ) == {
        "HL-2": "lpd://BRN1/BINARY_P1",
        "U": "usb://Brother/HL",
    }
    attrs = parse_ipp_attributes(IPP_OUT)
    assert attrs["printer-state"] == "idle"
    assert printers.driverless_capable(attrs)


def test_queue_host_and_port():
    assert PrinterQueue("a", "lpd://BRN1/BINARY_P1").host == "brn1"
    assert PrinterQueue("a", "lpd://BRN1/BINARY_P1").port == 515
    assert PrinterQueue("a", "ipp://1.2.3.4:8631/ipp/print").port == 8631
    assert PrinterQueue("a", "usb://Brother/HL").host is None
    assert PrinterQueue("a", "10.0.0.9").host == "10.0.0.9"


def test_unresolvable_brother_hostname_is_located_by_mac_and_repointed():
    plugin = Plugin(
        runner=make_runner(cups_responses("lpd://BRN3C2AF4E8C6F8/BINARY_P1")),
        resolver=lambda host: None,
        port_open=lambda host, port, *a: True,
        system="linux",
    )
    result = plugin.diagnose()
    assert result.status == Severity.CRITICAL
    finding = next(f for f in result.findings if "rozwiązać" in f.title)
    assert finding.data["address"] == "192.168.188.158"
    assert (
        "lpadmin -p HL -E -v ipp://192.168.188.158/ipp/print -m everywhere"
        in finding.command
    )
    assert "printers.conf.bak" in finding.command


def test_unresolvable_without_arp_entry_has_no_command():
    responses = cups_responses("lpd://BRN000000000001/BINARY_P1")
    plugin = Plugin(
        runner=make_runner(responses),
        resolver=lambda host: None,
        port_open=lambda *a: False,
        system="linux",
    )
    finding = plugin.diagnose().findings[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.command is None
    assert "--scan" in finding.suggestion


def test_generic_driver_on_driverless_printer_is_flagged():
    plugin = Plugin(
        runner=make_runner(cups_responses("lpd://192.168.188.158/BINARY_P1")),
        resolver=lambda host: host,
        port_open=lambda *a: True,
        system="linux",
    )
    result = plugin.diagnose()
    titles = [f.title for f in result.findings]
    assert any("sterownik" in t for t in titles)
    assert result.status == Severity.WARNING


def test_healthy_ipp_everywhere_queue_is_ok():
    plugin = Plugin(
        runner=make_runner(
            cups_responses(
                "ipp://192.168.188.158/ipp/print",
                "Brother HL-L5200DW series, driverless",
            )
        ),
        resolver=lambda host: host,
        port_open=lambda *a: True,
        system="linux",
    )
    result = plugin.diagnose()
    assert result.findings == []
    assert result.status == Severity.OK


def test_unreachable_printer_port():
    plugin = Plugin(
        runner=make_runner(cups_responses("ipp://10.1.1.1/ipp/print")),
        resolver=lambda host: host,
        port_open=lambda *a: False,
        system="linux",
    )
    assert "nie odpowiada" in plugin.diagnose().findings[0].title


def test_disabled_queue_and_stuck_jobs():
    old = time.strftime("%a %d %b %Y %I:%M:%S %p", time.localtime(time.time() - 3600))
    responses = cups_responses("ipp://10.1.1.1/ipp/print", "driverless")
    responses["lpstat -p"] = "printer HL disabled since Fri 13 Nov 2026 -\n\tunable"
    responses["not-completed"] = f"HL-27   tom   30720   {old} CET"
    plugin = Plugin(
        runner=make_runner(responses),
        resolver=lambda host: host,
        port_open=lambda *a: True,
        system="linux",
    )
    findings = {f.title: f for f in plugin.diagnose().findings}
    assert "cupsenable HL" in findings["HL: kolejka wstrzymana"].command
    stuck = findings["HL: zablokowane zadania (1)"]
    assert stuck.data["jobs"] == ["HL-27"]


def test_recent_job_is_not_stuck():
    fresh = time.strftime("%a %d %b %Y %I:%M:%S %p", time.localtime())
    assert printers._stuck_jobs(f"HL-30 tom 1024 {fresh} CET") == []


def test_cups_stopped():
    plugin = Plugin(
        runner=make_runner({"systemctl is-active cups": "inactive"}),
        system="linux",
    )
    finding = plugin.diagnose().findings[0]
    assert finding.command == "sudo systemctl enable --now cups"


def test_windows_unresolvable_port_is_repointed():
    printers_json = json.dumps(
        {
            "Name": "Brother",
            "Port": "BRN3C2AF4E8C6F8",
            "Host": "BRN3C2AF4E8C6F8",
            "Driver": "Brother HL-L5200DW series",
            "Status": "Normal",
            "Jobs": ["4"],
        }
    )
    responses = {
        "Get-Service Spooler": "Running",
        "Get-Printer": printers_json,
        "arp -a": "  192.168.188.158       3c-2a-f4-e8-c6-f8     dynamic",
    }
    plugin = Plugin(
        runner=make_runner(responses),
        resolver=lambda host: None,
        port_open=lambda *a: True,
        system="windows",
    )
    findings = plugin.diagnose().findings
    repoint = next(f for f in findings if "rozwiązać" in f.title)
    assert "Add-PrinterPort -Name 'IP_192.168.188.158'" in repoint.command
    assert "Set-Printer -Name 'Brother'" in repoint.command
    assert any("Remove-PrintJob" in (f.command or "") for f in findings)


def test_windows_spooler_stopped():
    plugin = Plugin(
        runner=make_runner({"Get-Service Spooler": "Stopped"}), system="windows"
    )
    assert "Restart-Service Spooler" in plugin.diagnose().findings[0].command


def test_test_print_waits_for_completion():
    responses = {
        "| lp -d": "request id is HL-29 (1 file(s))",
        "not-completed": "",
        "completed": "HL-29 tom 1024 Tue\n\tAlerts: job-completed-successfully",
    }
    ok, message = Plugin(runner=make_runner(responses), system="linux").test_print(
        "HL", 5
    )
    assert ok and "HL-29" in message


def test_registry_includes_printers():
    from fixos.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    registry.discover()
    assert "printers" in registry._plugins


def test_active_fault_reasons_evaluates_each_reason_independently():
    assert active_fault_reasons("media-empty-error,toner-low-report") == [
        "media-empty-error"
    ]
    assert active_fault_reasons("toner-low-report, media-empty-error") == [
        "media-empty-error"
    ]
    assert active_fault_reasons(
        " media-empty-error , door-open-error , toner-low-report , none , "
    ) == ["media-empty-error", "door-open-error"]
    assert active_fault_reasons("toner-low-report,marker-supply-low-report") == []
    assert active_fault_reasons("none") == []
    assert active_fault_reasons("   ,  ") == []


def test_diagnose_reports_mixed_ipp_fault_even_when_trailing_reason_is_report():
    responses = cups_responses(
        "ipp://192.168.188.158/ipp/print",
        "Brother HL-L5200DW series, driverless",
    )
    responses["ipptool"] = IPP_OUT.replace(
        "printer-state-reasons (keyword) = none",
        "printer-state-reasons (keyword) = media-empty-error,toner-low-report",
    )
    plugin = Plugin(
        runner=make_runner(responses),
        resolver=lambda host: host,
        port_open=lambda *a: True,
        system="linux",
    )
    result = plugin.diagnose()
    assert result.status == Severity.WARNING
    fault = next(f for f in result.findings if "zgłasza problem" in f.title)
    assert fault.data["reasons"] == ["media-empty-error"]
    assert "media-empty-error" in fault.description
    assert "toner-low-report" not in fault.description

