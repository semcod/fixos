"""CLI subcommand for the FixOS Model Context Protocol (MCP) server."""

from __future__ import annotations

import json
import sys

import click


@click.command("mcp")
@click.option(
    "--catalog",
    is_flag=True,
    default=False,
    help="Wypisz katalog operacji MCP URI (wellmanifest/mcp) jako JSON i zakończ",
)
@click.option(
    "--tools",
    is_flag=True,
    default=False,
    help="Wypisz listę narzędzi MCP (tools/list) jako JSON i zakończ",
)
@click.option(
    "--config",
    "print_config",
    is_flag=True,
    default=False,
    help="Wypisz przykładową konfigurację mcpServers dla klienta MCP i zakończ",
)
@click.option(
    "--plan",
    "plan_task",
    type=str,
    default="",
    help="Zaplanuj operację URI na podstawie opisu w języku naturalnym (bez wykonania)",
)
def mcp_cmd(catalog: bool, tools: bool, print_config: bool, plan_task: str) -> None:
    """Uruchom serwer Model Context Protocol (MCP) przez stdio (JSON-RPC 2.0)."""
    from fixos.mcp_server import (
        mcp_tools_list,
        registry_search,
        serve_stdio,
        task_plan,
    )

    if catalog:
        click.echo(json.dumps(registry_search(), indent=2, ensure_ascii=False))
        return
    if tools:
        click.echo(json.dumps({"tools": mcp_tools_list()}, indent=2, ensure_ascii=False))
        return
    if print_config:
        cfg = {
            "mcpServers": {
                "fixos": {
                    "command": sys.executable,
                    "args": ["-m", "fixos.mcp_server"],
                }
            }
        }
        click.echo(json.dumps(cfg, indent=2, ensure_ascii=False))
        return
    if plan_task:
        click.echo(json.dumps(task_plan(plan_task), indent=2, ensure_ascii=False))
        return

    raise SystemExit(serve_stdio())
