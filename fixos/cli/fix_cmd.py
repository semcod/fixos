"""
Fix command for fixOS CLI - diagnostics and repair session with LLM
"""

import json
import sys
from pathlib import Path
from typing import Any

import click

from fixos.agent.autonomous import run_autonomous_session
from fixos.agent.hitl import run_hitl_session
from fixos.cli.output_formatter import OutputFormatter
from fixos.cli.shared import BANNER, add_common_options, add_shared_options
from fixos.config import FixOsConfig, interactive_provider_setup
from fixos.constants import (
    DEFAULT_SESSION_TIMEOUT,
    MAX_FIXES_DEFAULT,
    MAX_SEARCH_QUERY_LENGTH,
)


def _collect_diagnostics(
    modules: str, disc: bool, fmt: OutputFormatter, output: str
) -> dict:
    """Run quick-first diagnostics and optionally disk analysis."""
    selected_modules = modules.split(",") if modules else None
    from fixos.diagnostics.quick_snapshot import collect_quick_snapshot

    quick_snapshot = collect_quick_snapshot()
    data: dict = {"quick": quick_snapshot}
    if not fmt.is_machine:
        from fixos.cli.quick_cmd import render_quick_snapshot

        render_quick_snapshot(quick_snapshot)

    if disc and not modules:
        pass
    else:
        fmt.status("\nZbieranie diagnostyki rozszerzonej...", fg="yellow")
        from fixos.diagnostics import get_full_diagnostics
        from fixos.diagnostics.system_checks import DEFAULT_DIAGNOSTIC_MODULES

        diagnostic_modules = selected_modules or list(DEFAULT_DIAGNOSTIC_MODULES)
        data.update(
            get_full_diagnostics(diagnostic_modules, progress_callback=fmt.progress)
        )

    if disc:
        from fixos.cli.scan_cmd import _run_disk_analysis

        _run_disk_analysis(data, fmt=fmt, is_fix_mode=True)

    if output:
        from fixos.utils.anonymizer import anonymize

        anon_str, _ = anonymize(str(data))
        try:
            Path(output).write_text(
                json.dumps(
                    {"anonymized": anon_str, "raw": data},
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            fmt.status(f"Raport: {output}", fg="green")
        except Exception as e:  # noqa: BLE001
            fmt.status(f"Błąd zapisu: {e}")

    return data


def _run_agent_session(
    cfg,
    data: dict,
    max_fixes: int,
    *,
    auto_confirm: bool = False,
    use_llm: bool | None = None,
    dry_run: bool = False,
) -> Any:
    """Dispatch to the appropriate agent session based on cfg.agent_mode."""
    if cfg.agent_mode == "autonomous":
        return run_autonomous_session(
            diagnostics=data,
            config=cfg,
            show_data=cfg.show_anonymized_data,
            max_fixes=max_fixes,
            auto_confirm=auto_confirm,
            use_llm=use_llm,
            dry_run=dry_run,
        )
    else:
        return run_hitl_session(
            diagnostics=data,
            config=cfg,
            show_data=cfg.show_anonymized_data,
        )


@click.command()
@add_common_options
@click.option(
    "--mode",
    type=click.Choice(["hitl", "autonomous"]),
    default=None,
    help="Tryb: hitl (domyślny) lub autonomous",
)
@click.option(
    "--timeout",
    default=DEFAULT_SESSION_TIMEOUT,
    show_default=True,
    help="Timeout sesji agenta (sekundy)",
)
@click.option(
    "--modules",
    "-M",
    default=None,
    help=(
        "Moduły diagnostyki: audio,thumbnails,hardware,system,... "
        "(domyślnie szybki zestaw bez głębokiego skanu plików; użyj 'all')"
    ),
)
@click.option(
    "--no-show-data",
    is_flag=True,
    default=False,
    help="Nie pokazuj danych diagnostycznych (tylko podsumowanie)",
)
@click.option("--output", "-o", default=None, help="Zapisz log sesji do JSON")
@click.option(
    "--max-fixes",
    default=MAX_FIXES_DEFAULT,
    show_default=True,
    help="Maksymalna liczba napraw w sesji",
)
@click.option(
    "--no-llm",
    is_flag=True,
    default=False,
    help="Tryb deterministyczny bez LLM (heurystyki i bezpieczne naprawy)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Nie pytaj o potwierdzenie przed startem trybu autonomicznego",
)
@add_shared_options
def fix(
    provider,
    token,
    model,
    no_banner,
    mode,
    timeout,
    modules,
    no_show_data,
    output,
    max_fixes,
    no_llm,
    yes,
    disc,
    dry_run,
    interactive,
    json_output,
    yaml_output,
    llm_fallback,
    show_raw,
) -> None:
    """
    Przeprowadza pełną diagnostykę i uruchamia sesję naprawczą z LLM lub heurystykami.

    \b
    Tryby:
      hitl        – Human-in-the-Loop (pyta o każdą akcję) [domyślny]
      autonomous  – Agent sam wykonuje komendy (działa również bez LLM!)

    \b
    Pipeline (synchroniczny, bez interakcji):
      fixos fix --yaml --no-interactive       # diagnostyka → YAML
      fixos fix --yaml --no-interactive --disc # diagnostyka + dysk → YAML

    \b
    Opcje dyskowe:
      --disc      – Analiza zajętości dysku + grupowanie przyczyn
      --dry-run   – Symulacja bez wykonywania akcji
      --json      – Wyjście w formacie JSON
      --yaml      – Wyjście w formacie YAML (pipe-safe)
      --llm-fallback – Użyj LLM gdy heurystyki nie wystarczą

    \b
    Przykłady:
      fixos fix                              # domyślnie hitl + Gemini z .env
      fixos fix --disc                       # z analizą dysku
      fixos fix --disc --dry-run             # analiza dysku bez wykonywania
      fixos fix --mode autonomous            # tryb autonomiczny (z LLM lub bez LLM)
      fixos fix --mode autonomous --no-llm   # autonomiczna naprawa bez LLM
      fixos fix --modules audio,thumbnails   # tylko audio i thumbnails
      fixos fix --modules all                # także głęboki skan plików
      fixos fix --yaml --no-interactive      # pipeline mode → YAML
      fixos fix --provider openai --token sk-...
    """
    fmt = OutputFormatter.from_flags(yaml_output=yaml_output, json_output=json_output)

    if not no_banner:
        fmt.banner(BANNER)

    # ── Pipeline mode: --yaml/--json + --no-interactive ──────
    if fmt.is_machine and not interactive:
        fmt.status("Pipeline mode: diagnostyka → structured output", fg="cyan")
        data = _collect_diagnostics(modules, disc, fmt, output)
        fmt.status("Diagnostyka gotowa.", fg="green")
        content = fmt.format_diagnostics(data)
        click.echo(content)
        return

    # ── Interactive / LLM / Heuristic mode ───────────────────
    cfg = FixOsConfig.load(
        provider=provider,
        api_key=token,
        model=model,
        agent_mode=mode,
        session_timeout=timeout,
        show_anonymized_data=not no_show_data,
    )

    if mode:
        cfg.agent_mode = mode

    use_llm = not no_llm and llm_fallback
    errors = cfg.validate() if use_llm else []

    if not use_llm:
        fmt.status(
            "\nTryb deterministyczny (bez LLM) — używam lokalnych heurystyk.",
            fg="yellow",
        )
    elif errors:
        if cfg.agent_mode == "autonomous" or disc or not interactive or yes:
            fmt.status(
                "\nBrak konfiguracji LLM — przełączam na tryb deterministyczny (bez LLM).",
                fg="yellow",
            )
            use_llm = False
        else:
            click.echo(click.style("\nBrak konfiguracji LLM.", fg="yellow"))
            new_cfg = interactive_provider_setup()
            if new_cfg is None:
                click.echo(
                    click.style(
                        "Anulowano. Użyj: fixos auto (bez LLM) lub fixos llm aby zobaczyć providery.",
                        fg="red",
                    )
                )
                sys.exit(1)
            cfg = new_cfg
            errors = cfg.validate()
            if errors:
                for err in errors:
                    click.echo(click.style(f"{err}", fg="red"))
                sys.exit(1)

    fmt.status("\nKonfiguracja:", fg="cyan")
    click.echo(cfg.summary())
    if dry_run:
        fmt.status("  Tryb: DRY-RUN (komendy nie będą wykonywane)", fg="yellow")
    if disc:
        fmt.status("  Analiza dysku: Włączona", fg="blue")

    data = _collect_diagnostics(modules, disc, fmt, output)
    fmt.status("Diagnostyka gotowa.\n", fg="green")

    if disc and "disk_analysis" in data:
        return handle_disk_cleanup_mode(
            data["disk_analysis"],
            cfg,
            dry_run,
            interactive and not yes,
            json_output,
            llm_fallback and use_llm,
        )

    _run_agent_session(
        cfg,
        data,
        max_fixes,
        auto_confirm=(yes or not interactive),
        use_llm=use_llm,
        dry_run=dry_run,
    )


@click.command("auto")
@add_common_options
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Symuluj wykonanie bez usuwania plików i uruchamiania komend",
)
@click.option(
    "--yes/--interactive",
    "-y",
    "yes",
    default=True,
    show_default=True,
    help="Wykonuj automatycznie bezpieczne naprawy i czyszczenie bez pytań",
)
@click.option(
    "--no-llm/--llm",
    "no_llm",
    default=True,
    show_default=True,
    help="Działaj bez LLM (deterministyczne heurystyki i czyszczenie dysku)",
)
@click.option(
    "--disc/--no-disc",
    "--disk/--no-disk",
    "disc",
    default=True,
    show_default=True,
    help="Automatycznie zwolnij bezpieczne miejsce na dysku (/tmp, ~/.cache, kosz, miniatury, IDE)",
)
@click.option(
    "--tmp/--no-tmp",
    "clean_tmp",
    default=True,
    show_default=True,
    help="Czyść przedawnione pliki z /tmp",
)
@click.option(
    "--user-cache/--no-user-cache",
    "clean_user_cache",
    default=True,
    show_default=True,
    help="Czyść bezpieczne, regenerowalne katalogi w ~/.cache (pip, uv, npm, itp.)",
)
@click.option(
    "--trash/--no-trash",
    "clean_trash",
    default=False,
    show_default=True,
    help="Opcjonalnie czyść przedawnione pliki z kosza (~/.local/share/Trash)",
)
@click.option(
    "--thumbnails/--no-thumbnails",
    "clean_thumbnails",
    default=True,
    show_default=True,
    help="Czyść stare miniaturki (~/.cache/thumbnails)",
)
@click.option(
    "--jetbrains/--no-jetbrains",
    "clean_jetbrains",
    default=True,
    show_default=True,
    help="Czyść stare wersje IDE z Toolbox i cache ~/.cache/JetBrains",
)
@click.option(
    "--build-cache/--no-build-cache",
    "clean_build_cache",
    default=True,
    show_default=True,
    help="Czyść regenerowalne cache kompilacji/pakietów (Cargo target/debug, ~/.npm/_cacache, archiwa conda)",
)
@click.option(
    "--snap-old/--no-snap-old",
    "clean_snap_old",
    default=False,
    show_default=True,
    help="Usuwaj wyłączone (disabled) rewizje pakietów snap",
)
@click.option(
    "--docker-build-cache/--no-docker-build-cache",
    "clean_docker_build_cache",
    default=True,
    show_default=True,
    help="Czyść wyłącznie nieużywany cache budowania Dockera starszy niż 7 dni (timeout 30 s)",
)
@click.option(
    "--free-gb",
    type=click.FloatRange(min=0.0, min_open=True),
    default=10.0,
    show_default=True,
    help="Minimalny cel wolnego miejsca w /; raportuj, gdy bezpieczne czyszczenie go nie osiągnie",
)
@click.option(
    "--journal/--no-journal",
    "clean_journal",
    default=True,
    show_default=True,
    help="Ogranicz rozmiar logów systemd journald (vacuum)",
)
@click.option(
    "--services/--no-services",
    "clean_services",
    default=False,
    show_default=True,
    help="Skanuj i czyść także dane usług (Docker/Ollama/npm/cargo)",
)
@click.option(
    "--retention",
    default="24h",
    show_default=True,
    help="Retencja dla czyszczenia /tmp (np. 24h, 12h, 1d, 7d)",
)
@click.option(
    "--modules",
    "-M",
    default=None,
    help="Moduły diagnostyczne (domyślnie szybki zestaw)",
)
@click.option(
    "--max-fixes",
    default=MAX_FIXES_DEFAULT,
    show_default=True,
    help="Maksymalna liczba napraw w sesji",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Zwróć wynik w formacie JSON",
)
@click.option("--output", "-o", default=None, help="Zapisz raport sesji do pliku JSON")
def auto_cmd(
    provider,
    token,
    model,
    no_banner,
    dry_run,
    yes,
    no_llm,
    disc,
    clean_tmp,
    clean_user_cache,
    clean_trash,
    clean_thumbnails,
    clean_jetbrains,
    clean_build_cache,
    clean_snap_old,
    clean_docker_build_cache,
    free_gb,
    clean_journal,
    clean_services,
    retention,
    modules,
    max_fixes,
    json_output,
    output,
) -> None:
    """
    Autonomiczna diagnostyka, naprawa i zwalnianie miejsca na dysku (bez LLM).

    \b
    Działa od razu bez klucza API i bez konfiguracji LLM:
      1. Szybki snapshot stanu systemu (CPU, RAM, dysk)
      2. Bezpieczne zwalnianie miejsca na dysku (/tmp, ~/.cache, build-cache, journald, kosz, miniatury, cache IDE)
      3. Deterministyczne naprawy znanych problemów z wtyczek diagnostycznych
      4. Podsumowanie odzyskanego miejsca i wykonanych akcji

    \b
    Przykłady:
      fixos auto                      # pełne autonomiczne czyszczenie i naprawa bez LLM
      fixos auto --dry-run            # podgląd akcji bez usuwania plików
      fixos auto --retention 12h      # czyść /tmp starsze niż 12 godzin
      fixos auto --services           # dołącz skanowanie usług (Docker/npm/cargo)
      fixos auto --json               # wynik maszynowy JSON
    """
    import math
    import os
    import shutil

    if not math.isfinite(free_gb):
        raise click.BadParameter("Cel musi być skończoną liczbą dodatnią", param_hint="--free-gb")

    from fixos.cli._auto_cleanup import (
        cleanup_additional_caches,
        cleanup_docker_builder,
    )
    from fixos.cli._cleanup_space import (
        _cleanup_build_caches,
        _cleanup_jetbrains,
        _cleanup_journal,
        _cleanup_snap_old,
        _cleanup_thumbnails,
        _cleanup_tmp,
        _cleanup_trash,
        _cleanup_user_cache,
        parse_retention_days,
    )
    from fixos.cli._cleanup_utils import _format_bytes
    from fixos.diagnostics.quick_snapshot import collect_quick_snapshot

    if not no_banner and not json_output:
        click.echo(click.style(BANNER, fg="cyan"))
        click.echo(
            click.style(
                "⚡ FIXOS AUTO — autonomiczna naprawa i zwalnianie miejsca (bez LLM)",
                fg="cyan",
                bold=True,
            )
        )

    before_usage = shutil.disk_usage("/")
    before_free_bytes = before_usage.free
    tmp_separate_mount = False
    before_tmp_free_bytes = 0
    try:
        if Path("/tmp").is_dir() and os.stat("/").st_dev != os.stat("/tmp").st_dev:
            tmp_separate_mount = True
            before_tmp_free_bytes = shutil.disk_usage("/tmp").free
    except OSError:
        tmp_separate_mount = False

    quick_snapshot = collect_quick_snapshot()

    if not json_output:
        from fixos.cli.quick_cmd import render_quick_snapshot

        render_quick_snapshot(quick_snapshot, compact=True)
        click.echo(
            click.style(
                f"Wolne miejsce przed uruchomieniem (/): {_format_bytes(before_free_bytes)}",
                fg="yellow",
            )
        )

    tmp_days = parse_retention_days(retention, default_days=1.0)
    steps_executed: list[str] = []

    from contextlib import nullcontext, redirect_stdout

    with redirect_stdout(sys.stderr) if json_output else nullcontext():
        if disc:
            if clean_tmp:
                if not json_output:
                    click.echo(
                        click.style(
                            f"\n[1/7] Czyszczenie /tmp (retencja: {retention})...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_tmp(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                    days=tmp_days,
                )
                steps_executed.append("tmp")

            if clean_user_cache:
                if not json_output:
                    click.echo(
                        click.style(
                            "\n[2/7] Czyszczenie bezpiecznych cache w ~/.cache...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_user_cache(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                )
                steps_executed.append("user-cache")
                cleanup_additional_caches(dry_run=dry_run, yes=yes)
                steps_executed.append("additional-cache")

            if clean_jetbrains:
                if not json_output:
                    click.echo(
                        click.style(
                            "\n[3/7] Czyszczenie starych kanałów i cache JetBrains...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_jetbrains(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                )
                steps_executed.append("jetbrains")

            if clean_build_cache:
                if not json_output:
                    click.echo(
                        click.style(
                            "\n[4/7] Czyszczenie cache kompilacji i pakietów (target/debug, npm, conda)...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_build_caches(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                )
                steps_executed.append("build-cache")

            if clean_docker_build_cache:
                if not json_output:
                    click.echo("\n[+] Nieużywany cache budowania Dockera (retencja: 7 dni)...")
                cleanup_docker_builder(dry_run=dry_run, yes=yes)
                steps_executed.append("docker-build-cache")

            if clean_snap_old:
                if not json_output:
                    click.echo(
                        click.style(
                            "\n[+] Czyszczenie wyłączonych rewizji snap...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_snap_old(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                )
                steps_executed.append("snap-old")

            if clean_journal:
                if not json_output:
                    click.echo(
                        click.style(
                            "\n[5/7] Ograniczanie rozmiaru logów systemd journald...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_journal(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                )
                steps_executed.append("journal")

            if clean_trash:
                if not json_output:
                    click.echo(
                        click.style(
                            "\n[6/7] Czyszczenie kosza (~/.local/share/Trash)...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_trash(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                )
                steps_executed.append("trash")

            if clean_thumbnails:
                if not json_output:
                    click.echo(
                        click.style(
                            "\n[7/7] Czyszczenie miniaturek (~/.cache/thumbnails)...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                _cleanup_thumbnails(
                    json_output=False,
                    dry_run=dry_run,
                    list_only=False,
                    yes=yes,
                )
                steps_executed.append("thumbnails")

            if clean_services:
                from fixos.cli.cleanup_cmd import _execute_yes_cleanup
                from fixos.diagnostics.service_scanner import ServiceDataScanner

                if not json_output:
                    click.echo(
                        click.style(
                            "\n[+] Skanowanie i czyszczenie bezpiecznych danych usług...",
                            fg="cyan",
                            bold=True,
                        )
                    )
                scanner = ServiceDataScanner()
                plan = scanner.get_cleanup_plan()
                _execute_yes_cleanup(plan, scanner, dry_run=dry_run)
                steps_executed.append("services")

    cfg = FixOsConfig.load(
        provider=provider,
        api_key=token,
        model=model,
        agent_mode="autonomous",
        show_anonymized_data=False,
    )
    use_llm = (not no_llm) and bool(cfg.api_key)

    diagnostics_data: dict[str, Any] = {"quick": quick_snapshot}
    if modules:
        from fixos.diagnostics import get_full_diagnostics

        diagnostics_data.update(get_full_diagnostics(modules.split(",")))

    with redirect_stdout(sys.stderr) if json_output else nullcontext():
        report = run_autonomous_session(
            diagnostics=diagnostics_data,
            config=cfg,
            show_data=False,
            max_fixes=max_fixes,
            auto_confirm=yes,
            use_llm=use_llm,
            dry_run=dry_run,
        )

    after_usage = shutil.disk_usage("/")
    after_free_bytes = after_usage.free
    root_freed_bytes = 0 if dry_run else max(0, after_free_bytes - before_free_bytes)
    tmp_freed_bytes = 0
    if tmp_separate_mount and not dry_run:
        try:
            tmp_freed_bytes = max(0, shutil.disk_usage("/tmp").free - before_tmp_free_bytes)
        except OSError:
            tmp_freed_bytes = 0
    # /tmp may be tmpfs: its free-space increase must never inflate disk recovery.
    freed_bytes = root_freed_bytes
    target_free_bytes = int(free_gb * 1024**3)
    goal_reached = after_free_bytes >= target_free_bytes
    disk_pressure_remaining = (
        (after_usage.total - after_free_bytes) / after_usage.total >= 0.95
        if after_usage.total else False
    )

    summary_payload = {
        "status": "dry_run" if dry_run else (
            "disk_pressure_remaining" if disk_pressure_remaining else
            "goal_unmet" if not goal_reached else "ok"
        ),
        "mode": "llm" if use_llm else "heuristic_no_llm",
        "steps_executed": steps_executed,
        "fixes_applied": len(report.fixes_applied),
        "problems_found": len(report.problems_found),
        "disk_free_before_bytes": before_free_bytes,
        "disk_free_after_bytes": after_free_bytes,
        "disk_freed_bytes": freed_bytes,
        "root_freed_bytes": root_freed_bytes,
        "tmp_freed_bytes": tmp_freed_bytes,
        "target_free_bytes": target_free_bytes,
        "goal_reached": goal_reached,
        "disk_pressure_remaining": disk_pressure_remaining,
        "disk_free_before_human": _format_bytes(before_free_bytes),
        "disk_free_after_human": _format_bytes(after_free_bytes),
        "disk_freed_human": _format_bytes(freed_bytes),
    }

    if output:
        try:
            Path(output).write_text(
                json.dumps(summary_payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            if not json_output:
                click.echo(click.style(f"Błąd zapisu raportu: {exc}", fg="red"))

    if json_output:
        click.echo(json.dumps(summary_payload, ensure_ascii=False, indent=2, default=str))
        return

    click.echo(click.style("═" * 60, fg="cyan"))
    click.echo(click.style("  PODSUMOWANIE FIXOS AUTO (BEZ LLM)", fg="cyan", bold=True))
    click.echo(click.style("═" * 60, fg="cyan"))
    click.echo(f"  Tryb             : {'LLM' if use_llm else 'Deterministyczny (bez LLM)'}")
    click.echo(f"  Kroki czyszczenia: {', '.join(steps_executed) or 'brak'}")
    click.echo(f"  Akcje agenta     : {len(report.fixes_applied)}")
    click.echo(f"  Wolne przed (/)  : {_format_bytes(before_free_bytes)}")
    click.echo(f"  Wolne po (/)     : {_format_bytes(after_free_bytes)}")
    if tmp_separate_mount and tmp_freed_bytes > 0:
        click.echo(f"  Osobny /tmp      : {_format_bytes(tmp_freed_bytes)} (poza bilansem /)")
    click.echo(f"  Cel wolnego (/)  : {_format_bytes(target_free_bytes)}")
    if not dry_run and (disk_pressure_remaining or not goal_reached):
        click.echo(click.style(
            "  UWAGA: czyszczenie nie rozwiązało problemu miejsca w /. "
            "Dane użytkownika pozostają chronione. "
            "Sprawdź największe kategorie: fixos scan --disc",
            fg="yellow",
        ))
    click.echo(
        click.style(
            f"  Odzyskane miejsce: {_format_bytes(freed_bytes)}",
            fg="green" if freed_bytes > 0 else "yellow",
            bold=True,
        )
    )
    click.echo(click.style("═" * 60, fg="cyan"))


def handle_disk_cleanup_mode(
    disk_analysis: dict[str, Any],
    cfg,
    dry_run: bool,
    interactive: bool,
    json_output: bool,
    llm_fallback: bool,
) -> None:
    """Handle disk cleanup mode with interactive planning"""
    from fixos.interactive.cleanup_planner import CleanupPlanner

    suggestions = disk_analysis.get("suggestions", [])
    if not suggestions:
        click.echo(click.style("Brak sugestii czyszczenia dysku.", fg="green"))
        return

    # Create cleanup plan
    planner = CleanupPlanner()
    plan = planner.create_cleanup_plan(suggestions)

    if json_output:
        click.echo(json.dumps(plan, indent=2, default=str))
        return

    # Display plan summary
    summary = plan["summary"]
    click.echo(click.style("\nPlan czyszczenia dysku:", fg="cyan"))
    click.echo(f"  🔢 Akcje: {summary['total_actions']}")
    click.echo(f"  Miejsce: {summary['total_size_gb']:.1f} GB")
    click.echo(f"  Bezpieczne: {summary['safe_size_gb']:.1f} GB")
    click.echo(f"  📂 Kategorie: {summary['categories_count']}")

    # Show categories
    for category_data in plan["categories"].values():
        info = category_data["info"]
        click.echo(f"\n{info['icon']} {info['name']}:")
        click.echo(f"  📁 Akcje: {category_data['actions_count']}")
        click.echo(f"  Miejsce: {category_data['total_size_gb']:.1f} GB")

        # Show top actions
        for action in category_data["actions"][:3]:
            safe_icon = "✓" if action["safe"] else "!"
            priority_icon = {"critical": "", "high": "", "medium": "", "low": ""}.get(
                action["priority"], ""
            )
            click.echo(
                f"    {safe_icon} {priority_icon} {action['description']} ({action['size_gb']:.1f}GB)"
            )

    # Show recommendations
    recommendations = plan.get("recommendations", [])
    if recommendations:
        click.echo(click.style("\nRekomendacje:", fg="yellow"))
        for rec in recommendations:
            priority_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(
                rec["priority"], "gray"
            )
            click.echo(click.style(f"  🎯 {rec['title']}", fg=priority_color))
            click.echo(f"     {rec['description']}")

    if dry_run:
        click.echo(
            click.style(
                "\nTryb DRY-RUN - żadne akcje nie zostaną wykonane", fg="yellow"
            )
        )
        return

    if interactive:
        selection = planner.interactive_selection(plan)
        click.echo(
            click.style(
                f"\nWybrano {selection['total_selected']} akcji do wykonania",
                fg="green",
            )
        )
        click.echo(
            click.style(
                f"Szacowane miejsce: {selection['estimated_space_gb']:.1f} GB",
                fg="green",
            )
        )

        # Execute selected actions
        execute_cleanup_actions(selection["selected_actions"], cfg, llm_fallback)
    else:
        # Auto-execute safe actions
        safe_actions = [a for a in plan["prioritized_actions"] if a.get("safe", False)]
        if safe_actions:
            click.echo(
                click.style(
                    f"\nAutomatyczne wykonanie {len(safe_actions)} bezpiecznych akcji",
                    fg="blue",
                )
            )
            execute_cleanup_actions(safe_actions, cfg, llm_fallback)
        else:
            click.echo(
                click.style(
                    "\nBrak bezpiecznych akcji do automatycznego wykonania", fg="yellow"
                )
            )


def execute_cleanup_actions(actions: list[dict], cfg, llm_fallback: bool) -> None:
    """Execute cleanup actions with safety checks"""
    from fixos.orchestrator.executor import CommandExecutor

    executor = CommandExecutor(
        default_timeout=60,
        require_confirmation=False,  # Already confirmed
        dry_run=False,
    )

    successful = []
    failed = []

    for i, action in enumerate(actions, 1):
        click.echo(f"\n[{i}/{len(actions)}] {action['description']}")

        # Execute the action
        cmd = action.get("command")
        if not cmd:
            click.echo(click.style("  Brak komendy", fg="yellow"))
            continue

        result = executor.execute_sync(cmd)

        if result.success:
            click.echo(click.style("  OK", fg="green"))
            successful.append(action)
        else:
            click.echo(click.style(f"  Błąd: {result.error}", fg="red"))
            failed.append(action)

    # Summary
    click.echo(click.style("\nPodsumowanie:", fg="cyan"))
    click.echo(f"  Wykonane: {len(successful)}")
    click.echo(f"  Błędy: {len(failed)}")

    if failed and llm_fallback:
        click.echo(click.style("\nPróba naprawy błędów przez LLM...", fg="yellow"))
        try_llm_fallback_for_failures(failed, cfg)


def try_llm_fallback_for_failures(failed_actions, cfg) -> None:
    """Try to fix failed actions using LLM"""
    from fixos.providers.llm import LLMClient

    try:
        llm = LLMClient(cfg)

        failed_desc = "\n".join(
            [
                f"- {a['description']}: {a.get('command', 'brak komendy')}"
                for a in failed_actions
            ]
        )

        prompt = f"""Następujące akcje czyszczenia dysku zakończyńczyły się błędem:
{failed_desc}

Zaproponuj alternatywne komendy lub podejście. Odpowiedz krótko, maksymalnie 3 komendy.
"""
        response = llm.chat(
            [{"role": "user", "content": prompt}], max_tokens=MAX_SEARCH_QUERY_LENGTH
        )
        click.echo(click.style("Sugestie LLM:", fg="cyan"))
        click.echo(response)

    except Exception as e:  # noqa: BLE001
        click.echo(click.style(f"Błąd LLM fallback: {e}", fg="red"))
