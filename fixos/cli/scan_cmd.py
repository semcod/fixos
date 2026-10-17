"""
Scan command for fixOS CLI - system diagnostics
"""

import click
import json
from pathlib import Path
from fixos.cli.shared import add_shared_options, BANNER
from fixos.cli.output_formatter import OutputFormatter


@click.command()
@click.option(
    "--audio", "modules", flag_value="audio", help="Tylko diagnostyka dźwięku"
)
@click.option(
    "--thumbnails", "modules", flag_value="thumbnails", help="Tylko podglądy plików"
)
@click.option("--hardware", "modules", flag_value="hardware", help="Tylko sprzęt")
@click.option("--system", "modules", flag_value="system", help="Tylko system")
@click.option(
    "--security", "modules", flag_value="security", help="Tylko bezpieczeństwo"
)
@click.option(
    "--resources",
    "modules",
    flag_value="resources",
    help="Tylko zasoby (CPU/RAM/procesy)",
)
@click.option(
    "--packages",
    "modules",
    flag_value="packages",
    help="Tylko pakiety (nieużywane/osierocone)",
)
@click.option(
    "--storage",
    "modules",
    flag_value="storage",
    help="Tylko dyski/partycje (resize/optymalizacja)",
)
@click.option(
    "--files", "modules", flag_value="files", help="Tylko pliki (duże/duplikaty/media)"
)
@click.option(
    "--all",
    "modules",
    flag_value="all",
    default=True,
    help="Wszystkie moduły (domyślnie)",
)
@add_shared_options
@click.option(
    "--no-banner", "no_banner", is_flag=True, default=False, help="Ukryj baner fixos"
)
@click.option("--output", "-o", default=None, help="Zapisz wyniki do pliku")
@click.option(
    "--profile",
    "-p",
    default=None,
    help="Profil diagnostyczny (server/desktop/developer/minimal)",
)
@click.option(
    "--modules-list",
    "-M",
    "modules_csv",
    default=None,
    help="Moduły diagnostyki (CSV): audio,thumbnails,hardware,system,security,resources,packages,storage,files",
)
def scan(
    modules: str,
    output: str,
    show_raw: bool,
    no_banner: bool,
    disc: bool,
    dry_run: bool,
    interactive: bool,
    json_output: bool,
    yaml_output: bool,
    llm_fallback: bool,
    profile: str,
    modules_csv: str,
) -> None:
    """
    Przeprowadza diagnostykę systemu.

    \\b
    Formaty wyjścia:
      (domyślny)    – Human-readable z kolorami
      --json        – Wyjście w formacie JSON
      --yaml        – Wyjście w formacie YAML (pipe-safe)

    \\b
    Tryb pipeline (synchroniczny):
      fixos scan --yaml                         # pełna diagnostyka → YAML
      fixos scan --yaml -M audio                # tylko audio → YAML
      fixos scan --yaml | yq .diagnostics.audio # pipe do yq

    \\b
    Przykłady:
      fixos scan                    # pełna diagnostyka
      fixos scan --disc             # z analizą dysku
      fixos scan --disc --json      # analiza dysku w JSON
      fixos scan --audio            # tylko diagnostyka dźwięku
      fixos scan --profile server   # profil serwera
      fixos scan --yaml -o scan.yml # YAML do pliku
    """
    from fixos.diagnostics import get_full_diagnostics

    fmt = OutputFormatter.from_flags(yaml_output=yaml_output, json_output=json_output)

    if not no_banner:
        fmt.banner(BANNER)

    # Resolve modules selection
    selected_modules = _resolve_modules(modules, modules_csv, profile, fmt)

    if disc and modules == "all" and not modules_csv:
        data = {}
    else:
        fmt.status("Zbieranie diagnostyki...", fg="yellow")
        data = get_full_diagnostics(selected_modules, progress_callback=fmt.progress)

    if disc:
        _run_disk_analysis(data, fmt=fmt, json_output=False, is_fix_mode=False)

    # ── Machine-parseable output (YAML / JSON) ───────────────
    if fmt.is_machine:
        content = fmt.format_diagnostics(
            data,
            modules=selected_modules,
        )
        click.echo(content)
        if output:
            Path(output).write_text(content + "\n", encoding="utf-8")
            fmt.status(f"Zapisano: {output}", fg="green")
        return

    # ── Human-readable output ─────────────────────────────────
    if show_raw:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(click.style("Diagnostyka zakończona.", fg="green"))

    if output:
        try:
            Path(output).write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            click.echo(click.style(f"Zapisano: {output}", fg="green"))
        except Exception as e:
            click.echo(f"Błąd zapisu: {e}")


def _resolve_modules(
    modules: str, modules_csv: str | None, profile: str | None, fmt: OutputFormatter
) -> list[str] | None:
    """Resolve module selection from flags, CSV, or profile."""
    # CSV override (e.g. -M audio,security)
    if modules_csv:
        selected = [m.strip() for m in modules_csv.split(",") if m.strip()]
        fmt.status(f"  Moduły: {', '.join(selected)}", fg="cyan")
        return selected

    # Profile override
    if profile:
        from fixos.profiles import Profile as DiagProfile

        try:
            prof = DiagProfile.load(profile)
            fmt.status(f"  Profil: {prof.name} — {prof.description}", fg="cyan")
            return prof.modules
        except FileNotFoundError as e:
            fmt.status(str(e), fg="red")
            return None

    # Single module flag (--audio, --system, etc.)
    if modules and modules != "all":
        return [modules]

    return None


def _display_disk_fix_mode(disk_analysis: dict) -> None:
    """Display compact disk status for fix mode."""
    status_color = {
        "critical": "red",
        "warning": "yellow",
        "moderate": "blue",
        "healthy": "green",
    }.get(disk_analysis.get("status", "unknown"), "gray")
    click.echo(
        click.style(
            f"  Dysk: {disk_analysis['usage_percent']:.1f}% zajęty "
            f"({disk_analysis['used_gb']:.1f}GB / {disk_analysis['total_gb']:.1f}GB)",
            fg=status_color,
        )
    )
    suggestions = disk_analysis.get("suggestions", [])
    if suggestions:
        safe_suggestions = [s for s in suggestions if s.get("safe", False)]
        total_safe_gb = sum(s.get("size_gb", 0) for s in safe_suggestions)
        if total_safe_gb > 0.1:
            click.echo(
                click.style(
                    f"  Można bezpiecznie zwolnić: {total_safe_gb:.1f}GB w {len(safe_suggestions)} akcjach",
                    fg="green",
                )
            )


def _display_disk_scan_mode(disk_analysis: dict) -> None:
    """Display detailed disk status for scan mode."""
    click.echo(click.style("\nAnaliza dysku:", fg="cyan"))
    click.echo(f"  📈 Użycie: {disk_analysis['usage_percent']:.1f}%")
    click.echo(f"  Zajęte: {disk_analysis['used_gb']:.1f} GB")
    click.echo(f"  🆓 Wolne: {disk_analysis['free_gb']:.1f} GB")
    click.echo(f"  📁 Status: {disk_analysis['status']}")
    suggestions = disk_analysis.get("suggestions", [])
    if suggestions:
        click.echo(click.style("\nSugestie czyszczenia:", fg="yellow"))
        for suggestion in suggestions[:5]:
            safe_icon = "" if suggestion.get("safe") else ""
            click.echo(
                f"  {safe_icon} {suggestion['description']} ({suggestion.get('size_gb', 0):.1f}GB)"
            )


def _run_disk_analysis(
    data: dict,
    fmt: OutputFormatter | None = None,
    json_output: bool = False,
    is_fix_mode: bool = False,
) -> None:
    """Helper for disk analysis logic to avoid duplication between scan and fix"""
    indent = "  " if is_fix_mode else ""

    # In machine mode, just add data to the dict (caller emits)
    if fmt and fmt.is_machine:
        fmt.status("Analizowanie zajętości dysku...", fg="blue")
        try:
            from fixos.diagnostics.disk_analyzer import DiskAnalyzer

            analyzer = DiskAnalyzer()
            disk_analysis = analyzer.analyze_disk_usage()
            if "error" not in disk_analysis:
                data["disk_analysis"] = disk_analysis
            else:
                fmt.status(
                    f"{indent}Błąd analizy dysku: {disk_analysis['error']}", fg="red"
                )
        except Exception as e:
            fmt.status(f"{indent}Błąd podczas analizy dysku: {e}", fg="red")
        return

    click.echo(click.style("Analizowanie zajętości dysku...", fg="blue"))
    try:
        from fixos.diagnostics.disk_analyzer import DiskAnalyzer

        analyzer = DiskAnalyzer()
        disk_analysis = analyzer.analyze_disk_usage()

        if "error" in disk_analysis:
            click.echo(
                click.style(
                    f"{indent}Błąd analizy dysku: {disk_analysis['error']}", fg="red"
                )
            )
            return

        data["disk_analysis"] = disk_analysis

        if json_output and not is_fix_mode:
            import json

            click.echo(json.dumps(disk_analysis, indent=2, default=str))
            return

        if is_fix_mode:
            _display_disk_fix_mode(disk_analysis)
        else:
            _display_disk_scan_mode(disk_analysis)

    except ImportError:
        click.echo(
            click.style(f"{indent}Moduł analizy dysku nie jest dostępny", fg="yellow")
        )
    except Exception as e:
        click.echo(
            click.style(f"{indent}Błąd podczas analizy dysku: {str(e)}", fg="red")
        )


def _print_quick_issues(data: dict) -> None:
    """Wyświetla szybki przegląd problemów z zebranych danych."""
    click.echo(click.style("\nSzybki przegląd problemów:", fg="cyan"))
    issues = []

    # Sprawdź audio
    audio = data.get("audio", {})
    if (
        "brak" in str(audio.get("alsa_cards", "")).lower()
        or not audio.get("alsa_cards", "").strip()
        or audio.get("alsa_cards", "") == "(brak outputu)"
    ):
        issues.append("Dźwięk: brak kart ALSA – prawdopodobnie brak sterownika SOF")
    if "failed" in str(audio.get("pipewire_status", "")).lower():
        issues.append("PipeWire: usługa failed")
    if "failed" in str(audio.get("wireplumber_status", "")).lower():
        issues.append("WirePlumber: usługa failed")

    # Sprawdź thumbnails
    thumb = data.get("thumbnails", {})
    thumb_count = str(thumb.get("thumbnail_cache_count", "0")).strip()
    if thumb_count == "0":
        issues.append("Thumbnails: pusty cache – brak podglądów")
    if "nie zainstalowany" in str(thumb.get("ffmpegthumbnailer", "")):
        issues.append("ffmpegthumbnailer: nie zainstalowany")
    if "nie znaleziony" in str(thumb.get("totem_thumb", "")):
        issues.append("totem-video-thumbnailer: nie znaleziony")

    # Sprawdź system
    sys_data = data.get("system", {})
    failed = str(sys_data.get("systemctl_failed", "")).strip()
    if failed and failed != "(brak outputu)" and "0 loaded" not in failed:
        issues.append(f"systemctl: usługi failed:\n    {failed[:200]}")

    if not issues:
        click.echo("  Brak oczywistych problemów w zebranych danych.")
    else:
        for issue in issues:
            click.echo(f"  {issue}")
        click.echo("\n  Uruchom 'fixos fix' aby naprawić z pomocą AI.")
