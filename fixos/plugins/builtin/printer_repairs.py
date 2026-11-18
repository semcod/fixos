"""Structured, shell-free printer repair operations for CUPS and Windows Spooler.

Validates every parameter (printer queue name, IPv4/IPv6 host address, target
OS) and builds explicit ``list[str]`` argument vectors executed with
``subprocess.run(..., shell=False)`` so untrusted queue names or network values
never cross a shell command-parsing boundary.
"""

from __future__ import annotations

import base64
import ipaddress
import re
import subprocess
import time
from collections.abc import Callable, Mapping
from typing import Any

ArgvRunner = Callable[[list[str]], tuple[int, str, str]]

_CUPS_QUEUE_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,126}$")
_WINDOWS_FORBIDDEN_CHARS = set('\x00\r\n\t\\/,;"`$|&<>')


class InvalidRepairError(ValueError):
    """Raised when a structured printer repair specification fails validation."""


def validate_queue_name(queue: str, system: str = "linux") -> str:
    """Validate a CUPS or Windows printer queue name before argv construction."""
    if not isinstance(queue, str) or not queue:
        raise InvalidRepairError("Nazwa kolejki drukarki jest pusta.")
    if queue.startswith("-"):
        raise InvalidRepairError(
            f"Niedozwolona nazwa kolejki zaczynająca się od '-': {queue!r}"
        )
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in queue):
        raise InvalidRepairError("Nazwa kolejki zawiera znaki sterujące.")

    if system == "windows":
        if len(queue) > 220 or any(ch in _WINDOWS_FORBIDDEN_CHARS for ch in queue):
            raise InvalidRepairError(
                f"Niedozwolone znaki w nazwie drukarki Windows: {queue!r}"
            )
        return queue

    if not _CUPS_QUEUE_RE.fullmatch(queue):
        raise InvalidRepairError(
            f"Nieprawidłowa nazwa kolejki CUPS: {queue!r}"
        )
    return queue


def validate_printer_address(address: str) -> tuple[str, str]:
    """Validate an IPv4 or IPv6 literal and return ``(normalized, uri_host)``."""
    if not isinstance(address, str) or not address.strip():
        raise InvalidRepairError("Adres IP drukarki jest pusty.")
    cleaned = address.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    try:
        parsed = ipaddress.ip_address(cleaned)
    except ValueError as exc:
        raise InvalidRepairError(
            f"Nieprawidłowy adres IP drukarki: {address!r}"
        ) from exc
    normalized = str(parsed)
    uri_host = f"[{normalized}]" if parsed.version == 6 else normalized
    return normalized, uri_host


def powershell_encoded_argv(script: str) -> list[str]:
    """Encode a PowerShell snippet as UTF-16LE Base64 for shell-free execution."""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
        encoded,
    ]


def _ps_single_quote(value: str) -> str:
    return value.replace("'", "''")


def build_repair_steps(
    spec: Mapping[str, Any], timestamp: str | None = None
) -> list[list[str]]:
    """Build validated ``argv`` steps for a structured printer repair spec."""
    if not isinstance(spec, Mapping):
        raise InvalidRepairError("Brak strukturalnej specyfikacji naprawy.")

    op = str(spec.get("op") or "")
    system = str(spec.get("system") or "linux").lower()

    if op == "enable_cups":
        return [["sudo", "systemctl", "enable", "--now", "cups"]]

    if op == "restart_spooler":
        return [powershell_encoded_argv("Restart-Service -Name 'Spooler' -Force")]

    if op == "resume_queue":
        queue = validate_queue_name(str(spec.get("queue") or ""), system=system)
        if system == "windows":
            q_lit = _ps_single_quote(queue)
            return [powershell_encoded_argv(f"Resume-Printer -Name '{q_lit}'")]
        return [
            ["sudo", "cupsenable", queue],
            ["sudo", "cupsaccept", queue],
        ]

    if op == "clear_jobs":
        queue = validate_queue_name(str(spec.get("queue") or ""), system=system)
        if system == "windows":
            q_lit = _ps_single_quote(queue)
            return [
                powershell_encoded_argv(
                    f"Get-PrintJob -PrinterName '{q_lit}' | Remove-PrintJob"
                )
            ]
        return [["cancel", "-a", queue]]

    if op == "repoint_queue":
        queue = validate_queue_name(str(spec.get("queue") or ""), system=system)
        normalized_ip, uri_host = validate_printer_address(
            str(spec.get("address") or "")
        )
        if system == "windows":
            port_name = f"IP_{normalized_ip.replace(':', '_')}"
            q_lit = _ps_single_quote(queue)
            p_lit = _ps_single_quote(port_name)
            ip_lit = _ps_single_quote(normalized_ip)
            script = (
                f"if (-not (Get-PrinterPort -Name '{p_lit}' -ErrorAction "
                f"SilentlyContinue)) {{ Add-PrinterPort -Name '{p_lit}' "
                f"-PrinterHostAddress '{ip_lit}' }}; "
                f"Set-Printer -Name '{q_lit}' -PortName '{p_lit}'"
            )
            return [powershell_encoded_argv(script)]

        steps: list[list[str]] = []
        if system == "linux":
            stamp = timestamp or time.strftime("%Y%m%d%H%M%S")
            if not re.fullmatch(r"[0-9]{8,20}", stamp):
                raise InvalidRepairError("Nieprawidłowy znacznik czasu kopii zapasowej.")
            steps.append(
                [
                    "sudo",
                    "cp",
                    "/etc/cups/printers.conf",
                    f"/etc/cups/printers.conf.bak-{stamp}",
                ]
            )
        steps.extend(
            [
                [
                    "sudo",
                    "lpadmin",
                    "-p",
                    queue,
                    "-E",
                    "-v",
                    f"ipp://{uri_host}/ipp/print",
                    "-m",
                    "everywhere",
                ],
                ["sudo", "cupsenable", queue],
                ["sudo", "cupsaccept", queue],
            ]
        )
        return steps

    raise InvalidRepairError(f"Nieznana operacja naprawy drukarki: {op!r}")


def _default_argv_runner(argv: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        argv,
        check=False,
        shell=False,
        text=True,
        capture_output=True,
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def execute_repair(
    spec: Mapping[str, Any] | None,
    runner: ArgvRunner | None = None,
) -> tuple[bool, int, str]:
    """Validate and execute all repair steps without invoking a shell."""
    if spec is None:
        return False, 2, "Brak zwalidowanej operacji naprawy dla tego zgłoszenia."
    try:
        steps = build_repair_steps(spec)
    except InvalidRepairError as exc:
        return False, 2, str(exc)

    exec_step = runner or _default_argv_runner
    for argv in steps:
        rc, out, err = exec_step(argv)
        if rc != 0:
            return False, rc, (err or out).strip()
    return True, 0, ""
