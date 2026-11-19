"""
Features CLI command for fixOS.
Manage packages and system features based on user profiles.
"""

from __future__ import annotations

import json
from typing import Any

import click

from ..constants import UI_BORDER_WIDTH
from ..features import SystemDetector
from ..features.auditor import FeatureAuditor
from ..features.catalog import PackageCatalog, PackageInfo
from ..features.installer import FeatureInstaller
from ..features.profiles import UserProfile
from ..features.renderer import FeatureRenderer
from ..utils.terminal import console


def _print_features_heading(title: str) -> None:
    """Render a consistent Rich section heading."""
    console.print()
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print(f"[cyan]{'═' * min(UI_BORDER_WIDTH, 60)}[/cyan]")
    console.print()


def _print_unknown_profile(profile: str) -> None:
    console.print(f"[red]❌ Profil '{profile}' nie istnieje.[/red]")
    console.print(f"Dostępne profile: {', '.join(UserProfile.list_available())}")


@click.group(name="features")
def features() -> None:
    """Zarządzanie pakietami komfortu systemu."""


@features.command("audit")
@click.option(
    "--profile", "-p", help="Profil użytkownika (developer, sysadmin, gamer, itd.)"
)
@click.option("--json-output", is_flag=True, help="Output JSON")
def features_audit(profile: str | None, json_output: bool) -> None:
    """Sprawdź brakujące pakiety dla profilu."""
    system = SystemDetector().detect()

    selected_profile = profile or _interactive_profile_select()

    try:
        prof = UserProfile.load(selected_profile)
    except FileNotFoundError:
        _print_unknown_profile(selected_profile)
        return

    catalog = PackageCatalog.load()
    auditor = FeatureAuditor(catalog, system)
    result = auditor.audit(prof)

    if json_output:
        click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        FeatureRenderer.render_audit(result)


def _show_install_plan(
    to_install: list[PackageInfo], yes: bool, dry_run: bool
) -> bool:
    """Display install plan and ask for confirmation. Returns False to abort."""
    console.print()
    console.print(f"[bold cyan]Zostaną zainstalowane {len(to_install)} pakiety:[/bold cyan]")
    for pkg in to_install[:10]:
        console.print(f"  • [bold]{pkg.id}[/bold] — {pkg.description[:50]}")
    if len(to_install) > 10:
        console.print(f"  ... i {len(to_install) - 10} więcej")
    console.print()
    if not yes and not dry_run and not click.confirm("Kontynuować instalację?"):
        console.print("[yellow]Anulowano.[/yellow]")
        return False
    return True


def _show_install_results(install_result: dict[str, Any]) -> None:
    """Display installation results summary."""
    console.print()
    installed = install_result.get("installed", [])
    failed = install_result.get("failed", [])
    skipped = install_result.get("skipped", [])
    if installed:
        console.print(f"[green]✅ Zainstalowano: {len(installed)}[/green]")
    if failed:
        console.print(f"[red]❌ Nie udało się: {len(failed)}[/red]")
        for pkg_id in failed[:5]:
            console.print(f"   - {pkg_id}")
    if skipped:
        console.print(f"[yellow]⏭️ Pominięto: {len(skipped)}[/yellow]")
    console.print()


@features.command("install")
@click.option("--profile", "-p", required=True, help="Profil użytkownika")
@click.option("--dry-run", is_flag=True, help="Symulacja bez instalacji")
@click.option("--yes", "-y", is_flag=True, help="Bez potwierdzenia")
@click.option("--category", "-c", multiple=True, help="Tylko wybrane kategorie")
def features_install(
    profile: str,
    dry_run: bool,
    yes: bool,
    category: tuple[str, ...],
) -> None:
    """Zainstaluj brakujące pakiety dla profilu."""
    system = SystemDetector().detect()

    try:
        prof = UserProfile.load(profile)
    except FileNotFoundError:
        _print_unknown_profile(profile)
        return

    catalog = PackageCatalog.load()
    auditor = FeatureAuditor(catalog, system)
    result = auditor.audit(prof)

    to_install: list[PackageInfo] = list(result.missing) + list(result.repos_needed)
    if category:
        allowed_categories = set(category)
        to_install = [p for p in to_install if p.category in allowed_categories]

    if not to_install:
        console.print("[green]✅ Wszystkie pakiety z profilu są zainstalowane![/green]")
        return

    if not _show_install_plan(to_install, yes, dry_run):
        return

    installer = FeatureInstaller(system, dry_run=dry_run)
    _show_install_results(installer.install(to_install))


@features.command("profiles")
def features_profiles() -> None:
    """Lista dostępnych profili."""
    profiles = UserProfile.list_available()

    _print_features_heading("📋 Dostępne profile:")

    for profile_name in profiles:
        try:
            prof = UserProfile.load(profile_name)
            console.print(
                f"  {prof.icon}  [bold]{prof.name:15s}[/bold]  {prof.description}"
            )
        except (OSError, ValueError, KeyError, TypeError):
            console.print(f"  📦  [bold]{profile_name:15s}[/bold]  (błąd ładowania)")

    console.print()


@features.command("system")
def features_system() -> None:
    """Pokaż wykryty system."""
    system = SystemDetector().detect()
    FeatureRenderer.render_system_info(system)


def _interactive_profile_select() -> str:
    """Interactive profile selection."""
    profiles = UserProfile.list_available()

    _print_features_heading("Wybierz profil:")

    for i, profile_name in enumerate(profiles, 1):
        try:
            prof = UserProfile.load(profile_name)
            console.print(f"  [{i}] {prof.icon} {prof.name} - {prof.description}")
        except (OSError, ValueError, KeyError, TypeError):
            console.print(f"  [{i}] 📦 {profile_name}")

    console.print()

    while True:
        choice = console.input("Wybór (numer lub nazwa): ").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(profiles):
                return profiles[idx]
            console.print("[red]Nieprawidłowy numer.[/red]")
            continue

        if choice in profiles:
            return choice

        matches = [p for p in profiles if choice.lower() in p.lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            console.print(f"[yellow]Dopasowania: {', '.join(matches)}[/yellow]")
        else:
            console.print(f"[red]Nie znaleziono profilu '{choice}'[/red]")
