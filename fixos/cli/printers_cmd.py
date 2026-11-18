"""``fixos printers`` — diagnose and repair printing (CUPS / Windows spooler)."""

from __future__ import annotations

import json

import click

from fixos.plugins.base import Severity

_COLORS = {
    Severity.CRITICAL: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
    Severity.OK: "green",
}


@click.command("printers")
@click.option("--fix", "apply_fix", is_flag=True, help="Wykonaj proponowane naprawy")
@click.option("--yes", "-y", is_flag=True, help="Nie pytaj przed każdą naprawą")
@click.option(
    "--scan",
    is_flag=True,
    help="Przeskanuj lokalną sieć /24, by odnaleźć drukarkę po adresie MAC",
)
@click.option(
    "--mesh",
    "run_mesh",
    is_flag=True,
    help="Przetestuj osiągalność drukarki z każdego interfejsu i węzła w sieci mesh",
)
@click.option(
    "--node",
    "mesh_nodes",
    multiple=True,
    help="Dodatkowy węzeł SSH dla --mesh (np. user@host, maskfleet)",
)
@click.option(
    "--test-print", "test_queue", default=None, help="Wydrukuj stronę testową"
)
@click.option("--json", "as_json", is_flag=True, help="Wynik w formacie JSON")
def printers(
    apply_fix, yes, scan, run_mesh, mesh_nodes, test_queue, as_json
) -> None:
    """
    Diagnostyka i naprawa drukarek (Linux/macOS: CUPS, Windows: Spooler).

    \b
    Wykrywa m.in. nierozwiązywalną nazwę drukarki sieciowej (np. BRN…),
    nieosiągalny port, wstrzymane kolejki, zablokowane zadania oraz
    przestarzały sterownik, gdy drukarka obsługuje IPP Everywhere.

    \b
    Przykłady:
      fixos printers                       # diagnoza
      fixos printers --scan                # szukaj drukarki w sieci po MAC
      fixos printers --mesh                # test z każdego interfejsu i węzła mesh
      fixos printers --fix                 # napraw (z potwierdzeniem)
      fixos printers --test-print NAZWA    # strona testowa
    """
    from fixos.plugins.builtin.printers import Plugin

    plugin = Plugin(sweep=scan)
    result = plugin.diagnose()
    mesh_result = None

    if run_mesh or mesh_nodes:
        from fixos.plugins.builtin.mesh import Plugin as MeshPlugin
        from fixos.plugins.builtin.printers import PrinterQueue

        printer_targets: list[str] = []
        for queue in result.raw_data.get("queues", []):
            candidate = (
                queue.get("address")
                or queue.get("located_address")
                or PrinterQueue(
                    name=str(queue.get("name") or ""),
                    uri=str(queue.get("uri") or ""),
                ).host
            )
            if candidate and candidate not in printer_targets:
                printer_targets.append(candidate)
        mesh_plugin = MeshPlugin(
            targets=printer_targets or None,
            nodes=list(mesh_nodes),
            discover_peers=True,
            probe_ssh=True,
        )
        mesh_result = mesh_plugin.diagnose()

    if as_json:
        payload = result.to_dict()
        if mesh_result is not None:
            payload["mesh"] = mesh_result.to_dict()
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _render(result)
        if mesh_result is not None:
            from fixos.cli.mesh_cmd import render_mesh_result

            click.echo()
            render_mesh_result(mesh_result)

    failed = 0
    if apply_fix:
        from fixos.plugins.builtin.printer_repairs import execute_repair

        for finding in result.findings:
            repair_spec = (finding.data or {}).get("repair")
            if (
                not (finding.command or repair_spec)
                or finding.severity not in (Severity.CRITICAL, Severity.WARNING)
            ):
                continue
            preview = finding.command or str(repair_spec)
            click.echo(
                f"\n→ {finding.title}\n  {click.style(preview, fg='cyan')}"
            )
            if not yes and not click.confirm("  Wykonać?", default=True):
                continue
            ok, rc, err_msg = execute_repair(repair_spec)
            if ok:
                click.echo(click.style("  OK", fg="green"))
            else:
                failed += 1
                click.echo(
                    click.style(
                        f"  FAIL ({rc}): {err_msg[:300]}", fg="red"
                    )
                )

    if test_queue:
        ok, message = plugin.test_print(test_queue)
        click.echo(
            click.style(f"\nStrona testowa: {message}", fg="green" if ok else "red")
        )
        failed += 0 if ok else 1

    if failed:
        raise SystemExit(1)


def _render(result) -> None:
    queues = result.raw_data.get("queues", [])
    click.echo(click.style(f"Drukarki ({len(queues)}):", fg="cyan", bold=True))
    for queue in queues:
        address = queue.get("address") or queue.get("located_address") or "?"
        click.echo(f"  • {queue['name']}  {queue['uri']}  [{address}]")
        if queue.get("model"):
            click.echo(f"      sterownik: {queue['model']}")
    if not result.findings:
        click.echo(click.style("\nBrak problemów.", fg="green"))
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
