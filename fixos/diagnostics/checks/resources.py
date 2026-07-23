"""
Resources diagnostics module.
Checks disk usage, memory, processes, autostart services.
"""

from typing import Any
from ._shared import (
    _cmd,
    _psutil_required,
    IS_LINUX,
    IS_WINDOWS,
    IS_MAC,
    psutil_module as psutil,
)
from ...constants import (
    MAX_TOP_PROCESSES,
    MAX_AUTOSTART_SERVICES,
    MAX_USER_AUTOSTART,
    MAX_SLOW_SERVICES,
    MAX_NETWORK_INTERFACES,
)


def diagnose_resources() -> dict[str, Any]:
    """
    Diagnostyka zasobów systemowych.
    Sprawdza: dysk (co zajmuje miejsce), pamięć (co ją żre),
    procesy startujące automatycznie, usługi w tle.
    """
    if not _psutil_required():
        return {
            "error": "psutil is required for resources diagnostics but is not installed",
        }
    # Top procesów wg CPU i RAM
    top_cpu: list[dict] = []
    top_mem: list[dict] = []
    for p in psutil.process_iter(
        [
            "pid",
            "name",
            "cpu_percent",
            "memory_percent",
            "memory_info",
            "status",
            "username",
        ]
    ):
        try:
            info = p.info
            info["memory_mb"] = round(
                (info.get("memory_info") or type("", (), {"rss": 0})()).rss / 1024**2, 1
            )
            top_cpu.append(info)
            top_mem.append(dict(info))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top_cpu.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    top_mem.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)

    result: dict[str, Any] = {
        "top_cpu_processes": [
            {
                "pid": p["pid"],
                "name": p["name"],
                "cpu_pct": p.get("cpu_percent", 0),
                "mem_mb": p.get("memory_mb", 0),
                "user": p.get("username", "?"),
            }
            for p in top_cpu[:MAX_TOP_PROCESSES]
        ],
        "top_mem_processes": [
            {
                "pid": p["pid"],
                "name": p["name"],
                "mem_pct": round(p.get("memory_percent") or 0, 2),
                "mem_mb": p.get("memory_mb", 0),
                "user": p.get("username", "?"),
            }
            for p in top_mem[:MAX_TOP_PROCESSES]
        ],
        "total_processes": len(top_cpu),
        "ram_available_gb": round(psutil.virtual_memory().available / 1024**3, 2),
        "ram_used_percent": psutil.virtual_memory().percent,
        "swap_used_percent": psutil.swap_memory().percent,
    }

    if IS_LINUX:
        result.update(
            {
                # Dysk – co zajmuje miejsce
                "disk_usage_top": _cmd(
                    "df -hT / /home 2>/dev/null; "
                    "du -sh /var/log /var/cache /tmp 2>/dev/null | sort -h"
                ),
                "disk_usage_home": (
                    "Pominięto w szybkim trybie: użyj "
                    "`fixos fix --modules files` lub `fixos cleanup --full`"
                ),
                "large_files": (
                    "Pominięto w szybkim trybie: głęboki skan jest dostępny "
                    "przez `fixos fix --modules files`"
                ),
                "log_sizes": _cmd(
                    f"du -sh /var/log/* 2>/dev/null | sort -h | tail -{MAX_TOP_PROCESSES}"
                ),
                "journal_size": _cmd("journalctl --disk-usage 2>/dev/null"),
                "old_kernels": _cmd(
                    "rpm -q kernel 2>/dev/null | sort -V | head -5 || dpkg -l 'linux-image-*' 2>/dev/null | grep '^ii' | head -5"
                ),
                "package_cache": _cmd(
                    "du -sh /var/cache/dnf 2>/dev/null || du -sh /var/cache/apt 2>/dev/null || echo 'N/A'"
                ),
                # Autostart – usługi startujące z systemem
                "autostart_services": _cmd(
                    f"systemctl list-unit-files --type=service --state=enabled --no-legend 2>/dev/null | head -{MAX_AUTOSTART_SERVICES}"
                ),
                "autostart_user": _cmd(
                    f"systemctl --user list-unit-files --state=enabled --no-legend 2>/dev/null | head -{MAX_USER_AUTOSTART}"
                ),
                "startup_time": _cmd("systemd-analyze 2>/dev/null | head -3"),
                "slowest_services": _cmd(
                    f"systemd-analyze blame 2>/dev/null | head -{MAX_SLOW_SERVICES}"
                ),
                # Pamięć – szczegóły
                "memory_details": _cmd("free -h 2>/dev/null"),
                "oom_events": _cmd(
                    "journalctl -k --no-pager -n 20 2>/dev/null | grep -i 'oom\\|killed process\\|out of memory' | tail -10 || echo 'Brak zdarzeń OOM'"
                ),
                "swap_usage": _cmd("swapon --show 2>/dev/null || echo 'Brak swap'"),
                # Zasoby sieciowe
                "network_usage": _cmd(
                    f'cat /proc/net/dev 2>/dev/null | awk \'NR>2 {{print $1, "RX:", $2, "TX:", $10}}\' | head -{MAX_NETWORK_INTERFACES}'
                ),
            }
        )
    elif IS_WINDOWS:
        result.update(
            {
                "disk_usage": _cmd(
                    'powershell -Command "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free | Format-Table" 2>nul'
                ),
                "autostart": _cmd(
                    'powershell -Command "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Format-List" 2>nul'
                ),
                "large_files": _cmd(
                    'powershell -Command "Get-ChildItem C:\\\\ -Recurse -ErrorAction SilentlyContinue | Where-Object {$_.Length -gt 100MB} | Select-Object FullName,Length | Sort-Object Length -Descending | Select-Object -First 10" 2>nul'
                ),
            }
        )
    elif IS_MAC:
        result.update(
            {
                "disk_usage_top": _cmd(
                    "du -sh /Library /Applications ~/Library 2>/dev/null | sort -h"
                ),
                "large_files": _cmd("find / -xdev -size +100M 2>/dev/null | head -15"),
                "autostart": _cmd("launchctl list 2>/dev/null | head -20"),
                "startup_time": _cmd(
                    "system_profiler SPStartupItemDataType 2>/dev/null | head -20"
                ),
            }
        )

    return result
