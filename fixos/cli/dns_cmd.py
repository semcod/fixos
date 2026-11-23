"""``fixos dns`` — deterministic DNS diagnostics and repair (systemd-resolved / NetworkManager)."""

from __future__ import annotations

import json

import click

from fixos.plugins.base import DiagnosticResult, Severity

_COLORS = {
    Severity.CRITICAL: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
    Severity.OK: "green",
}


def _parse_csv(raw_value: str | None) -> tuple[str, ...] | None:
    if not raw_value:
        return None
    items = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    return items or None


@click.command("dns")
@click.option("--fix", "apply_fix", is_flag=True, help="Wykonaj deterministyczną naprawę DNS")
@click.option("--yes", "-y", is_flag=True, help="Nie pytaj przed wykonaniem naprawy")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Pokaż plan naprawy bez modyfikowania konfiguracji systemu",
)
@click.option(
    "--host",
    "hosts",
    multiple=True,
    help="Host do przetestowania rozwiązywania DNS (można podać wielokrotnie)",
)
@click.option(
    "--dns",
    "upstream_dns_csv",
    default=None,
    help="Nadrzędne serwery DNS po przecinku (domyślnie: 1.1.1.1,8.8.8.8)",
)
@click.option("--json", "as_json", is_flag=True, help="Wynik w formacie JSON")
def dns(
    apply_fix: bool,
    yes: bool,
    dry_run: bool,
    hosts: tuple[str, ...],
    upstream_dns_csv: str | None,
    as_json: bool,
) -> None:
    """
    Diagnostyka i deterministyczna naprawa DNS (systemd-resolved, NetworkManager).

    \b
    Sprawdza /etc/resolv.conf, licznik timeoutów w systemd-resolved, konfigurację
    interfejsów domyślnych (router-only DNS) oraz czas rozwiązywania nazw hostów.

    \b
    Przykłady:
      fixos dns                        # szybka diagnoza DNS
      fixos dns --fix --dry-run        # podgląd planu naprawy bez zmian
      fixos dns --fix --yes            # zastosuj drop-in systemd-resolved + nmcli
      fixos dns --json                 # wynik maszynowy JSON
    """
    from fixos.plugins.builtin.dns import (
        DEFAULT_UPSTREAM_DNS,
        Plugin,
        apply_dns_repair,
        build_repair_plan,
    )

    upstream_dns = _parse_csv(upstream_dns_csv) or DEFAULT_UPSTREAM_DNS
    plugin = Plugin(probe_hosts=hosts or None, upstream_dns=upstream_dns)
    result = plugin.diagnose()

    repair_results: list[dict] = []
    if apply_fix or dry_run:
        plan = build_repair_plan(
            status=result.raw_data.get("status", {}),
            nm_connections=result.raw_data.get("nm_connections", {}),
            upstream_dns=upstream_dns,
        )
        should_execute = True
        if not dry_run and not yes and not as_json:
            click.echo(click.style("\nPlan naprawy DNS:", fg="cyan", bold=True))
            for item in plan:
                click.echo(f"  - {item['description']}")
            should_execute = click.confirm("Wykonać powyższy plan naprawy DNS?", default=True)
        if should_execute:
            repair_results = apply_dns_repair(plan, dry_run=dry_run)

    if as_json:
        payload = result.to_dict()
        if repair_results:
            payload["repair_results"] = repair_results
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    render_dns_result(result)
    if repair_results:
        click.echo()
        title = "Podgląd naprawy DNS (dry-run):" if dry_run else "Wyniki naprawy DNS:"
        click.echo(click.style(title, fg="cyan", bold=True))
        for step in repair_results:
            mark = click.style("✓", fg="green") if step["ok"] else click.style("✗", fg="red")
            click.echo(f"  {mark} {step['description']}")
            if step.get("command"):
                click.echo(f"      {click.style(step['command'], fg='bright_black')}")
            if not step["ok"] and step.get("output"):
                click.echo(f"      {click.style(step['output'], fg='red')}")


def render_dns_result(result: DiagnosticResult) -> None:
    """Render DNS diagnostic findings and probe summary to the terminal."""
    color = _COLORS.get(result.status, "white")
    click.echo(
        click.style(
            f"Diagnostyka DNS — status: {result.status.value.upper()} ({result.duration_ms:.0f} ms)",
            fg=color,
            bold=True,
        )
    )
    stats = result.raw_data.get("statistics", {})
    if stats:
        click.echo(
            f"  systemd-resolved: transakcje={stats.get('total_transactions', 0)}, "
            f"timeouty={stats.get('total_timeouts', 0)}, "
            f"cache_hits={stats.get('cache_hits', 0)}"
        )
    probes = result.raw_data.get("probes", [])
    for probe in probes:
        icon = click.style("✓", fg="green") if probe["ok"] else click.style("✗", fg="red")
        detail = (
            f"{', '.join(probe['addresses'][:2])} ({probe['latency_ms']:.0f} ms)"
            if probe["ok"]
            else str(probe["error"])
        )
        click.echo(f"  {icon} {probe['host']}: {detail}")

    click.echo()
    for finding in result.findings:
        f_color = _COLORS.get(finding.severity, "white")
        click.echo(
            f"[{click.style(finding.severity.value.upper(), fg=f_color, bold=True)}] "
            f"{finding.title}"
        )
        click.echo(f"  {finding.description}")
        if finding.suggestion:
            click.echo(f"  Sugestia: {finding.suggestion}")
