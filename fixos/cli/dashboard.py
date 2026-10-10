"""
Interactive Graphical Shell Dashboard and Automated Safe Intervention for fixOS.
Provides rich terminal visualizations of CPU, RAM, Disk, caches, and rogue processes,
with safe, evidence-led automated intervention capabilities.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import click
import psutil
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from fixos.diagnostics.native_scan import measure_tree, scan_dir_native
from fixos.diagnostics.process_chains import (
    PRIVILEGED_ACCOUNTS,
    ProcessRecord,
    collect_processes,
)

# Protected application and session patterns that must NEVER be terminated
PROTECTED_PROCESS_PATTERNS = frozenset(
    {
        "systemd",
        "init",
        "dbus",
        "gnome",
        "kde",
        "plasma",
        "wayland",
        "xorg",
        "x11",
        "pipewire",
        "pulseaudio",
        "wireplumber",
        "login",
        "sshd",
        "bash",
        "zsh",
        "fish",
        "sh",
        "tmux",
        "screen",
        "pycharm",
        "idea",
        "code",
        "cursor",
        "vscode",
        "alacritty",
        "kitty",
        "wezterm",
        "konsole",
        "gnome-terminal",
        "ptyxis",
        "terminal",
        "fixos",
        "dockerd",
        "containerd",
    }
)


@dataclass
class StorageItem:
    name: str
    path: str
    size_mb: float
    risk: str
    safe_to_cleanup: bool
    description: str


@dataclass
class ProcessItem:
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    create_time: float
    runtime_str: str
    cmdline_str: str
    safety: str  # "safe", "review", "protected"
    reason: str


@dataclass
class DashboardScanData:
    cpu_percent: float
    cpu_cores: int
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_free_gb: float
    is_disk_critical: bool
    storage_items: list[StorageItem]
    safe_reclaimable_gb: float
    total_scanned_storage_gb: float
    heavy_processes: list[ProcessItem]
    safe_terminable_pids: list[int]
    warnings: list[str]


def _format_runtime(create_time: float, now: float) -> str:
    elapsed = max(0, int(now - create_time))
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def classify_process_safety(
    proc: ProcessRecord, self_pid: int, now: float
) -> tuple[str, str]:
    """Classify whether a process is safe to terminate automatically.

    Returns (safety, reason) where safety is 'safe', 'review', or 'protected'.
    """
    pid = proc.pid
    name_lower = proc.name.lower()

    if pid in (0, 1, 2) or pid == self_pid:
        return "protected", "Bieżący proces lub proces systemowy PID <= 2"

    if proc.username.lower() in PRIVILEGED_ACCOUNTS:
        return "protected", f"Proces konta uprzywilejowanego ({proc.username})"

    for pat in PROTECTED_PROCESS_PATTERNS:
        if pat in name_lower:
            return "protected", f"Chroniona aplikacja/środowisko ({pat})"

    # Check command line arguments for IDE / development GUI markers
    cmd_str = " ".join(proc.cmdline).lower()
    for pat in PROTECTED_PROCESS_PATTERNS:
        if pat in cmd_str and ("bin/" in cmd_str or "opt/" in cmd_str or "app" in cmd_str):
            return "protected", f"Powiązany z chronionym komponentem ({pat})"

    # Check for excessive CPU / memory usage
    high_cpu = proc.cpu_percent >= 70.0
    high_mem = proc.memory_percent >= 25.0
    stale_runtime = (now - proc.create_time) >= 600  # Running > 10m

    if (
        (high_cpu or high_mem)
        and stale_runtime
        and name_lower in ("python", "python3", "node", "ruby", "perl", "worker", "php")
    ):
        return (
            "safe",
            f"Zablokowany / zapętlony worker ({proc.cpu_percent:.1f}% CPU, {proc.memory_percent:.1f}% RAM)",
        )

    if high_cpu:
        return "review", f"Wysokie zużycie CPU ({proc.cpu_percent:.1f}%), wymaga weryfikacji"

    return "review", "Standardowy proces użytkownika"


def collect_dashboard_scan() -> DashboardScanData:
    """Run a fast, comprehensive system scan returning structured metrics."""
    now = time.time()
    warnings: list[str] = []

    # 1. System CPU & Memory
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count(logical=True) or 1
    vm = psutil.virtual_memory()
    ram_percent = vm.percent
    ram_used_gb = (vm.total - vm.available) / (1024**3)
    ram_total_gb = vm.total / (1024**3)

    # 2. Disk metrics
    try:
        du = shutil.disk_usage("/")
        disk_percent = (du.used / du.total) * 100
        disk_used_gb = du.used / (1024**3)
        disk_total_gb = du.total / (1024**3)
        disk_free_gb = du.free / (1024**3)
    except OSError:
        disk_percent, disk_used_gb, disk_total_gb, disk_free_gb = 0.0, 0.0, 0.0, 0.0

    is_disk_critical = disk_percent >= 90.0
    if is_disk_critical:
        warnings.append(
            f"KRYTYCZNE ZAJĘCIE DYSKU: {disk_percent:.1f}% zajęte (tylko {disk_free_gb:.1f} GB wolne)!"
        )

    # 3. Storage opportunities (Fast scan using Rust native where available)
    storage_items: list[StorageItem] = []
    cache_root = Path.home() / ".cache"
    if cache_root.is_dir():
        native_entries = scan_dir_native(cache_root, min_bytes=100 * 1024 * 1024)
        if native_entries:
            for entry in native_entries[:12]:
                name = entry["name"]
                size_mb = entry["bytes"] / (1024 * 1024)
                # Known safe caches
                is_safe = name.lower() in {
                    "pip", "uv", "npm", "yarn", "pnpm", "thumbnails",
                    "google-chrome", "mozilla", "huggingface", "mesa_shader_cache",
                }
                risk = "safe" if is_safe else "review"
                storage_items.append(
                    StorageItem(
                        name=f"~/.cache/{name}",
                        path=entry["path"],
                        size_mb=round(size_mb, 1),
                        risk=risk,
                        safe_to_cleanup=is_safe,
                        description="Pamięć podręczna aplikacji / narzędzi programistycznych",
                    )
                )

    # Check temp and trash
    tmp_path = Path("/tmp")
    if tmp_path.is_dir():
        tmp_m = measure_tree(tmp_path, native=True)
        tmp_mb = tmp_m.get("bytes", 0) / (1024 * 1024)
        if tmp_mb > 50:
            storage_items.append(
                StorageItem(
                    name="/tmp",
                    path="/tmp",
                    size_mb=round(tmp_mb, 1),
                    risk="safe",
                    safe_to_cleanup=True,
                    description="Tymczasowe pliki systemowe i procesów",
                )
            )

    safe_reclaimable_gb = sum(
        item.size_mb / 1024 for item in storage_items if item.safe_to_cleanup
    )
    total_scanned_storage_gb = sum(item.size_mb / 1024 for item in storage_items)

    # 4. Process sampling & safety classification
    self_pid = os.getpid()
    all_procs = collect_processes(sample_seconds=0.1)
    heavy_procs: list[ProcessItem] = []
    safe_terminable_pids: list[int] = []

    # Sort by CPU % descending, then Memory %
    sorted_procs = sorted(
        all_procs,
        key=lambda p: (p.cpu_percent, p.memory_percent),
        reverse=True,
    )

    for proc in sorted_procs:
        if proc.cpu_percent >= 5.0 or proc.memory_percent >= 5.0:
            safety, reason = classify_process_safety(proc, self_pid, now)
            runtime_str = _format_runtime(proc.create_time, now)
            cmd_preview = " ".join(proc.cmdline)[:60] if proc.cmdline else proc.name
            heavy_procs.append(
                ProcessItem(
                    pid=proc.pid,
                    name=proc.name,
                    username=proc.username,
                    cpu_percent=proc.cpu_percent,
                    memory_percent=proc.memory_percent,
                    create_time=proc.create_time,
                    runtime_str=runtime_str,
                    cmdline_str=cmd_preview,
                    safety=safety,
                    reason=reason,
                )
            )
            if safety == "safe":
                safe_terminable_pids.append(proc.pid)

    return DashboardScanData(
        cpu_percent=round(cpu_percent, 1),
        cpu_cores=cpu_cores,
        ram_percent=round(ram_percent, 1),
        ram_used_gb=round(ram_used_gb, 2),
        ram_total_gb=round(ram_total_gb, 2),
        disk_percent=round(disk_percent, 1),
        disk_used_gb=round(disk_used_gb, 2),
        disk_total_gb=round(disk_total_gb, 2),
        disk_free_gb=round(disk_free_gb, 2),
        is_disk_critical=is_disk_critical,
        storage_items=storage_items,
        safe_reclaimable_gb=round(safe_reclaimable_gb, 2),
        total_scanned_storage_gb=round(total_scanned_storage_gb, 2),
        heavy_processes=heavy_procs[:10],
        safe_terminable_pids=safe_terminable_pids,
        warnings=warnings,
    )


def render_dashboard(data: DashboardScanData, console: Console | None = None) -> None:
    """Render graphical shell representation using Rich components."""
    console = console or Console()

    # 1. Header & Title
    title = Text("FixOS • Szybki Dashboard Diagnostyczny i Optymalizacja Systemu", style="bold cyan")
    console.print(Panel(title, box=ROUNDED, border_style="cyan"))

    # 2. Resource Status Table
    res_table = Table(box=ROUNDED, border_style="bright_blue", show_header=True, expand=True)
    res_table.add_column("Zasób", style="bold white", width=14)
    res_table.add_column("Wskaźnik Wykorzystania", ratio=3)
    res_table.add_column("Szczegóły", style="bright_white", ratio=2)
    res_table.add_column("Status", style="bold", justify="center", width=12)

    def _status_badge(percent: float, crit_thresh: float = 90.0, warn_thresh: float = 75.0) -> tuple[str, str]:
        if percent >= crit_thresh:
            return "[red]KRYTYCZNY[/red]", "red"
        if percent >= warn_thresh:
            return "[yellow]OSTRZEŻENIE[/yellow]", "yellow"
        return "[green]W NORMIE[/green]", "green"

    # CPU bar
    cpu_badge, cpu_color = _status_badge(data.cpu_percent, 85.0, 65.0)
    cpu_bar = ProgressBar(total=100.0, completed=data.cpu_percent, complete_style=cpu_color)
    res_table.add_row(
        "CPU",
        cpu_bar,
        f"{data.cpu_percent}%  ({data.cpu_cores} rdzeni logicznych)",
        cpu_badge,
    )

    # RAM bar
    ram_badge, ram_color = _status_badge(data.ram_percent, 90.0, 75.0)
    ram_bar = ProgressBar(total=100.0, completed=data.ram_percent, complete_style=ram_color)
    res_table.add_row(
        "Pamięć RAM",
        ram_bar,
        f"{data.ram_percent}%  ({data.ram_used_gb:.1f} GB / {data.ram_total_gb:.1f} GB)",
        ram_badge,
    )

    # Disk bar
    disk_badge, disk_color = _status_badge(data.disk_percent, 90.0, 80.0)
    disk_bar = ProgressBar(total=100.0, completed=data.disk_percent, complete_style=disk_color)
    res_table.add_row(
        "Dysk (/)",
        disk_bar,
        f"{data.disk_percent}%  (Wolne: {data.disk_free_gb:.1f} GB z {data.disk_total_gb:.1f} GB)",
        disk_badge,
    )

    console.print(Panel(res_table, title="[bold]1. Główne Zasoby Systemowe[/bold]", box=ROUNDED, border_style="blue"))

    # Warnings / Alerts
    if data.warnings:
        for w in data.warnings:
            console.print(Panel(Text(f"⚠️  {w}", style="bold red"), border_style="red"))

    # 3. Storage Table
    storage_table = Table(box=ROUNDED, border_style="bright_magenta", show_header=True, expand=True)
    storage_table.add_column("Lokalizacja / Cache", style="white", ratio=2)
    storage_table.add_column("Rozmiar", justify="right", style="cyan", width=12)
    storage_table.add_column("Kategoria Ryzyka", justify="center", width=16)
    storage_table.add_column("Opis & Rekomendacja", style="bright_black", ratio=3)

    if data.storage_items:
        for item in data.storage_items:
            size_str = f"{item.size_mb / 1024:.2f} GB" if item.size_mb >= 1024 else f"{item.size_mb:.0f} MB"
            if item.safe_to_cleanup:
                risk_tag = "[green]BEZPIECZNE[/green]"
            elif item.risk == "review":
                risk_tag = "[yellow]DO DECYZJI[/yellow]"
            else:
                risk_tag = "[red]CHRONIONE[/red]"
            storage_table.add_row(item.name, size_str, risk_tag, item.description)
    else:
        storage_table.add_row("Brak dużych katalogów cache powyżej progu", "-", "-", "-")

    storage_title = (
        f"[bold]2. Przestrzeń Dysku & Cache (Bezpieczny odzysk: [green]{data.safe_reclaimable_gb:.2f} GB[/green] / "
        f"Łącznie: {data.total_scanned_storage_gb:.2f} GB)[/bold]"
    )
    console.print(Panel(storage_table, title=storage_title, box=ROUNDED, border_style="magenta"))

    # 4. Top Heavy Processes Table
    proc_table = Table(box=ROUNDED, border_style="bright_yellow", show_header=True, expand=True)
    proc_table.add_column("PID", justify="right", style="cyan", width=8)
    proc_table.add_column("Nazwa", style="bold white", width=16)
    proc_table.add_column("CPU %", justify="right", style="yellow", width=8)
    proc_table.add_column("RAM %", justify="right", style="magenta", width=8)
    proc_table.add_column("Czas", justify="right", style="white", width=10)
    proc_table.add_column("Bezpieczeństwo Zatrzymania", justify="center", width=26)
    proc_table.add_column("Uzasadnienie", style="bright_black", ratio=3)

    if data.heavy_processes:
        for p in data.heavy_processes:
            if p.safety == "safe":
                safety_tag = "[bold green]BEZPIECZNE ZAMKNIĘCIE[/bold green]"
            elif p.safety == "review":
                safety_tag = "[yellow]DO DECYZJI[/yellow]"
            else:
                safety_tag = "[red]CHRONIONY (SYSTEM/IDE)[/red]"
            proc_table.add_row(
                str(p.pid),
                p.name,
                f"{p.cpu_percent:.1f}%",
                f"{p.memory_percent:.1f}%",
                p.runtime_str,
                safety_tag,
                p.reason,
            )
    else:
        proc_table.add_row("-", "Brak procesów o wysokim obciążeniu", "-", "-", "-", "-", "-")

    safe_count = len(data.safe_terminable_pids)
    proc_title = (
        f"[bold]3. Procesy o Wysokim Obciążeniu (Bezpieczne do zakończenia: [green]{safe_count}[/green])[/bold]"
    )
    console.print(Panel(proc_table, title=proc_title, box=ROUNDED, border_style="yellow"))


def execute_safe_cache_cleanup(data: DashboardScanData, *, dry_run: bool = False) -> tuple[int, float]:
    """Safely delete only items marked as safe_to_cleanup."""
    cleaned_count = 0
    reclaimed_mb = 0.0

    for item in data.storage_items:
        if not item.safe_to_cleanup:
            continue

        p = Path(item.path)
        if not p.exists():
            continue

        if dry_run:
            click.echo(f"  [DRY-RUN] Usunięcie bezpiecznego cache: {item.name} ({item.size_mb:.1f} MB)")
            cleaned_count += 1
            reclaimed_mb += item.size_mb
            continue

        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                p.mkdir(parents=True, exist_ok=True)
            elif p.is_file():
                p.unlink(missing_ok=True)
            click.echo(click.style(f"  ✓ Oczyszczono: {item.name} ({item.size_mb:.1f} MB)", fg="green"))
            cleaned_count += 1
            reclaimed_mb += item.size_mb
        except OSError as exc:
            click.echo(click.style(f"  ✗ Błąd czyszczenia {item.name}: {exc}", fg="red"))

    return cleaned_count, reclaimed_mb


def execute_safe_process_termination(data: DashboardScanData, *, dry_run: bool = False) -> list[int]:
    """Terminate only processes verified as safe to terminate."""
    terminated: list[int] = []

    for item in data.heavy_processes:
        if item.safety != "safe":
            continue

        pid = item.pid
        if dry_run:
            click.echo(f"  [DRY-RUN] Bezpieczne zakończenie procesu PID {pid} ({item.name}): {item.reason}")
            terminated.append(pid)
            continue

        try:
            proc = psutil.Process(pid)
            # Revalidate creation time
            if abs(proc.create_time() - item.create_time) > 0.1:
                click.echo(click.style(f"  ⚠️ Pominięto PID {pid}: PID został ponownie użyty", fg="yellow"))
                continue

            click.echo(click.style(f"  → Zamykanie procesu PID {pid} ({item.name})...", fg="cyan"))
            proc.terminate()
            try:
                proc.wait(timeout=1.5)
            except psutil.TimeoutExpired:
                proc.kill()
            click.echo(click.style(f"  ✓ Zakończono PID {pid} ({item.name})", fg="green"))
            terminated.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            click.echo(click.style(f"  ⚠️ Proces PID {pid} nie mógł zostać zamknięty: {exc}", fg="yellow"))

    return terminated


def run_interactive_dashboard(dry_run: bool = False) -> None:
    """Run interactive visual dashboard loop."""
    console = Console()

    while True:
        console.clear()
        console.print("[dim cyan]Zbieranie danych diagnostycznych (Rust native scan)...[/dim cyan]")
        data = collect_dashboard_scan()
        render_dashboard(data, console)

        console.print()
        console.print("[bold cyan]Opcje automatycznej bezpiecznej interwencji:[/bold cyan]")
        console.print("  [bold yellow][1][/bold yellow] Wykonaj bezpieczne czyszczenie cache (pip, uv, npm, thumbnails, /tmp)")
        console.print("  [bold yellow][2][/bold yellow] Bezpiecznie zakończ zapętlone procesy o wysokim obciążeniu")
        console.print("  [bold yellow][3][/bold yellow] Pełna automatyczna interwencja (1 + 2)")
        console.print("  [bold yellow][r][/bold yellow] Odśwież skan")
        console.print("  [bold yellow][q][/bold yellow] Wyjście do menu")
        console.print()

        choice = click.prompt("Wybierz opcję", default="q", show_default=True).strip().lower()

        if choice in ("q", "quit", "exit"):
            break
        if choice in ("r", "refresh"):
            continue
        if choice == "1":
            console.print("\n[bold]Czyszczenie bezpiecznego cache:[/bold]")
            count, mb = execute_safe_cache_cleanup(data, dry_run=dry_run)
            console.print(f"\n[green]Zakończono: oczyszczono {count} pozycji, odzyskano {mb:.1f} MB.[/green]")
            click.pause("\nNaciśnij dowolny klawisz, aby odświeżyć...")
        elif choice == "2":
            console.print("\n[bold]Zamykanie bezpiecznych procesów:[/bold]")
            if not data.safe_terminable_pids:
                console.print("[yellow]Brak procesów zakwalifikowanych jako bezpieczne do automatycznego zamknięcia.[/yellow]")
            else:
                pids = execute_safe_process_termination(data, dry_run=dry_run)
                console.print(f"\n[green]Zakończono: zamknięto {len(pids)} procesów.[/green]")
            click.pause("\nNaciśnij dowolny klawisz, aby odświeżyć...")
        elif choice == "3":
            console.print("\n[bold]Pełna bezpieczna interwencja:[/bold]")
            count, mb = execute_safe_cache_cleanup(data, dry_run=dry_run)
            pids = execute_safe_process_termination(data, dry_run=dry_run)
            console.print(f"\n[green]Podsumowanie: odzyskano {mb:.1f} MB, zakończono {len(pids)} procesów.[/green]")
            click.pause("\nNaciśnij dowolny klawisz, aby odświeżyć...")


@click.command("dashboard")
@click.option("--dry-run", is_flag=True, default=False, help="Symuluj interwencję bez usuwania plików i zabijania procesów")
@click.option("--auto-fix", is_flag=True, default=False, help="Automatycznie wykonaj bezpieczną interwencję bez pytań")
@click.option("--json", "json_output", is_flag=True, default=False, help="Zwróć dane skanu w formacie JSON")
def dashboard_cmd(dry_run: bool, auto_fix: bool, json_output: bool) -> None:
    """Graficzna reprezentacja stanu systemu w shellu i automatyczna interwencja."""
    if json_output:
        import json

        data = collect_dashboard_scan()
        out = {
            "cpu_percent": data.cpu_percent,
            "ram_percent": data.ram_percent,
            "disk_percent": data.disk_percent,
            "disk_free_gb": data.disk_free_gb,
            "safe_reclaimable_gb": data.safe_reclaimable_gb,
            "storage_items": [
                {"name": i.name, "path": i.path, "size_mb": i.size_mb, "risk": i.risk, "safe": i.safe_to_cleanup}
                for i in data.storage_items
            ],
            "heavy_processes": [
                {"pid": p.pid, "name": p.name, "cpu": p.cpu_percent, "ram": p.memory_percent, "safety": p.safety}
                for p in data.heavy_processes
            ],
        }
        click.echo(json.dumps(out, indent=2))
        return

    if auto_fix:
        console = Console()
        console.print("[dim cyan]Wykonywanie automatycznej bezpiecznej interwencji...[/dim cyan]")
        data = collect_dashboard_scan()
        render_dashboard(data, console)
        console.print("\n[bold]Uruchamianie interwencji:[/bold]")
        _count, mb = execute_safe_cache_cleanup(data, dry_run=dry_run)
        pids = execute_safe_process_termination(data, dry_run=dry_run)
        console.print(f"\n[bold green]Interwencja zakończona: odzyskano {mb:.1f} MB, zamknięto {len(pids)} procesów.[/bold green]")
        return

    run_interactive_dashboard(dry_run=dry_run)
