"""
Security diagnostics module.
Checks firewall, open ports, SSH, SELinux, fail2ban.
"""

from typing import Any
from ._shared import _cmd, IS_LINUX, IS_WINDOWS, IS_MAC
from ...constants import (
    MAX_OPEN_PORTS,
    MAX_SECURITY_LOGS,
    MAX_AUTH_FAILURES,
    MAX_NETWORK_INTERFACES_DIAG,
    MAX_SUDO_USERS,
    MAX_SUID_FILES,
)


def diagnose_security() -> dict[str, Any]:
    """
    Diagnostyka bezpieczeństwa systemu i sieci.
    Sprawdza: firewall, otwarte porty, usługi sieciowe, SELinux/AppArmor,
    aktualizacje bezpieczeństwa, nieautoryzowane procesy, SSH config.
    """
    result: dict[str, Any] = {}

    if IS_LINUX:
        result.update(
            {
                # Firewall
                "firewall_state": _cmd(
                    f"firewall-cmd --state 2>/dev/null || ufw status 2>/dev/null || iptables -L -n --line-numbers 2>/dev/null | head -{MAX_SECURITY_LOGS} || echo 'N/A'"
                ),
                "firewall_zones": _cmd(
                    f"firewall-cmd --list-all 2>/dev/null | head -{MAX_SECURITY_LOGS} || ufw status verbose 2>/dev/null | head -{MAX_SECURITY_LOGS} || echo 'N/A'"
                ),
                # Otwarte porty i połączenia
                "open_ports": _cmd(
                    f"ss -tlnp 2>/dev/null | head -{MAX_OPEN_PORTS} || netstat -tlnp 2>/dev/null | head -{MAX_OPEN_PORTS}"
                ),
                "active_connections": _cmd(
                    f"ss -tnp 2>/dev/null | grep ESTAB | head -{MAX_SECURITY_LOGS}"
                ),
                "listening_services": _cmd(
                    f"ss -tlnp 2>/dev/null | awk 'NR>1 {{print $1, $4, $6}}' | head -{MAX_SECURITY_LOGS}"
                ),
                # SELinux / AppArmor
                "selinux_status": _cmd(
                    "getenforce 2>/dev/null || sestatus 2>/dev/null | head -5 || echo 'N/A'"
                ),
                "apparmor_status": _cmd(
                    "aa-status 2>/dev/null | head -10 || apparmor_status 2>/dev/null | head -10 || echo 'N/A'"
                ),
                "selinux_denials": _cmd(
                    f"ausearch -m avc -ts recent 2>/dev/null | tail -10 || journalctl -t audit --no-pager -n {MAX_AUTH_FAILURES} 2>/dev/null | grep 'denied' | tail -10 || echo 'N/A'"
                ),
                # SSH
                "ssh_config": _cmd(
                    "grep -E '^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|Port|AllowUsers)' /etc/ssh/sshd_config 2>/dev/null || echo 'N/A'"
                ),
                "ssh_service": _cmd(
                    "systemctl is-active sshd 2>/dev/null || systemctl is-active ssh 2>/dev/null || echo 'N/A'"
                ),
                "ssh_authorized_keys": _cmd(
                    "find /root/.ssh /home/*/.ssh -maxdepth 1 "
                    "-name 'authorized_keys' -type f 2>/dev/null | "
                    "head -5 || echo 'N/A'"
                ),
                # Aktualizacje bezpieczeństwa
                "security_updates": _cmd(
                    "dnf updateinfo list security 2>/dev/null | wc -l || "
                    "apt list --upgradable 2>/dev/null | grep -i security | wc -l || echo '0'"
                ),
                "last_security_update": _cmd(
                    "dnf history list 2>/dev/null | grep -i security | head -3 || "
                    "grep 'security' /var/log/dpkg.log 2>/dev/null | tail -3 || echo 'N/A'"
                ),
                # Użytkownicy i uprawnienia
                "sudo_users": _cmd(
                    f"getent group sudo wheel 2>/dev/null | head -{MAX_SUDO_USERS}"
                ),
                "users_with_shell": _cmd(
                    "awk -F: '$7 !~ /nologin|false/ {print $1, $7}' /etc/passwd 2>/dev/null | head -10"
                ),
                "suid_files": _cmd(
                    f"find /usr/bin /usr/sbin /bin /sbin -perm -4000 2>/dev/null | head -{MAX_SUID_FILES}"
                ),
                "world_writable": _cmd(
                    "find /tmp /var/tmp -world-writable -not -sticky 2>/dev/null | head -10 || echo 'N/A'"
                ),
                # Sieć
                "network_interfaces": _cmd(
                    f"ip addr show 2>/dev/null | grep -E '(^[0-9]+:|inet )' | head -{MAX_NETWORK_INTERFACES_DIAG}"
                ),
                "routing_table": _cmd("ip route 2>/dev/null | head -10"),
                "dns_config": _cmd(
                    "cat /etc/resolv.conf 2>/dev/null | grep -v '^#' | head -5"
                ),
                "hosts_file": _cmd(
                    "cat /etc/hosts 2>/dev/null | grep -v '^#' | grep -v '^$' | head -10"
                ),
                # Procesy sieciowe
                "network_processes": _cmd(
                    f"ss -tlnp 2>/dev/null | grep -v '127.0.0.1\\|::1' | awk 'NR>1 {{print $4, $6}}' | head -{MAX_SUID_FILES}"
                ),
                "suspicious_connections": _cmd(
                    f"ss -tnp 2>/dev/null | grep -v '127.0.0.1\\|::1\\|LISTEN' | grep ESTAB | head -{MAX_AUTH_FAILURES}"
                ),
                # Fail2ban / intrusion detection
                "fail2ban": _cmd(
                    "fail2ban-client status 2>/dev/null | head -5 || echo 'fail2ban nie zainstalowany'"
                ),
                "auth_failures": _cmd(
                    f"journalctl -u sshd --no-pager -n {MAX_SECURITY_LOGS} 2>/dev/null | grep -i 'failed\\|invalid' | tail -{MAX_AUTH_FAILURES} || grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -10 || echo 'N/A'"
                ),
            }
        )
    elif IS_WINDOWS:
        result.update(
            {
                "firewall_state": _cmd(
                    "netsh advfirewall show allprofiles state 2>nul"
                ),
                "open_ports": _cmd("netstat -an 2>nul | findstr LISTENING | head -20"),
                "windows_defender": _cmd(
                    'powershell -Command "Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled" 2>nul'
                ),
                "security_updates": _cmd(
                    'powershell -Command "(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search("IsInstalled=0 and Type=\'Software\' and IsHidden=0").Updates | Where-Object {$_.AutoSelectOnWebSites} | Measure-Object | Select-Object Count" 2>nul'
                ),
            }
        )
    elif IS_MAC:
        result.update(
            {
                "firewall_state": _cmd(
                    "defaults read /Library/Preferences/com.apple.alf globalstate 2>/dev/null"
                ),
                "open_ports": _cmd("netstat -an 2>/dev/null | grep LISTEN | head -20"),
                "gatekeeper": _cmd("spctl --status 2>/dev/null"),
                "sip_status": _cmd("csrutil status 2>/dev/null"),
            }
        )

    return result
