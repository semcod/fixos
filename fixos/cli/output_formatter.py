"""
Centralized output formatter for fixOS CLI.

Supports human-readable (default), JSON, and YAML output formats.
In YAML/JSON mode, all status/progress output goes to stderr,
keeping stdout clean for machine-parseable data.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TextIO

import yaml

import click

from fixos import __version__


class OutputFormat(Enum):
    """Supported output formats."""

    HUMAN = "human"
    JSON = "json"
    YAML = "yaml"


def _yaml_str_representer(dumper: yaml.Dumper, data: str) -> yaml.Node:
    """Use literal block style for multi-line strings in YAML output."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Register the custom string representer
yaml.add_representer(str, _yaml_str_representer)


class OutputFormatter:
    """
    Centralized output formatter for fixOS CLI commands.

    Usage:
        fmt = OutputFormatter.from_flags(yaml_output=True, json_output=False)
        fmt.status("Zbieranie diagnostyki...")      # → stderr
        fmt.emit(diagnostics_data)                  # → stdout (YAML)
    """

    def __init__(self, fmt: OutputFormat = OutputFormat.HUMAN) -> None:
        self.fmt = fmt

    @classmethod
    def from_flags(
        cls,
        yaml_output: bool = False,
        json_output: bool = False,
    ) -> "OutputFormatter":
        """Create formatter from CLI flag values. YAML takes precedence over JSON."""
        if yaml_output:
            return cls(OutputFormat.YAML)
        if json_output:
            return cls(OutputFormat.JSON)
        return cls(OutputFormat.HUMAN)

    @property
    def is_machine(self) -> bool:
        """True if output is machine-parseable (YAML or JSON)."""
        return self.fmt in (OutputFormat.YAML, OutputFormat.JSON)

    # ── Status / progress (always stderr in machine mode) ─────

    def status(self, msg: str, fg: Optional[str] = None, bold: bool = False) -> None:
        """Print a status/progress message. Goes to stderr in machine mode."""
        if self.is_machine:
            click.echo(msg, err=True)
        else:
            click.echo(click.style(msg, fg=fg, bold=bold) if fg else msg)

    def progress(self, name: str, desc: str) -> None:
        """Print a progress line for diagnostic module collection."""
        self.status(f"  → {desc}...")

    def banner(self, text: str) -> None:
        """Print banner. Suppressed in machine mode."""
        if not self.is_machine:
            click.echo(click.style(text, fg="cyan"))

    # ── Data output (always stdout) ───────────────────────────

    def emit(self, data: Any, stream: TextIO = sys.stdout) -> None:
        """Emit structured data to stdout in the configured format."""
        content = self.format_data(data)
        click.echo(content, file=stream)

    def format_data(self, data: Any) -> str:
        """Format data dict/list as string in the configured format."""
        if self.fmt == OutputFormat.YAML:
            return self._to_yaml(data)
        if self.fmt == OutputFormat.JSON:
            return self._to_json(data)
        # HUMAN: fallback to repr (callers usually handle human display themselves)
        return str(data)

    # ── Diagnostics-specific helpers ──────────────────────────

    def format_diagnostics(
        self,
        data: dict,
        *,
        timestamp: Optional[str] = None,
        modules: Optional[list[str]] = None,
    ) -> str:
        """Format full diagnostic result with metadata envelope."""
        envelope = {
            "fixos_version": __version__,
            "timestamp": timestamp or datetime.now().isoformat(),
            "format": self.fmt.value,
        }
        if modules:
            envelope["modules"] = modules
        envelope["diagnostics"] = data

        return self.format_data(envelope)

    def format_scan_result(
        self,
        data: dict,
        *,
        disk_analysis: Optional[dict] = None,
    ) -> str:
        """Format scan results with optional disk analysis."""
        result: dict[str, Any] = {
            "fixos_version": __version__,
            "timestamp": datetime.now().isoformat(),
            "scan": data,
        }
        if disk_analysis:
            result["disk_analysis"] = disk_analysis
        return self.format_data(result)

    # ── Private serializers ───────────────────────────────────

    @staticmethod
    def _to_yaml(data: Any) -> str:
        """Serialize data to YAML string."""
        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        ).rstrip()

    @staticmethod
    def _to_json(data: Any) -> str:
        """Serialize data to JSON string."""
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
