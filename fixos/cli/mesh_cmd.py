"""``fixos mesh`` — multi-vantage network diagnostics across interfaces and LAN/SSH peers."""

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


def parse_ports(ports_csv: str | None) -> tuple[int, ...] | None:
    if not ports_csv:
        return None
    parsed: list[int] = []
    for raw in ports_csv.split(","):
        raw = raw.strip()
        if not raw:
            continue
        port = int(raw)
        if not (1 <= port <= 65535):
            raise click.BadParameter(f"Port poza zakresem 1..65535: {port}")
        parsed.append(port)
    return tuple(parsed) if parsed else None


@click.command("mesh")
@click.argument("targets", nargs=-1)
@click.option(
    "--node",
    "nodes",
    multiple=True,
    help="Dodatkowy węzeł SSH do testu (np. user@host, maskfleet, 192.168.188.108)",
)
@click.option(
    "--ports",
    "ports_csv",
    default=None,
    help="Lista portów TCP po przecinku (domyślnie: 631,9100,515,80,443)",
)
@click.option(
    "--discover/--no-discover",
    default=True,
    help="Automatycznie wykrywaj urządzenia w sieci LAN/mDNS/Tailscale/SSH",
)
@click.option(
    "--ssh/--no-ssh",
    "probe_ssh",
    default=True,
    help="Wykonuj nieinteraktywne zdalne testy SSH (BatchMode=yes) z węzłów mesh",
)
@click.option(
    "--all-interfaces",
    is_flag=True,
    help="Uwzględnij też wirtualne mosty kontenerów (docker/br-/virbr)",
)
@click.option("--json", "as_json", is_flag=True, help="Wynik w formacie JSON")
def mesh(
    targets: tuple[str, ...],
    nodes: tuple[str, ...],
    ports_csv: str | None,
    discover: bool,
    probe_ssh: bool,
    all_interfaces: bool,
    as_json: bool,
) -> None:
    """
    Diagnostyka sieci mesh — testuje osiągalność hosta z każdego urządzenia i interfejsu.

    \b
    Sprawdza wskazany adres hosta (lub skonfigurowane drukarki sieciowe, gdy nie
    podano argumentu) z każdego lokalnego interfejsu IPv4 oraz z wykrytych węzłów
    LAN / Tailscale / SSH, a także weryfikuje multicast mDNS i bramę domyślną SNMP.

    \b
    Przykłady:
      fixos mesh 192.168.188.158
      fixos mesh BRN3C2AF4E8C6F8.local --node maskfleet
      fixos mesh --ports 631,9100,80 192.168.188.158
      fixos mesh --json 192.168.188.158
    """
    from fixos.plugins.builtin.mesh import Plugin

    ports = parse_ports(ports_csv)
    plugin = Plugin(
        targets=list(targets),
        nodes=list(nodes),
        ports=ports,
        discover_peers=discover,
        probe_ssh=probe_ssh,
        include_virtual_interfaces=all_interfaces,
    )
    result = plugin.diagnose()

    if as_json:
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    render_mesh_result(result)


def render_mesh_result(result: DiagnosticResult) -> None:
    mesh_nodes = result.raw_data.get("mesh_nodes", [])
    targets = result.raw_data.get("targets", [])
    click.echo(
        click.style(
            f"Diagnostyka mesh — węzły/interfejsy ({len(mesh_nodes)}):",
            fg="cyan",
            bold=True,
        )
    )

    for entry in targets:
        target = entry.get("target", "?")
        resolved = entry.get("resolved_ip") or "nierozwiązany"
        click.echo(
            f"\nCel: {click.style(str(target), bold=True)}  [IP: {resolved}]"
        )
        snmp = entry.get("snmp")
        if isinstance(snmp, dict):
            gw = snmp.get("default_gateway")
            gw_str = (
                click.style(str(gw), fg="red", bold=True)
                if gw == "0.0.0.0"
                else str(gw or "?")
            )
            descr = snmp.get("sys_descr") or "SNMP"
            mask = snmp.get("netmask") or "?"
            click.echo(f"  SNMP: {descr} | maska: {mask} | brama: {gw_str}")

        for item in entry.get("results", []):
            mode = item.get("mode", "active")
            open_ports = item.get("open_ports") or []
            closed_ports = item.get("closed_ports") or []
            reachable = (
                bool(open_ports)
                if (open_ports or closed_ports)
                else bool(item.get("ping_ok"))
            )
            if mode == "passive":
                badge = click.style("[PASYWNY]", fg="cyan")
            elif reachable:
                badge = click.style("[OK]     ", fg="green")
            else:
                badge = click.style("[BŁĄD]   ", fg="red")

            latency = (
                f" ({item['latency_ms']:.1f} ms)"
                if item.get("latency_ms") is not None
                else ""
            )
            ports_info = (
                f"porty={open_ports}"
                if open_ports
                else ("brak otwartych portów" if mode == "active" else "")
            )
            same_sub = item.get("same_subnet")
            sub_info = (
                "ta sama podsieć"
                if same_sub is True
                else ("inna podsieć" if same_sub is False else "")
            )
            mdns_parts = []
            if item.get("mdns_unicast_ok") is not None:
                mdns_parts.append(
                    f"unicast={'OK' if item['mdns_unicast_ok'] else 'brak'}"
                )
            if item.get("mdns_multicast_ok") is not None:
                mdns_parts.append(
                    f"multicast={'OK' if item['mdns_multicast_ok'] else 'brak'}"
                )
            mdns_info = f"mDNS({', '.join(mdns_parts)})" if mdns_parts else ""
            note = item.get("note") or ""
            details = " | ".join(
                p for p in (ports_info + latency, sub_info, mdns_info, note) if p
            )
            click.echo(f"  {badge} {item['node_id']} -> {details}")

    if not result.findings:
        click.echo(click.style("\nBrak problemów w sieci mesh.", fg="green"))
        return

    for finding in result.findings:
        color = _COLORS.get(finding.severity, "white")
        click.echo(
            "\n"
            + click.style(
                f"[{finding.severity.value.upper()}] {finding.title}", fg=color
            )
        )
        click.echo(f"  {finding.description}")
        if finding.suggestion:
            click.echo(f"  Sugestia: {finding.suggestion}")
        if finding.command:
            click.echo(f"  Naprawa: {click.style(finding.command, fg='cyan')}")
