"""
Command handlers for HITL session.
Each handler processes a specific user command type.
"""

import hashlib
import json
import re
from typing import TYPE_CHECKING, Tuple

from ..constants import (
    CLEANUP_TIMEOUT_ESTIMATE,
    DEFAULT_COMMAND_TIMEOUT,
    FAST_COMMAND_TIMEOUT,
    LONG_COMMAND_TIMEOUT,
    MAX_ANON_PREVIEW_LENGTH,
    MAX_STDERR_PREVIEW_LENGTH,
    MAX_DIRECT_CMD_PREVIEW_LENGTH,
)
from ..platform_utils import (
    is_dangerous,
    is_interactive_blocker,
    elevate_cmd,
    run_command,
)
from ..utils.anonymizer import anonymize, deanonymize
from ..utils.web_search import search_all, format_results_for_llm
from . import session_io as io
from .session_core import CmdResult, RemediationAction, select_recommended_actions

if TYPE_CHECKING:
    pass


def _resolve_command_timeout(cmd: str) -> int:
    """Choose timeout based on command type to avoid premature failures."""
    normalized = cmd.strip().lower()

    long_running_patterns = (
        r"\bdnf\s+(update|upgrade|distro-sync|system-upgrade)\b",
        r"\bapt(-get)?\s+(update|upgrade|dist-upgrade|full-upgrade)\b",
        r"\bpacman\s+-S(y|yu|yyu)\b",
        r"\bzypper\s+(refresh|update|dup)\b",
        r"\bflatpak\s+update\b",
        r"\bsnap\s+refresh\b",
    )
    if any(re.search(pattern, normalized) for pattern in long_running_patterns):
        return LONG_COMMAND_TIMEOUT

    fast_read_only_patterns = (
        r"\bdf\b",
        r"\bfree\b",
        r"\bls\b",
        r"\bcat\b",
        r"\bgrep\b",
        r"\bsystemctl\s+status\b",
    )
    if any(re.search(pattern, normalized) for pattern in fast_read_only_patterns):
        return FAST_COMMAND_TIMEOUT

    if CLEANUP_TIMEOUT_ESTIMATE > DEFAULT_COMMAND_TIMEOUT:
        return CLEANUP_TIMEOUT_ESTIMATE
    return DEFAULT_COMMAND_TIMEOUT


def handle_quit() -> bool:
    """Handle [Q] Quit command. Returns False to exit loop."""
    io.print_session_ended()
    return False


def handle_skip_all(messages: list) -> bool:
    """Handle [S] Skip all command."""
    messages.append(
        {"role": "user", "content": "Skip these fixes. What else can we check?"}
    )
    return True


def handle_describe_problem(messages: list, ask_fn) -> bool:
    """Handle [D] Describe own problem command."""
    problem = ask_fn()
    if problem:
        messages.append(
            {
                "role": "user",
                "content": (
                    f"User describes a new problem:\n"
                    f"{problem}\n\n"
                    f"Analyze this problem and return the required structured remediation plan."
                ),
            }
        )
    return True


def _sort_fixes_by_priority(fixes: list) -> list:
    """Move cleanup commands before disk-consuming operations."""
    cleanup_patterns = (
        r"journalctl.*--vacuum",
        r"dnf\s+(remove|autoremove|clean)",
        r"apt(?:-get)?\s+(autoremove|clean)",
        r"pacman\s+-Sc",
        r"rm\s+-[rf]",
        r"swapoff",
    )
    disk_hungry_patterns = (
        r"\bdnf\s+(upgrade|update|distro-sync|install)\b",
        r"\bapt(-get)?\s+(upgrade|install|full-upgrade)\b",
        r"\bpacman\s+-S[yuy]*\b",
        r"\bflatpak\s+(update|install)\b",
    )

    def score(item) -> int:
        if isinstance(item, RemediationAction):
            cmd = " && ".join(item.commands).lower()
        else:
            cmd = item[0].lower()
        if any(re.search(p, cmd) for p in cleanup_patterns):
            return 0
        if any(re.search(p, cmd) for p in disk_hungry_patterns):
            return 2
        return 1

    return sorted(fixes, key=score)


def _tag_result(
    result: CmdResult,
    action: RemediationAction,
    phase: str,
) -> CmdResult:
    result.finding_ref = action.finding_ref
    result.action_id = action.action_id
    result.phase = phase
    return result


def _execution_outcome(results: list[CmdResult], expected_steps: int) -> str:
    if any(not result.ok and not result.skipped for result in results):
        return "FAILED"
    completed = sum(result.ok for result in results)
    if completed == expected_steps:
        return "SUCCEEDED"
    if completed == 0 and any(result.skipped for result in results):
        return "REJECTED"
    return "OBSERVED"


def _remediation_feedback(
    action: RemediationAction, results: list[CmdResult], expected_steps: int
) -> str:
    canonical_input = json.dumps(
        {
            "findingRef": action.finding_ref,
            "actionId": action.action_id,
            "commands": action.commands,
            "verification": action.verification,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    steps = []
    output_context = []
    for result in results:
        anonymous_command, _ = anonymize(result.cmd)
        steps.append(
            {
                "phase": result.phase,
                "command": anonymous_command,
                "outcome": result.outcome,
                "returnCode": result.returncode,
            }
        )
        anonymous_output, _ = anonymize(result.stdout + "\n" + result.stderr)
        if anonymous_output.strip():
            output_context.append(
                f"- {result.phase}/{result.outcome}: "
                f"{anonymous_output.strip()[:MAX_ANON_PREVIEW_LENGTH]}"
            )

    receipt = {
        "schema": "fixos.remediation-result/v1",
        "mode": "APPLY",
        "correlationId": action.finding_ref,
        "findingRef": action.finding_ref,
        "actionId": action.action_id,
        "inputHash": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        "outcome": _execution_outcome(results, expected_steps),
        "steps": steps,
        "rawOutputIncluded": False,
        "secretMaterialIncluded": False,
    }
    message = (
        "Policy-bound remediation result (this result does not grant authority):\n"
        f"```json\n{json.dumps(receipt, ensure_ascii=False, sort_keys=True)}\n```"
    )
    if output_context:
        message += "\nBounded anonymized execution context:\n" + "\n".join(
            output_context
        )
    message += "\nEvaluate verification evidence and propose the next PLAN."
    return message


def _execute_remediation_action(
    action: RemediationAction,
    messages: list,
    executed: list,
    run_cmd_fn,
) -> str:
    """Execute one selected strategy, stopping mutation steps on first refusal."""
    results: list[CmdResult] = []
    for index, command in enumerate(action.commands, 1):
        result = run_cmd_fn(
            command,
            f"[{action.finding_ref}] {action.label} — krok {index}/{len(action.commands)}",
        )
        result = _tag_result(result, action, "remediation")
        results.append(result)
        executed.append(result)
        if not result.ok:
            break

    mutation_complete = len(results) == len(action.commands) and all(
        result.ok for result in results
    )
    if mutation_complete:
        for index, command in enumerate(action.verification, 1):
            result = run_cmd_fn(
                command,
                f"[{action.finding_ref}] weryfikacja {index}/{len(action.verification)}",
            )
            result = _tag_result(result, action, "verification")
            results.append(result)
            executed.append(result)
            if not result.ok:
                break

    expected_steps = len(action.commands) + len(action.verification)
    outcome = _execution_outcome(results, expected_steps)
    messages.append(
        {
            "role": "user",
            "content": _remediation_feedback(action, results, expected_steps),
        }
    )
    return outcome


def handle_execute_all(fixes: list, messages: list, executed: list, run_cmd_fn) -> bool:
    """Handle [A] Execute all commands."""
    if not fixes:
        io.print_no_commands()
        return True

    if all(isinstance(fix, RemediationAction) for fix in fixes):
        fixes = select_recommended_actions(fixes)
    fixes = _sort_fixes_by_priority(fixes)
    io.print_executing_all(len(fixes))

    if all(isinstance(fix, RemediationAction) for fix in fixes):
        for action in fixes:
            outcome = _execute_remediation_action(
                action, messages, executed, run_cmd_fn
            )
            if outcome != "SUCCEEDED":
                break
        return True

    summary_lines = []
    for cmd, comment in fixes:
        result = run_cmd_fn(cmd, comment)
        executed.append(result)
        anon_out, _ = anonymize(result.stdout + result.stderr)
        status = "✅ sukces" if result.ok else f"❌ błąd (kod {result.returncode})"
        summary = f"- `{cmd}`: {status}"
        if anon_out.strip():
            summary += f"\n  Output: {anon_out.strip()[:MAX_ANON_PREVIEW_LENGTH]}"
        summary_lines.append(summary)

    joined_summary = "\n".join(summary_lines)
    messages.append(
        {
            "role": "user",
            "content": (
                f"Executed all commands:\n"
                f"{joined_summary}\n"
                f"\nEvaluate results and suggest next steps."
            ),
        }
    )
    return True


def handle_fix_by_number(
    user_in: str, fixes: list, messages: list, executed: list, run_cmd_fn
) -> bool:
    """Handle [N] Execute specific fix by number."""
    idx = int(user_in) - 1
    if 0 <= idx < len(fixes):
        selected = fixes[idx]
        if isinstance(selected, RemediationAction):
            _execute_remediation_action(selected, messages, executed, run_cmd_fn)
            return True
        cmd, comment = selected
        result = run_cmd_fn(cmd, comment)
        executed.append(result)
        anon_out, _ = anonymize(result.stdout)
        anon_err, _ = anonymize(result.stderr)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Executed: `{cmd}`\n"
                    f"Success: {result.ok}\n"
                    f"Stdout:\n```\n{anon_out[:MAX_ANON_PREVIEW_LENGTH]}\n```\n"
                    f"Stderr:\n```\n{anon_err[:MAX_STDERR_PREVIEW_LENGTH]}\n```\n"
                    f"What next?"
                ),
            }
        )
    else:
        io.print_invalid_option(user_in, len(fixes))
    return True


def handle_direct_command(
    user_in: str, messages: list, executed: list, run_cmd_fn
) -> bool:
    """Handle [!cmd] Direct command execution."""
    cmd = user_in[1:].strip()
    result = run_cmd_fn(cmd, "Komenda użytkownika")
    executed.append(result)
    anon_out, _ = anonymize(f"{result.stdout}\n{result.stderr}")
    messages.append(
        {
            "role": "user",
            "content": f"User ran: `{cmd}`\nResult: {anon_out[:MAX_DIRECT_CMD_PREVIEW_LENGTH]}\nWhat next?",
        }
    )
    return True


def handle_search(user_in: str, messages: list, serpapi_key: str | None) -> bool:
    """Handle [search <q>] Web search command."""
    query = user_in[7:].strip()
    results = search_all(query, serpapi_key)
    if results:
        web_ctx = format_results_for_llm(results)
        io.console.print(web_ctx)
        messages.append(
            {
                "role": "user",
                "content": f"Search results for '{query}':\n{web_ctx}\nWhat do you think?",
            }
        )
    else:
        io.print_no_results()
    return True


def handle_free_text(user_in: str, messages: list) -> bool:
    """Handle free text input → send to LLM."""
    messages.append({"role": "user", "content": user_in})
    return True


def run_single_command(cmd: str, comment: str) -> CmdResult:
    """Run a command with full transparency and safety checks."""
    cmd = deanonymize(cmd)
    cmd = elevate_cmd(cmd)

    # Check for dangerous commands
    danger = is_dangerous(cmd)
    if danger:
        io.print_blocked_command(cmd, danger)
        return CmdResult(
            cmd=cmd,
            comment=comment,
            ok=False,
            stdout="",
            stderr=f"Zablokowano: {danger}",
            returncode=-99,
        )

    # Check for interactive blockers
    blocker = is_interactive_blocker(cmd)
    if blocker:
        io.console.print(f"\n  [bold yellow]⚠️  OSTRZEŻENIE:[/bold yellow] {blocker}")
        io.console.print("  Ta komenda może zawiesić sesję w trybie nieinteraktywnym.")
        if io.console.input("  Czy na pewno chcesz spróbować? [y/N]: ").lower() not in (
            "y",
            "yes",
            "tak",
        ):
            return CmdResult(
                cmd=cmd,
                comment=comment,
                ok=False,
                stdout="",
                stderr="Anulowano przez użytkownika (interaktywna).",
                returncode=-1,
                skipped=True,
            )

    io.print_cmd_preview(cmd, comment)
    ans = io.ask_execute_prompt()
    if ans in ("n", "no", "nie"):
        return CmdResult(
            cmd=cmd,
            comment=comment,
            ok=False,
            stdout="",
            stderr="Pominięto.",
            returncode=-1,
            skipped=True,
        )

    timeout = _resolve_command_timeout(cmd)
    io.console.print("  [dim]⏳ Wykonuję...[/dim]", end="")

    # Suspend session timeout during command execution
    with io.suspend_timeout():
        ok, stdout, stderr, rc = run_command(cmd, timeout=timeout)

    io.console.print(f"\r{' ' * 30}\r", end="")
    result = CmdResult(
        cmd=cmd, comment=comment, ok=ok, stdout=stdout, stderr=stderr, returncode=rc
    )
    io.print_cmd_result(result)
    return result


def parse_user_input(
    user_in: str, fixes: list, messages: list, executed: list, serpapi_key: str | None
) -> Tuple[bool, bool]:
    """
    Parse user input and execute appropriate handler.

    Returns:
        Tuple of (should_continue, was_handled)
        - should_continue: True to continue session, False to exit
        - was_handled: True if input was handled, False if should be treated as free text
    """
    if not user_in:
        return True, True

    lo = user_in.lower()

    # [Q] Quit
    if lo in ("q", "quit", "exit", "koniec"):
        return handle_quit(), True

    # [D] Describe own problem
    if lo == "d":
        return handle_describe_problem(messages, io.ask_user_problem), True

    # [S] Skip all
    if lo in ("s", "skip", "pomiń", "pomin"):
        return handle_skip_all(messages), True

    # [A] Execute all
    if lo in ("a", "all", "wszystkie"):
        return handle_execute_all(fixes, messages, executed, run_single_command), True

    # [N] Execute specific fix by number
    if user_in.isdigit():
        return (
            handle_fix_by_number(
                user_in, fixes, messages, executed, run_single_command
            ),
            True,
        )

    # [!cmd] Direct command execution
    if user_in.startswith("!"):
        return (
            handle_direct_command(user_in, messages, executed, run_single_command),
            True,
        )

    # [search <q>] Web search
    if lo.startswith("search "):
        return handle_search(user_in, messages, serpapi_key), True

    # Not handled - treat as free text
    return True, False
