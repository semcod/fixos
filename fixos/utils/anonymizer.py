"""
Anonimizacja wrażliwych danych systemowych z podglądem dla użytkownika.
"""

from __future__ import annotations

import getpass
import hashlib
import ipaddress
import os
import re
import secrets
import socket
from dataclasses import dataclass, field
from typing import Iterable

from .terminal import _C


MAPPING_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ALIAS_RE = re.compile(
    r"\[(?:HOME|HOSTNAME|USER(?:-[0-9]+)?|UUID-[0-9]+|"
    r"IP-(?:ANY|LOOPBACK|BROADCAST|"
    r"(?:PRIVATE|PUBLIC|LINKLOCAL|MULTICAST|RESERVED)-[0-9]+))\]"
)
HOME_RE = re.compile(
    r"/home/(?P<user>(?!\[USER(?:-[0-9]+)?\](?:/|$))[^/\s\"'\\]+)"
    r"(?P<suffix>(?:/[^\s\"'\\]*)?)"
)
IPV4_RE = re.compile(
    r"(?<![A-Za-z0-9_.:])(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
    r"(?![A-Za-z0-9_.:])"
)
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
SERIAL_RE = re.compile(
    r"\b(?P<label>S/N|Serial|SN)(?P<separator>[\s:]+)"
    r"(?P<value>[A-Z0-9]{6,20})\b",
    re.IGNORECASE,
)
API_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-|pk-|xai-|AIzaSy[A-Za-z0-9_-]+|Bearer\s+)"
    r"[A-Za-z0-9\-_.]{15,}"
)
CREDENTIAL_RE = re.compile(
    r"(?P<key>password|passwd|secret|token|api_key|apikey|auth)"
    r"\s*[=:]\s*\S+",
    re.IGNORECASE,
)
RFC1918 = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
SEMANTIC_IPS = {
    "0.0.0.0": "[IP-ANY]",
    "255.255.255.255": "[IP-BROADCAST]",
}


class ResolutionError(ValueError):
    """Raised when an anonymized alias cannot be resolved safely."""


def _new_mapping_id() -> str:
    return f"payload-{secrets.token_hex(8)}"


@dataclass
class AnonymizationContext:
    """Memory-only alias state. Never include this object in LLM payloads."""

    mapping_id: str = field(default_factory=_new_mapping_id)
    primary_user: str | None = None
    reverse_map: dict[str, str] = field(default_factory=dict, repr=False)
    _aliases: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)
    _next_index: dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not MAPPING_ID_RE.fullmatch(self.mapping_id):
            raise ValueError("mapping_id does not match the anonymization contract")
        if self.primary_user:
            self.bind("USER", self.primary_user, "[USER]")

    def bind(self, category: str, original: str, token: str) -> str:
        existing = self.reverse_map.get(token)
        if existing is not None and existing != original:
            raise ValueError(f"alias collision for {token}")
        self.reverse_map[token] = original
        self._aliases[(category, original)] = token
        return token

    def numbered_alias(self, category: str, original: str, *, start: int = 1) -> str:
        key = (category, original)
        existing = self._aliases.get(key)
        if existing is not None:
            return existing
        index = self._next_index.get(category, start)
        token = f"[{category}-{index}]"
        self._next_index[category] = index + 1
        return self.bind(category, original, token)

    def user_alias(self, username: str) -> str:
        if self.primary_user is not None and username == self.primary_user:
            return self.bind("USER", username, "[USER]")
        return self.numbered_alias("USER", username, start=2)


@dataclass
class AnonymizationReport:
    """Raport anonimizacji – co zostało zmaskowane."""

    original_length: int = 0
    anonymized_length: int = 0
    replacements: dict[str, int] = field(default_factory=dict)
    mapping_id: str = ""
    payload_sha256: str = ""

    def add(self, category: str, count: int = 1):
        self.replacements[category] = self.replacements.get(category, 0) + count

    def summary(self) -> str:
        if not self.replacements:
            return "  Nie znaleziono wrażliwych danych."
        lines = []
        for cat, count in sorted(self.replacements.items()):
            lines.append(f"  ✓ {cat}: {count} wystąpień")
        return "\n".join(lines)


def _get_sensitive() -> dict:
    result = {}
    try:
        result["hostname"] = socket.gethostname()
    except Exception:
        result["hostname"] = None
    try:
        result["username"] = getpass.getuser()
    except Exception:
        result["username"] = None
    try:
        result["home"] = os.path.expanduser("~")
    except Exception:
        result["home"] = None
    return result


def _redact_irreversible(data: str, report: AnonymizationReport) -> str:
    data, count = API_TOKEN_RE.subn("[API_TOKEN_REDACTED]", data)
    if count:
        report.add("Tokeny API", count)

    def replace_credential(match: re.Match[str]) -> str:
        return f"{match.group('key')}=[REDACTED]"

    data, count = CREDENTIAL_RE.subn(replace_credential, data)
    if count:
        report.add("Hasła/sekrety", count)
    data, count = MAC_RE.subn("XX:XX:XX:XX:XX:XX", data)
    if count:
        report.add("Adresy MAC", count)

    def replace_serial(match: re.Match[str]) -> str:
        return (
            f"{match.group('label')}{match.group('separator')}"
            "[SERIAL-REDACTED]"
        )

    data, count = SERIAL_RE.subn(replace_serial, data)
    if count:
        report.add("Numery seryjne", count)
    return data


def _replace_home_paths(
    data: str,
    context: AnonymizationContext,
    report: AnonymizationReport,
) -> str:
    def replace(match: re.Match[str]) -> str:
        report.add("Ścieżki /home")
        alias = context.user_alias(match.group("user"))
        return f"/home/{alias}{match.group('suffix')}"

    return HOME_RE.sub(replace, data)


def _replace_literal_home(
    data: str,
    home: str,
    context: AnonymizationContext,
    report: AnonymizationReport,
) -> str:
    """Replace a non-/home home root without matching it inside another path."""
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_.-]){re.escape(home)}(?=$|[/\\])"
    )
    data, count = pattern.subn("[HOME]", data)
    if count:
        context.bind("HOME", home, "[HOME]")
        report.add("Ścieżka domowa", count)
    return data


def _replace_user_words(
    data: str,
    context: AnonymizationContext,
    report: AnonymizationReport,
) -> str:
    users = [
        (original, alias)
        for (category, original), alias in context._aliases.items()
        if category == "USER"
    ]
    for original, alias in sorted(users, key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<![A-Za-z0-9_.-]){re.escape(original)}(?![A-Za-z0-9_.-])"
        data, count = re.subn(pattern, alias, data)
        if count:
            report.add("Username", count)
    return data


def _replace_uuid(
    data: str,
    context: AnonymizationContext,
    report: AnonymizationReport,
) -> str:
    def replace(match: re.Match[str]) -> str:
        report.add("UUID (serial/hardware)")
        return context.numbered_alias("UUID", match.group(0))

    return UUID_RE.sub(replace, data)


def _ip_category(address: ipaddress.IPv4Address) -> str:
    if address.is_link_local:
        return "IP-LINKLOCAL"
    if address.is_multicast:
        return "IP-MULTICAST"
    if any(address in network for network in RFC1918):
        return "IP-PRIVATE"
    if address.is_global:
        return "IP-PUBLIC"
    return "IP-RESERVED"


def _replace_ipv4(
    data: str,
    context: AnonymizationContext,
    report: AnonymizationReport,
) -> str:
    def replace(match: re.Match[str]) -> str:
        original = match.group(0)
        try:
            address = ipaddress.IPv4Address(original)
        except ipaddress.AddressValueError:
            return original
        report.add("Adresy IPv4")
        semantic = SEMANTIC_IPS.get(original)
        if semantic is not None:
            return semantic
        if address.is_loopback:
            return "[IP-LOOPBACK]"
        return context.numbered_alias(_ip_category(address), original)

    return IPV4_RE.sub(replace, data)


def anonymize(
    data_str: str,
    context: AnonymizationContext | None = None,
) -> tuple[str, AnonymizationReport]:
    """
    Anonimizuje wrażliwe dane.

    Returns:
        Tuple (zanonimizowany_string, raport)
    """
    if not isinstance(data_str, str):
        data_str = str(data_str)

    sensitive = _get_sensitive()
    context = context or AnonymizationContext(primary_user=sensitive.get("username"))
    report = AnonymizationReport(
        original_length=len(data_str),
        mapping_id=context.mapping_id,
    )

    # Secrets are removed before reversible aliases are allocated, so a secret
    # can never enter the local reverse map by also looking like an identifier.
    data_str = _redact_irreversible(data_str, report)

    if sensitive.get("hostname"):
        count = data_str.count(sensitive["hostname"])
        if count:
            context.bind("HOSTNAME", sensitive["hostname"], "[HOSTNAME]")
            data_str = data_str.replace(sensitive["hostname"], "[HOSTNAME]")
            report.add("Hostname", count)

    # Non-/home platforms retain the legacy [HOME] token. Linux home paths are
    # handled structurally below to preserve every non-sensitive suffix.
    if sensitive.get("home") and not sensitive["home"].startswith("/home/"):
        data_str = _replace_literal_home(
            data_str,
            sensitive["home"],
            context,
            report,
        )

    data_str = _replace_home_paths(data_str, context, report)
    data_str = _replace_user_words(data_str, context, report)
    data_str = _replace_uuid(data_str, context, report)
    data_str = _replace_ipv4(data_str, context, report)

    report.anonymized_length = len(data_str)
    report.payload_sha256 = hashlib.sha256(data_str.encode("utf-8")).hexdigest()
    return data_str, report


def _resolve_contextual_aliases(
    text: str,
    context: AnonymizationContext,
    allowed_aliases: Iterable[str] | None,
) -> str:
    if allowed_aliases is None:
        raise ResolutionError("allowed_aliases_required")
    observed = set(ALIAS_RE.findall(text))
    unknown = sorted(observed - set(context.reverse_map))
    if unknown:
        raise ResolutionError(f"unknown_or_semantic_alias:{','.join(unknown)}")
    unselected = sorted(observed - set(allowed_aliases))
    if unselected:
        raise ResolutionError(f"unselected_alias:{','.join(unselected)}")
    for token in sorted(observed, key=len, reverse=True):
        text = text.replace(token, context.reverse_map[token])
    return text


def _resolve_legacy_aliases(text: str) -> str:
    legacy_tokens = {"[USER]", "[HOSTNAME]", "[HOME]"}
    unresolved = sorted(set(ALIAS_RE.findall(text)) - legacy_tokens)
    if unresolved:
        raise ResolutionError("mapping_context_required:" + ",".join(unresolved))

    sensitive = _get_sensitive()
    replacements = {
        "[HOSTNAME]": sensitive.get("hostname"),
        "[HOME]": sensitive.get("home"),
        "[USER]": sensitive.get("username"),
    }
    for token, original in replacements.items():
        if original:
            text = text.replace(token, original)
    return text


def deanonymize(
    text: str,
    context: AnonymizationContext | None = None,
    allowed_aliases: Iterable[str] | None = None,
) -> str:
    """Resolve aliases locally while preserving the legacy primary tokens."""
    if not isinstance(text, str):
        return text
    if context is not None:
        return _resolve_contextual_aliases(text, context, allowed_aliases)
    return _resolve_legacy_aliases(text)


def display_anonymized_preview(
    data_str: str, report: AnonymizationReport, max_lines: int = 80
):
    """
    Wyświetla użytkownikowi zanonimizowane dane przed wysłaniem do LLM.
    Formatuje jako czytelny markdown z kolorami ANSI.
    """
    line_char = "\u2550" * 65
    print(f"\n{_C.CYAN}{_C.BOLD}{line_char}{_C.RESET}")
    print(
        f"{_C.CYAN}{_C.BOLD}  📋 DANE DIAGNOSTYCZNE (zanonimizowane) – wysyłane do LLM{_C.RESET}"
    )
    print(f"{_C.CYAN}{_C.BOLD}{line_char}{_C.RESET}")

    formatted = _format_diagnostics_markdown(data_str)

    lines = formatted.splitlines()
    if len(lines) > max_lines:
        half = max_lines // 2
        shown = (
            lines[:half]
            + [
                f"  {_C.DIM}...{_C.RESET}",
                f"  {_C.DIM}[skrócono – pełne dane wysyłane do LLM]{_C.RESET}",
                f"  {_C.DIM}...{_C.RESET}",
            ]
            + lines[-half:]
        )
    else:
        shown = lines

    max_width = 100
    for line in shown:
        rendered = _colorize_md_line(line)
        # Strip ANSI for length check, truncate raw if needed
        raw_len = len(re.sub(r"\033\[[^m]*m", "", rendered))
        if raw_len > max_width:
            # Truncate the original line (before colorizing) then re-colorize
            rendered = _colorize_md_line(line[: max_width - 3] + "...")
        print(f"  {rendered}")

    dash_char = "\u2500"
    dash_line = f"{_C.DIM}{dash_char * 65}{_C.RESET}"
    print(f"\n{dash_line}")
    print(f"{_C.BOLD}  🔒 Anonimizacja – co zostało ukryte:{_C.RESET}")
    for rep_line in report.summary().splitlines():
        print(f"{_C.GREEN}  {rep_line}{_C.RESET}")
    print(
        f"  {_C.DIM}Rozmiar: {report.original_length:,} → {report.anonymized_length:,} znaków{_C.RESET}"
    )
    print(f"  {_C.DIM}SHA-256 payloadu: {report.payload_sha256}{_C.RESET}")
    print(dash_line)


def _colorize_md_line(line: str) -> str:
    """Apply ANSI colors to a single markdown-formatted diagnostic line."""
    stripped = line.lstrip()

    # ### Section heading
    if stripped.startswith("### "):
        title = stripped[4:]
        return f"{_C.CYAN}{_C.BOLD}{line[: len(line) - len(stripped)]}### {title}{_C.RESET}"

    # ``` fence lines
    if stripped.startswith("```"):
        return f"{_C.DIM}{line}{_C.RESET}"

    # - **key**: `value`  or  - **key**: value
    if stripped.startswith("- **"):
        # bold key
        line = re.sub(
            r"\*\*([^*]+)\*\*",
            lambda m: f"{_C.BOLD}{_C.WHITE}{m.group(1)}{_C.RESET}",
            line,
        )
        # inline code value
        line = re.sub(
            r"`([^`]+)`", lambda m: f"{_C.CYAN}`{m.group(1)}`{_C.RESET}", line
        )
        return line

    # indented code content (inside ``` blocks rendered as plain lines)
    if (
        line.startswith("  ")
        and stripped
        and not stripped.startswith("-")
        and not stripped.startswith("#")
    ):
        return f"{_C.GREEN}{line}{_C.RESET}"

    # ... truncation markers
    if stripped.startswith("..."):
        return f"{_C.DIM}{line}{_C.RESET}"

    # inline code anywhere
    line = re.sub(r"`([^`]+)`", lambda m: f"{_C.CYAN}`{m.group(1)}`{_C.RESET}", line)
    return line


def _format_diagnostics_markdown(data_str: str) -> str:
    """Formatuje dane diagnostyczne jako czytelny markdown."""
    import ast

    # Próbuj sparsować jako dict
    try:
        data = ast.literal_eval(data_str)
        if isinstance(data, dict):
            return _dict_to_markdown(data)
    except (SyntaxError, ValueError):
        pass

    # Fallback: formatuj jako kod
    return f"```\n{data_str}\n```"


def _render_dict_list_value(key: str, value: list, prefix: str) -> list:
    """Render a list value as markdown lines."""
    if value and isinstance(value[0], dict):
        return [f"{prefix}- **{key}**: [{len(value)} elementów]"]
    if len(value) > 10:
        lines = [f"{prefix}- **{key}**:"]
        for item in value[:5]:
            lines.append(f"{prefix}  - {item}")
        lines.append(f"{prefix}  ... ({len(value) - 10} więcej)")
        for item in value[-5:]:
            lines.append(f"{prefix}  - {item}")
        return lines
    return [f"{prefix}- **{key}**: {value}"]


def _render_dict_long_string(key: str, value: str, prefix: str) -> list:
    """Render a long string (>200 chars) as a truncated code block."""
    lines = [f"{prefix}- **{key}**:", f"{prefix}  ```"]
    for line in value.split("\n")[:15]:
        lines.append(f"{prefix}  {line[:80]}")
    if value.count("\n") > 15:
        lines.append(f"{prefix}  ... ({value.count(chr(10)) - 15} więcej linii)")
    lines.append(f"{prefix}  ```")
    return lines


def _render_dict_multiline_string(key: str, value: str, prefix: str) -> list:
    """Render a multiline string as a code block."""
    lines = [f"{prefix}- **{key}**:", f"{prefix}  ```"]
    for line in value.split("\n")[:10]:
        lines.append(f"{prefix}  {line}")
    if value.count("\n") > 10:
        lines.append(f"{prefix}  ... ({value.count(chr(10)) - 10} więcej)")
    lines.append(f"{prefix}  ```")
    return lines


def _dict_to_markdown(data: dict, indent: int = 0) -> str:
    """Rekurencyjnie konwertuje dict na markdown."""
    lines = []
    prefix = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            section_title = _format_key_title(key)
            lines.append(f"\n{prefix}### {section_title}")
            lines.append(_dict_to_markdown(value, indent + 1))
        elif isinstance(value, list):
            lines.extend(_render_dict_list_value(key, value, prefix))
        elif isinstance(value, str) and len(value) > 200:
            lines.extend(_render_dict_long_string(key, value, prefix))
        elif isinstance(value, str) and "\n" in value:
            lines.extend(_render_dict_multiline_string(key, value, prefix))
        else:
            val_str = str(value)
            if len(val_str) > 60:
                val_str = val_str[:57] + "..."
            lines.append(f"{prefix}- **{key}**: `{val_str}`")

    return "\n".join(lines)


def _format_key_title(key: str) -> str:
    """Formatuje klucz dict jako czytelny tytuł."""
    titles = {
        "system": "🖥️ System",
        "audio": "🔊 Dźwięk",
        "thumbnails": "🖼️ Podglądy plików",
        "hardware": "🔧 Sprzęt",
        "disks": "💾 Dyski",
        "top_processes": "📊 Top procesy",
    }
    return titles.get(key, key.replace("_", " ").title())
