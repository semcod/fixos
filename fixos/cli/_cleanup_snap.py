"""Snap package management CLI handlers."""

from __future__ import annotations

import subprocess

import click

from fixos.cli._cleanup_utils import _format_bytes, _parse_numeric_range_set


_SNAP_CORE_PACKAGES = {"core", "core18", "core20", "core22", "snapd"}


def _snap_fetch_packages(analyzer) -> list:
    """Return snap package list from analyzer or live snap CLI."""
    packages = getattr(analyzer, "snap_packages", [])
    if packages:
        return packages
    try:
        result = subprocess.run(
            ["snap", "list", "--all"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            packages = []
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    packages.append(
                        {
                            "name": parts[0],
                            "version": parts[1],
                            "rev": parts[2],
                            "size": 0,
                            "disabled": "disabled" in line.lower(),
                        }
                    )
    except Exception:
        pass
    return packages


def _run_snap_remove(pkg_name: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sudo", "snap", "remove", pkg_name],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _snap_remove_packages(packages_to_remove: list) -> None:
    """Execute snap remove for each package and report results."""
    click.echo(
        f"\n{click.style('🚀 ODINSTALOWYWANIE PAKIETÓW SNAP:', fg='cyan', bold=True)}"
    )
    for pkg in packages_to_remove:
        click.echo(f"\n• {pkg['name']} (v{pkg['version']})")
        try:
            result = _run_snap_remove(pkg["name"])
            if result.returncode == 0:
                click.echo(click.style("  ✅ Odinstalowano", fg="green"))
            else:
                click.echo(click.style(f"  ❌ Błąd: {result.stderr[:100]}", fg="red"))
        except Exception as e:
            click.echo(click.style(f"  ❌ Błąd: {e}", fg="red"))


def _snap_display_packages(active_packages: list) -> None:
    """Print numbered list of active snap packages."""
    click.echo(
        f"\n{click.style('📦 ZAINSTALOWANE PAKIETY SNAP:', fg='magenta', bold=True)}"
    )
    click.echo(click.style("Wybierz numery pakietów do odinstalowania", fg="white"))
    for i, pkg in enumerate(active_packages, 1):
        size_str = (
            _format_bytes(pkg.get("size", 0)) if pkg.get("size", 0) > 0 else "? MB"
        )
        click.echo(
            f"  [{i:3d}] {click.style(pkg['name'], fg='yellow')} (v{pkg['version']}, rev {pkg['rev']}): {size_str}"
        )
    click.echo(f"\n  💰 Łącznie pakietów: {len(active_packages)}")


def _snap_select_packages(active_packages: list) -> list:
    """Prompt user to select packages; return list to remove or empty."""
    nums = click.prompt(
        click.style("\nWybierz numery do odinstalowania (np. 1,3,5-10)", fg="cyan"),
        default="",
    )
    if not nums.strip():
        click.echo(click.style("⏭️ Nie wybrano żadnych pakietów.", fg="yellow"))
        return []
    selected_indices = _parse_numeric_range_set(nums)
    packages_to_remove = [
        active_packages[i - 1]
        for i in selected_indices
        if 1 <= i <= len(active_packages)
    ]
    if not packages_to_remove:
        click.echo(click.style("❌ Nie wybrano żadnych pakietów.", fg="red"))
    return packages_to_remove


def _snap_warn_dangerous(packages_to_remove: list) -> None:
    """Warn if any selected package is a core snap component."""
    dangerous = [p for p in packages_to_remove if p["name"] in _SNAP_CORE_PACKAGES]
    if dangerous:
        click.echo(
            click.style(
                "\n⚠️ UWAGA: Wybrane pakiety zawierają komponenty systemowe:",
                fg="red",
                bold=True,
            )
        )
        for pkg in dangerous:
            click.echo(f"  • {pkg['name']}")
        click.echo(
            click.style(
                "Ich usunięcie może wpłynąć na działanie innych pakietów Snap!",
                fg="red",
            )
        )


def _handle_snap_management(analyzer, dry_run: bool) -> None:
    """Handle Snap package management selection."""
    snap_packages = _snap_fetch_packages(analyzer)
    if not snap_packages:
        click.echo(
            click.style(
                "\n❌ Brak zainstalowanych pakietów Snap lub snapd niedostępny.",
                fg="red",
            )
        )
        return

    active_packages = [p for p in snap_packages if not p.get("disabled", False)]
    if not active_packages:
        click.echo(
            click.style(
                "\n❌ Brak aktywnych pakietów Snap do odinstalowania.", fg="red"
            )
        )
        return

    _snap_display_packages(active_packages)
    packages_to_remove = _snap_select_packages(active_packages)
    if not packages_to_remove:
        return

    click.echo(
        f"\n{click.style('📦 WYBRANE PAKIETY DO ODINSTALOWANIA:', fg='red', bold=True)}"
    )
    for i, pkg in enumerate(packages_to_remove, 1):
        click.echo(
            f"  {i:3d}. {click.style(pkg['name'], fg='yellow')} (v{pkg['version']})"
        )

    _snap_warn_dangerous(packages_to_remove)

    if dry_run:
        click.echo(
            click.style("\n[DRY-RUN] - symulacja, nic nie zostanie usunięte", fg="cyan")
        )
        return
    if not click.confirm(
        click.style("\n⚠️ Potwierdzasz odinstalowanie tych pakietów?", fg="yellow"),
        default=False,
    ):
        click.echo(click.style("⏭️ Anulowano.", fg="yellow"))
        return

    _snap_remove_packages(packages_to_remove)
