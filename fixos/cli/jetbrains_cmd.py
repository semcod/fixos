"""JetBrains JVM diagnosis and window-preserving recovery CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from fixos.diagnostics.jetbrains_recovery import (
    JetBrainsDiagnosis,
    JetBrainsRecovery,
    JetBrainsRecoveryResult,
    JetBrainsRecoverySafetyError,
)
from fixos.diagnostics.jetbrains_ai import JetBrainsAiControl, JetBrainsAiSafetyError


def _diagnosis_payload(diagnosis: JetBrainsDiagnosis) -> dict[str, Any]:
    metrics = diagnosis.metrics
    signals = diagnosis.log_signals
    return {
        "pid": diagnosis.process.pid,
        "create_time": diagnosis.process.create_time,
        "command": list(diagnosis.process.cmdline),
        "severity": diagnosis.severity,
        "reason_codes": list(diagnosis.reason_codes),
        "gc_recommended": diagnosis.gc_recommended,
        "metrics": {
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "rss_bytes": metrics.rss_bytes,
            "thread_count": metrics.thread_count,
        },
        "heap": None
        if diagnosis.heap is None
        else {
            "used_bytes": diagnosis.heap.used_bytes,
            "committed_bytes": diagnosis.heap.committed_bytes,
            "used_ratio": diagnosis.heap.used_ratio,
        },
        "edt": None
        if diagnosis.edt is None
        else {
            "java_state": diagnosis.edt.java_state,
            "detail": diagnosis.edt.detail,
            "contended": diagnosis.edt.contended,
            "top_frames": list(diagnosis.edt.top_frames),
        },
        "log_path": str(diagnosis.log_path) if diagnosis.log_path else None,
        "log_signals": {
            "write_action_waits": signals.write_action_waits,
            "edt_grab_warnings": signals.edt_grab_warnings,
            "max_edt_grab_ms": signals.max_edt_grab_ms,
            "project_disposals": signals.project_disposals,
            "working_directory_errors": signals.working_directory_errors,
            "git_stash_refresh_failures": signals.git_stash_refresh_failures,
            "ai_quota_errors": signals.ai_quota_errors,
            "missing_working_directories": list(
                signals.missing_working_directories
            ),
        },
        "diagnostic_errors": list(diagnosis.diagnostic_errors),
    }


def _recovery_payload(result: JetBrainsRecoveryResult) -> dict[str, Any]:
    return {
        "pid": result.pid,
        "command": list(result.command),
        "dry_run": result.dry_run,
        "executed": result.executed,
        "returncode": result.returncode,
        "verified_improvement": result.verified_improvement,
        "errors": list(result.errors),
    }


def _render_diagnosis(diagnosis: JetBrainsDiagnosis) -> None:
    metrics = diagnosis.metrics
    heap = (
        "brak danych"
        if diagnosis.heap is None
        else f"{diagnosis.heap.used_ratio * 100:.1f}%"
    )
    edt = (
        "brak danych"
        if diagnosis.edt is None
        else f"{diagnosis.edt.java_state}, contention={diagnosis.edt.contended}"
    )
    click.echo(
        click.style(
            f"JetBrains PID {diagnosis.process.pid}: {diagnosis.severity}",
            fg="red" if diagnosis.severity in {"critical", "high"} else "yellow",
            bold=True,
        )
    )
    click.echo(
        f"  CPU={metrics.cpu_percent:.1f}%  RSS={metrics.rss_bytes / 1024**3:.2f} GiB"
        f"  wątki={metrics.thread_count}  sterta={heap}"
    )
    click.echo(f"  EDT: {edt}")
    click.echo(
        "  Powody: "
        + (", ".join(diagnosis.reason_codes) or "brak sygnałów przeciążenia")
    )
    signals = diagnosis.log_signals
    click.echo(
        "  Log: "
        f"write-waits={signals.write_action_waits}, "
        f"EDT-max={signals.max_edt_grab_ms} ms, "
        f"AI-quota-errors={signals.ai_quota_errors}"
    )
    if diagnosis.diagnostic_errors:
        click.echo(
            click.style(
                "  Błędy diagnostyki: " + "; ".join(diagnosis.diagnostic_errors),
                fg="yellow",
            )
        )
    if diagnosis.gc_recommended:
        click.echo(
            click.style(
                "  GC jest uzasadnione; użyj --pid PID --apply-gc.",
                fg="cyan",
            )
        )
    if "ai-quota-refresh-loop" in diagnosis.reason_codes:
        click.echo(
            "  JetBrains AI Assistant zapętla odświeżanie limitu; "
            "sprawdź logowanie lub wyłącz wtyczkę przy następnym restarcie."
        )


@click.group(name="jetbrains")
def jetbrains() -> None:
    """Diagnozuj współdzieloną JVM JetBrains bez zamykania okien."""


@jetbrains.command(name="doctor")
@click.option("--pid", type=click.IntRange(min=1), help="Dokładny PID głównej JVM IDE")
@click.option(
    "--minutes",
    type=click.FloatRange(min=0.1),
    default=10.0,
    show_default=True,
    help="Zakres ostatnich zdarzeń idea.log",
)
@click.option(
    "--no-thread-dump",
    is_flag=True,
    help="Pomiń diagnostyczny odczyt stanu EDT przez jcmd",
)
@click.option("--json", "json_output", is_flag=True, help="Zwróć wynik JSON")
@click.option(
    "--apply-gc",
    is_flag=True,
    help="Wykonaj GC.run tylko dla uzasadnionej diagnozy i dokładnego --pid",
)
@click.option("--yes", is_flag=True, help="Pomiń potwierdzenie --apply-gc")
def doctor(
    pid: int | None,
    minutes: float,
    no_thread_dump: bool,
    json_output: bool,
    apply_gc: bool,
    yes: bool,
) -> None:
    """Zbierz metryki JVM, stan EDT i sygnały z idea.log."""

    if apply_gc and pid is None:
        raise click.UsageError("--apply-gc wymaga dokładnego --pid")
    if apply_gc and json_output and not yes:
        raise click.UsageError("JSON z --apply-gc wymaga jawnego --yes")

    recovery = JetBrainsRecovery()
    processes = recovery.find_main_processes()
    if pid is not None:
        processes = [process for process in processes if process.pid == pid]
        if not processes:
            raise click.ClickException(
                f"PID {pid} nie jest aktywnym głównym procesem JetBrains"
            )

    diagnoses: list[JetBrainsDiagnosis] = []
    errors: list[dict[str, Any]] = []
    for process in processes:
        try:
            diagnoses.append(
                recovery.diagnose(
                    process.pid,
                    lookback_seconds=minutes * 60,
                    capture_thread_dump=not no_thread_dump,
                )
            )
        except JetBrainsRecoverySafetyError as exc:
            errors.append({"pid": process.pid, "error": str(exc)})

    applied: JetBrainsRecoveryResult | None = None
    if apply_gc and diagnoses:
        selected = diagnoses[0]
        if not yes and not click.confirm(
            f"Wykonać window-preserving jcmd {selected.process.pid} GC.run?",
            default=False,
        ):
            click.echo("Pominięto GC.run.")
            return
        try:
            applied = recovery.recover(selected, apply=True)
        except JetBrainsRecoverySafetyError as exc:
            raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(
            json.dumps(
                {
                    "service": "jetbrains-doctor",
                    "read_only": not apply_gc,
                    "diagnoses": [_diagnosis_payload(item) for item in diagnoses],
                    "errors": errors,
                    "recovery": _recovery_payload(applied) if applied else None,
                },
                indent=2,
            )
        )
        return

    if not processes:
        click.echo("Nie znaleziono aktywnej głównej JVM JetBrains.")
        return
    for diagnosis in diagnoses:
        _render_diagnosis(diagnosis)
    for error in errors:
        click.echo(click.style(f"PID {error['pid']}: {error['error']}", fg="red"))
    if applied:
        status = "potwierdzona poprawa" if applied.verified_improvement else "brak potwierdzonej poprawy"
        click.echo(f"GC.run wykonano: {status}.")


def _render_ai_status(payload: dict[str, Any]) -> None:
    click.echo(click.style("JetBrains AI — stan", fg="yellow", bold=True))
    helpers = payload["helpers"]
    if helpers:
        for helper in helpers:
            click.echo(
                f"  Qoder PID {helper['pid']} (rodzic {helper['ppid']}), "
                f"RSS={helper['rss_bytes'] / 1024**2:.1f} MB"
            )
    else:
        click.echo("  Brak aktywnych helperów Qoder.")
    configs = payload["configs"]
    if not configs:
        click.echo("  Nie znaleziono konfiguracji aktywnego produktu JetBrains.")
    for config in configs:
        disabled = ", ".join(config["disabled"]) or "brak"
        click.echo(f"  {config['directory']}: wyłączone AI: {disabled}")


@jetbrains.command(name="ai")
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path, file_okay=False, exists=True),
    help="Dokładny katalog konfiguracji produktu JetBrains; domyślnie aktywny produkt",
)
@click.option(
    "--disable-plugins",
    is_flag=True,
    help="Dodaj com.qoder i com.intellij.ml.llm do disabled_plugins.txt",
)
@click.option(
    "--stop-qoder",
    is_flag=True,
    help="Zakończ TERM wyłącznie helpery Qoder należące do głównego IDE",
)
@click.option(
    "--apply",
    is_flag=True,
    help="Wykonaj wybrane zmiany; bez tej opcji pokazuje tylko plan",
)
@click.option("--yes", is_flag=True, help="Pomiń potwierdzenie z --apply")
@click.option("--json", "json_output", is_flag=True, help="Zwróć wynik JSON")
def ai_control(
    config_dir: Path | None,
    disable_plugins: bool,
    stop_qoder: bool,
    apply: bool,
    yes: bool,
    json_output: bool,
) -> None:
    """Diagnozuj i ogranicz dodatki AI bez zamykania okien IDE."""
    if apply and not (disable_plugins or stop_qoder):
        raise click.UsageError("--apply wymaga --disable-plugins lub --stop-qoder")
    control = JetBrainsAiControl()
    try:
        before = control.status(config_dir=config_dir)
    except JetBrainsAiSafetyError as exc:
        raise click.ClickException(str(exc)) from exc

    if not (disable_plugins or stop_qoder):
        if json_output:
            click.echo(json.dumps(before, indent=2))
        else:
            _render_ai_status(before)
        return
    if apply and not yes and not click.confirm(
        "Wyłączyć wskazane wtyczki i/lub zakończyć dokładne helpery Qoder?",
        default=False,
    ):
        click.echo("Pominięto zmiany JetBrains AI.")
        return

    result: dict[str, Any] = {
        "service": "jetbrains-ai-control",
        "dry_run": not apply,
        "plugin_changes": [],
        "helper_change": None,
    }
    try:
        if disable_plugins:
            if not before["configs"]:
                raise JetBrainsAiSafetyError(
                    "no exact JetBrains config directory was discovered"
                )
            result["plugin_changes"] = [
                control.disable_plugins(
                    Path(config["directory"]),
                    apply=apply,
                )
                for config in before["configs"]
            ]
        if stop_qoder:
            result["helper_change"] = control.stop_qoder_helpers(
                [
                    (helper["pid"], helper["create_time"])
                    for helper in before["helpers"]
                ],
                apply=apply,
            )
        result["after"] = control.status(config_dir=config_dir)
    except (JetBrainsAiSafetyError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        click.echo(json.dumps(result, indent=2))
        return
    mode = "WYKONANO" if apply else "PLAN"
    click.echo(click.style(f"JetBrains AI [{mode}]", fg="green" if apply else "cyan"))
    for change in result["plugin_changes"]:
        added = ", ".join(change["added"]) or "brak nowych wpisów"
        click.echo(f"  Wtyczki: {added}; restart IDE wymagany do pełnego efektu.")
    if result["helper_change"] is not None:
        helper = result["helper_change"]
        click.echo(
            f"  Qoder: wybrane={helper['selected']}, zatrzymane={helper['stopped']}, "
            f"błędy={len(helper['failed'])}"
        )
    click.echo("  Główna JVM i okna IDE nie są zatrzymywane.")
