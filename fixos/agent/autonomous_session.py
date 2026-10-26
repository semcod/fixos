"""
Autonomous Session for fixOS Agent
Handles self-directed diagnostic and repair sessions with LLM.
"""

import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import FixOsConfig
from ..constants import (
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_TOKEN_LIMIT,
    MAX_COMMAND_LENGTH,
    MAX_OUTPUT_PREVIEW_LENGTH,
    MAX_SEARCH_QUERY_LENGTH,
    UI_BORDER_WIDTH,
)
from ..providers.llm import LLMAuthError, LLMClient, LLMError
from ..utils.anonymizer import anonymize, deanonymize, display_anonymized_preview
from ..utils.timeout import SessionTimeout
from ..utils.web_search import format_results_for_llm, search_all

# Commands NEVER executed automatically
FORBIDDEN_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"dd\s+if=",
    r"mkfs\.",
    r":\(\)\{ :|:& };:",
    r"chmod\s+-R\s+777",
    r">\s+/dev/sd",
    r"fdisk|parted|gdisk",
    r"systemctl\s+disable\s+--now\s+(network|sshd|firewalld)",
    r"iptables\s+-F",
    r"passwd\s+root",
]

SUDO_PREFIXES = [
    "dnf",
    "rpm",
    "systemctl",
    "firewall-cmd",
    "setenforce",
    "modprobe",
    "rmmod",
    "alsactl",
    "grub2-",
    "update-grub",
]

SYSTEM_PROMPT_AUTONOMOUS = """Jesteś autonomicznym agentem diagnostyki Linux, Windows, macOS.

Działasz w pętli: OBSERVE → ANALYZE → ACT → VERIFY

Protokół odpowiedzi (WYMAGANY format JSON):
{
  "analysis": "krótka analiza sytuacji",
  "severity": "critical|high|medium|low",
  "action": "EXEC|SEARCH|SKIP|DONE",
  "command": "komenda do wykonania (gdy action=EXEC)",
  "search_query": "zapytanie (gdy action=SEARCH)",
  "reason": "uzasadnienie akcji",
  "next_step": "co sprawdzimy po tej akcji"
}

Zasady:
1. Zaczynaj od najbezpieczniejszych akcji (read-only: status, list, check)
2. Wykonuj jedną komendę naraz, weryfikuj wynik przed następną
3. Nigdy nie wykonuj destrukcyjnych operacji (rm -rf, mkfs, fdisk)
4. Gdy nie masz pewności → action=SEARCH lub action=SKIP
5. Po naprawieniu problemu zweryfikuj fix
6. Zakończ gdy action=DONE lub po MAX_FIXES naprawach
"""


@dataclass
class FixAction:
    command: str
    reason: str
    result: str | None = None
    success: bool | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentReport:
    fixes_applied: list = field(default_factory=list)
    searches_done: list = field(default_factory=list)
    problems_found: list = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def summary(self) -> str:
        elapsed = int(time.time() - self.start_time)
        successful = failed = simulated = 0
        action_lines = []
        for i, action in enumerate(self.fixes_applied, 1):
            if action.result == "[DRY-RUN]":
                simulated += 1
                icon = "🧪"
            elif action.success is True:
                successful += 1
                icon = "✅"
            elif action.success is False:
                failed += 1
                icon = "❌"
            else:
                icon = "❔"
            action_lines.append(f"    {i}. {icon} `{action.command}`")
            action_lines.append(f"       Powód: {action.reason}")

        lines = [
            f"  ⏱️  Czas: {elapsed}s",
            f"  🔧 Udane operacje: {successful}",
            f"  ❌ Nieudane operacje: {failed}",
            f"  🧪 Symulacje: {simulated}",
            f"  🔎 Wyszukiwania: {len(self.searches_done)}",
            f"  🔴 Wykryte problemy: {len(self.problems_found)}",
        ]
        if action_lines:
            lines.append("\n  Akcje sesji:")
            lines.extend(action_lines)
        return "\n".join(lines)


class AutonomousSession:
    """Self-directed autonomous diagnostic and repair session."""

    MAX_SEARCHES = 3

    def __init__(
        self,
        diagnostics: dict[str, Any],
        config: FixOsConfig,
        show_data: bool = True,
        max_fixes: int = 10,
        auto_confirm: bool = False,
        use_llm: bool | None = None,
        dry_run: bool = False,
    ):
        self.diagnostics = diagnostics
        self.config = config
        self.show_data = show_data
        self.max_fixes = max_fixes
        self.auto_confirm = auto_confirm
        self.use_llm = use_llm
        self.dry_run = dry_run
        self._heuristic_queue: list[dict[str, Any]] | None = None
        if self.use_llm is False:
            self.llm = None
        else:
            try:
                self.llm = LLMClient(config)
            except LLMError:
                if self.use_llm is True:
                    raise
                self.llm = None
        self.report = AgentReport()
        self.fix_count = 0
        self.search_count = 0
        self.messages: list[dict[str, str]] = []
        self.start_time = time.time()
        self._setup_timeout()

    def _is_llm_active(self) -> bool:
        """Return True if LLM calls should be used, False for LLM-free heuristic mode."""
        if getattr(self, "use_llm", None) is False:
            return False
        if getattr(self, "use_llm", None) is True:
            return True
        llm_obj = getattr(self, "llm", None)
        if llm_obj is not None and not isinstance(llm_obj, LLMClient):
            return True
        cfg = getattr(self, "config", None)
        if cfg is None:
            return False
        if hasattr(cfg, "validate") and callable(cfg.validate):
            return len(cfg.validate()) == 0
        return bool(getattr(cfg, "api_key", None))

    def _setup_timeout(self) -> None:
        """Setup session timeout handler."""

        def _timeout_handler(signum, frame) -> None:
            raise SessionTimeout()

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(self.config.session_timeout)

    def _clear_timeout(self) -> None:
        """Clear the timeout alarm."""
        signal.alarm(0)

    def _confirm_start(self) -> bool:
        """Ask user for confirmation before starting autonomous mode."""
        import sys

        llm_active = self._is_llm_active()
        model_label = (
            getattr(self.config, "model", "unknown")
            if llm_active
            else "heurystyki lokalne (bez LLM)"
        )
        print(f"\n{'═' * UI_BORDER_WIDTH}")
        if self.dry_run:
            print("  🧪 TRYB SYMULACJI – komendy nie będą wykonywane.")
        else:
            print("  ⚠️  TRYB AUTONOMICZNY – agent sam wykonuje komendy!")
        print("  Naciśnij Ctrl+C w dowolnym momencie aby przerwać.")
        print("═" * UI_BORDER_WIDTH)
        print(f"\n  Max napraw: {self.max_fixes}")
        print(f"  Timeout sesji: {self.config.session_timeout}s")
        print(f"  Model: {model_label}")

        if getattr(self, "auto_confirm", False):
            print("  Potwierdzenie: automatyczne (--yes / fixos auto)")
            return True

        try:
            confirm = input(
                "\n  Czy na pewno chcesz uruchomić tryb autonomiczny? (yes/N): "
            ).strip()
        except EOFError:
            if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
                print("  Brak interaktywnego terminala — anulowano (użyj --yes lub fixos auto).")
            return False
        if confirm.lower() not in ("yes", "tak"):
            print("  Anulowano. Użyj --mode hitl dla trybu z potwierdzeniem.")
            return False
        return True

    def _initialize_messages(self) -> None:
        """Initialize LLM message history with system prompt and diagnostics."""
        if not self._is_llm_active():
            return
        anon_str, anon_report = anonymize(str(self.diagnostics))
        if self.show_data:
            display_anonymized_preview(anon_str, anon_report)

        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT_AUTONOMOUS},
            {
                "role": "user",
                "content": (
                    f"Dane diagnostyczne system:\n```\n{anon_str}\n```\n\n"
                    f"Rozpocznij analizę i naprawę. Odpowiadaj TYLKO w formacie JSON."
                ),
            },
        ]

    @staticmethod
    def _is_command_applicable_on_host(cmd: str) -> bool:
        """Check whether a heuristic repair command targets tools/units present on this host."""
        import shlex
        import shutil
        from pathlib import Path

        try:
            tokens = shlex.split(cmd)
        except ValueError:
            tokens = cmd.split()
        idx = 0
        while idx < len(tokens) and (
            tokens[idx] in ("sudo", "env", "nohup") or "=" in tokens[idx] or tokens[idx].startswith("-")
        ):
            idx += 1
        if idx >= len(tokens):
            return False
        prog = tokens[idx]
        if (
            prog in ("dnf", "yum", "pacman", "zypper", "apk", "ufw", "firewall-cmd")
            and shutil.which(prog) is None
        ):
            return False
        return not (
            prog == "systemctl"
            and "firewalld" in tokens
            and shutil.which("firewall-cmd") is None
            and not Path("/lib/systemd/system/firewalld.service").exists()
            and not Path("/usr/lib/systemd/system/firewalld.service").exists()
        )

    def _build_heuristic_actions(self) -> list[dict[str, Any]]:
        """Build deterministic repair and safe cleanup actions without LLM."""
        from .session_core import package_cleanup_guard

        actions: list[dict[str, Any]] = []
        seen_commands: set[str] = set()

        def _add_candidate(cmd: str, reason: str, severity: str = "warning") -> None:
            cmd_clean = (cmd or "").strip()
            if not cmd_clean or cmd_clean in seen_commands:
                return
            if self._is_forbidden(cmd_clean) or package_cleanup_guard(cmd_clean):
                return
            if not self._is_command_applicable_on_host(cmd_clean):
                return
            seen_commands.add(cmd_clean)
            if reason and reason not in self.report.problems_found:
                self.report.problems_found.append(reason)
            actions.append(
                {
                    "action": "EXEC",
                    "command": cmd_clean,
                    "reason": reason or "Naprawa heurystyczna (bez LLM)",
                    "analysis": f"[{severity}] {reason or cmd_clean}",
                    "severity": severity,
                }
            )

        diag = self.diagnostics if isinstance(self.diagnostics, dict) else {}

        # 1. Inspect findings already present in diagnostics dict
        for key, val in diag.items():
            if isinstance(val, dict):
                for item in val.get("findings", []) or val.get("problems", []) or []:
                    if isinstance(item, dict) and item.get("command"):
                        sev = str(item.get("severity", "warning")).lower()
                        if sev in ("critical", "warning", "high", "error"):
                            _add_candidate(
                                str(item["command"]),
                                str(item.get("title") or item.get("description") or key),
                                sev,
                            )

        # 2. Run offline diagnostic plugins if no findings were pre-populated
        if not actions and diag.get("_run_plugins", True) is not False:
            try:
                from ..plugins.base import Severity
                from ..plugins.registry import PluginRegistry

                registry = PluginRegistry()
                registry.discover()
                for res in registry.run():
                    for finding in res.findings:
                        if finding.command and finding.severity in (
                            Severity.CRITICAL,
                            Severity.WARNING,
                        ):
                            _add_candidate(
                                finding.command,
                                f"{finding.title}: {finding.description}",
                                finding.severity.value,
                            )
            except Exception:  # noqa: BLE001, S110
                pass

        # 3. Extract safe disk cleanup suggestions if disk_analysis is present
        disk_analysis = diag.get("disk_analysis")
        if isinstance(disk_analysis, dict):
            suggestions = disk_analysis.get("suggestions", [])
            if suggestions:
                try:
                    from ..interactive.cleanup_planner import CleanupPlanner

                    plan = CleanupPlanner().create_cleanup_plan(suggestions)
                    for item in plan.get("prioritized_actions", []):
                        if item.get("safe") and item.get("command"):
                            _add_candidate(
                                str(item["command"]),
                                str(item.get("description") or "Bezpieczne czyszczenie dysku"),
                                str(item.get("priority") or "medium"),
                            )
                except Exception:  # noqa: BLE001, S110
                    pass

        return actions

    def _process_heuristic_turn(self) -> bool:
        """Execute one deterministic turn without calling an LLM."""
        self._check_timeout()
        if self._heuristic_queue is None:
            self._heuristic_queue = self._build_heuristic_actions()

        if not self._heuristic_queue:
            self._handle_done()
            return False

        remaining = self._get_remaining_time()
        print(
            f"  ⟳ Tura {self.fix_count + 1}/{self.max_fixes} | ⏰ {remaining}s pozostało (tryb bez LLM)"
        )
        action_data = self._heuristic_queue.pop(0)
        analysis = action_data.get("analysis", "")
        reason = action_data.get("reason", "")
        print(f"\n  📋 Analiza: {analysis}")
        print(f"  🎯 Akcja: EXEC – {reason}")

        self._handle_exec(action_data)
        return True

    def _get_remaining_time(self) -> int:
        """Get remaining session time in seconds."""
        from . import get_remaining_time

        return get_remaining_time(self)

    def _check_timeout(self) -> None:
        """Check if session has timed out."""
        if self._get_remaining_time() <= 0:
            raise SessionTimeout()

    def _query_llm(self) -> str | None:
        """Query LLM and return reply."""
        try:
            if self.llm is None:
                self.llm = LLMClient(self.config)
            return self.llm.chat(
                self.messages, max_tokens=DEFAULT_TOKEN_LIMIT, temperature=0.1
            )
        except LLMAuthError as e:
            print(f"  ❌ LLM błąd: {e}")
            print("  Sesja zakończona: popraw klucz API i uruchom ponownie.")
            self.llm_auth_failed = True
            return None
        except LLMError as e:
            print(f"  ❌ LLM błąd: {e}")
            return None

    def _handle_llm_error(self) -> bool:
        """Handle LLM error - try web search if enabled."""
        if self.config.enable_web_search and self.search_count < self.MAX_SEARCHES:
            results = search_all("fedora repair diagnostics", self.config.serpapi_key)
            if results:
                self.messages.append(
                    {"role": "user", "content": format_results_for_llm(results)}
                )
                self.search_count += 1
                return True
        return False

    def _parse_action(self, reply: str) -> dict[str, Any] | None:
        """Parse JSON action from LLM reply."""
        import json

        patterns = [
            r"```(?:json)?\s*(\{.*?\})\s*```",
            r"(\{[^{}]*\"action\"[^{}]*\})",
        ]
        for pattern in patterns:
            m = re.search(pattern, reply, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
        try:
            return json.loads(reply.strip())
        except json.JSONDecodeError:
            return None

    def _is_forbidden(self, cmd: str) -> str | None:
        """Check if command is forbidden."""
        for pattern in FORBIDDEN_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return f"Komenda pasuje do wzorca zabronionego: {pattern}"
        return None

    def _add_sudo(self, cmd: str) -> str:
        """Add sudo if command requires it."""
        if cmd.strip().startswith("sudo"):
            return cmd
        for prefix in SUDO_PREFIXES:
            if cmd.strip().startswith(prefix):
                return f"sudo {cmd.strip()}"
        return cmd

    def _execute_command(self, cmd: str) -> tuple[bool, str]:
        """Execute command and return (success, output)."""
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=DEFAULT_COMMAND_TIMEOUT,
                check=False,
            )
            out = proc.stdout.strip() or proc.stderr.strip() or "(brak outputu)"
            return proc.returncode == 0, out[:MAX_OUTPUT_PREVIEW_LENGTH]
        except subprocess.TimeoutExpired:
            return False, f"[TIMEOUT {DEFAULT_COMMAND_TIMEOUT}s]"
        except Exception as e:  # noqa: BLE001 - report any command failure to the LLM loop
            return False, f"[WYJĄTEK: {e}]"

    def _handle_search(self, action_data: dict[str, Any]) -> bool:
        """Handle SEARCH action - perform web search."""
        query = action_data.get("search_query", "fedora fix")
        if self.search_count < self.MAX_SEARCHES:
            results = search_all(query, self.config.serpapi_key)
            self.search_count += 1
            self.report.searches_done.append(query)
            if results:
                web_ctx = format_results_for_llm(results)
                self.messages.append(
                    {
                        "role": "user",
                        "content": f"Wyniki dla '{query}':\n{web_ctx}\nKontynuuj naprawę.",
                    }
                )
            else:
                self.messages.append(
                    {
                        "role": "user",
                        "content": f"Brak wyników dla '{query}'. Co innego możemy zrobić?",
                    }
                )
            return True
        else:
            print("  ⚠️  Limit wyszukiwań osiągnięty.")
            self.messages.append(
                {
                    "role": "user",
                    "content": "Brak więcej wyszukiwań. Co możemy zrobić bez zewnętrznych źródeł?",
                }
            )
            return False

    def _handle_exec(self, action_data: dict[str, Any]) -> bool:
        """Handle EXEC action - execute command."""
        cmd_raw = action_data.get("command", "").strip()
        reason = action_data.get("reason", "")

        if not cmd_raw:
            self.messages.append(
                {"role": "user", "content": "Brak komendy. Podaj konkretną komendę."}
            )
            return False

        # Security check
        danger = self._is_forbidden(cmd_raw)
        if danger:
            print(f"  🚫 ZABLOKOWANO: {danger}")
            self.messages.append(
                {
                    "role": "user",
                    "content": f"Komenda `{cmd_raw}` jest zabroniona: {danger}. Zaproponuj bezpieczniejszą alternatywę.",
                }
            )
            return False

        cmd = deanonymize(cmd_raw)
        cmd = self._add_sudo(cmd)
        if getattr(self, "dry_run", False):
            print(f"  [DRY-RUN] Pominięto wykonanie: {cmd}")
            self.report.fixes_applied.append(
                FixAction(command=cmd, reason=reason, result="[DRY-RUN]", success=True)
            )
            self.fix_count += 1
            return True

        print(f"  ▶️  Wykonuję: {cmd}")

        ok, out = self._execute_command(cmd)
        fix = FixAction(command=cmd, reason=reason, result=out, success=ok)
        self.report.fixes_applied.append(fix)
        self.fix_count += 1

        icon = "✅" if ok else "❌"
        print(f"  {icon} Wynik: {out[:MAX_COMMAND_LENGTH]}")

        # Anonymize before sending to LLM
        anon_out, _ = anonymize(out)
        anon_cmd, _ = anonymize(cmd)

        self.messages.append(
            {
                "role": "user",
                "content": (
                    f"Wykonano: `{anon_cmd}`\n"
                    f"Sukces: {ok}\n"
                    f"Output: {anon_out[:MAX_SEARCH_QUERY_LENGTH]}\n"
                    f"Zweryfikuj wynik i zaproponuj następną akcję."
                ),
            }
        )
        return True

    def _handle_skip(self, action_data: dict[str, Any]) -> None:
        """Handle SKIP action."""
        reason = action_data.get("reason", "")
        print(f"  ⏭️  Pomijam: {reason}")
        self.messages.append(
            {"role": "user", "content": f"Pominięto: {reason}. Co dalej?"}
        )
        self.fix_count += 1

    def _handle_done(self) -> None:
        """Handle DONE action - session complete."""
        print("\n  ℹ️ Agent zakończył sesję.")

    def _process_turn(self) -> bool:
        """Process one turn of the autonomous session.

        Returns False if session should end, True to continue.
        """
        if not self._is_llm_active():
            return self._process_heuristic_turn()

        self._check_timeout()
        remaining = self._get_remaining_time()
        print(
            f"  ⟳ Tura {self.fix_count + 1}/{self.max_fixes} | ⏰ {remaining}s pozostało"
        )

        # Query LLM
        reply = self._query_llm()
        if reply is None:
            # Retrying a rejected key only repeats the failure.
            return not getattr(
                self, "llm_auth_failed", False
            ) and self._handle_llm_error()

        self.messages.append({"role": "assistant", "content": reply})

        # Parse action
        action_data = self._parse_action(reply)
        if not action_data:
            print("  ⚠️  Nieprawidłowy format JSON, kontynuuję...")
            self.messages.append(
                {
                    "role": "user",
                    "content": "Odpowiedz TYLKO w formacie JSON jak w instrukcji.",
                }
            )
            return True

        action = action_data.get("action", "SKIP")
        analysis = action_data.get("analysis", "")
        reason = action_data.get("reason", "")

        print(f"\n  📋 Analiza: {analysis}")
        print(f"  🎯 Akcja: {action} – {reason}")

        # Handle different actions
        if action == "DONE":
            self._handle_done()
            return False

        if action == "SKIP":
            self._handle_skip(action_data)
            return True

        if action == "SEARCH":
            self._handle_search(action_data)
            return True

        if action == "EXEC":
            self._handle_exec(action_data)
            time.sleep(1)
            return True

        return True

    def run(self) -> AgentReport:
        """Run the autonomous session."""
        if not self._confirm_start():
            return self.report

        self._initialize_messages()
        print("\n\n  🤖 Agent uruchomiony...\n")

        try:
            while self.fix_count < self.max_fixes:
                should_continue = self._process_turn()
                if not should_continue:
                    break
        except SessionTimeout:
            print("\n  ⏰ Timeout sesji.")
        except KeyboardInterrupt:
            print("\n\n  ⛔ Przerwano przez użytkownika (Ctrl+C).")
        finally:
            self._clear_timeout()

        self._print_report()
        return self.report

    def _print_report(self) -> None:
        """Print session report."""
        print(f"\n{'═' * UI_BORDER_WIDTH}")
        print("  📊 RAPORT SESJI AUTONOMICZNEJ")
        print("═" * UI_BORDER_WIDTH)
        print(self.report.summary())
        print(f"{'═' * UI_BORDER_WIDTH}\n")


def run_autonomous_session(
    diagnostics: dict[str, Any],
    config: FixOsConfig,
    show_data: bool = True,
    max_fixes: int = 10,
    auto_confirm: bool = False,
    use_llm: bool | None = None,
    dry_run: bool = False,
) -> AgentReport:
    """Run autonomous session (backward compatible wrapper)."""
    session = AutonomousSession(
        diagnostics=diagnostics,
        config=config,
        show_data=show_data,
        max_fixes=max_fixes,
        auto_confirm=auto_confirm,
        use_llm=use_llm,
        dry_run=dry_run,
    )
    return session.run()
