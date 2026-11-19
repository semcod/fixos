"""
Command handlers for HITL session.
Each handler processes a specific user command type while preserving an optional
session-scoped AnonymizationContext across turns.
"""

from __future__ import annotations

import hashlib
import json
import re
from difflib import get_close_matches

from ..constants import (
    CLEANUP_TIMEOUT_ESTIMATE,
    DEFAULT_COMMAND_TIMEOUT,
    FAST_COMMAND_TIMEOUT,
    LONG_COMMAND_TIMEOUT,
    MAX_ANON_PREVIEW_LENGTH,
    MAX_DIRECT_CMD_PREVIEW_LENGTH,
    MAX_STDERR_PREVIEW_LENGTH,
)
from ..platform_utils import (
    elevate_cmd,
    is_dangerous,
    is_interactive_blocker,
    run_command,
)
from ..utils.anonymizer import (
    ALIAS_RE,
    AnonymizationContext,
    anonymize,
    deanonymize,
)
from ..utils.web_search import format_results_for_llm, search_all
from . import session_io as io
from .session_core import (
    CmdResult,
    DiagnosticChoice,
    RemediationAction,
    package_cleanup_guard,
    select_recommended_actions,
)


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


def _resolve_with_context(
    cmd: str,
    anonymization_context: AnonymizationContext | None,
) -> str:
    """Resolve bound session aliases when a contextual alias map is active."""
    if anonymization_context is None or not ALIAS_RE.search(cmd):
        return cmd
    return deanonymize(
        cmd,
        context=anonymization_context,
        allowed_aliases=set(anonymization_context.reverse_map),
    )


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


def handle_describe_problem(
    messages: list,
    ask_fn,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> bool:
    """Handle [D] Describe own problem command."""
    problem = ask_fn()
    if problem:
        anon_problem, _ = anonymize(problem, context=anonymization_context)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"User describes a new problem:\n"
                    f"{anon_problem}\n\n"
                    f"Analyze this problem and return the required structured remediation plan."
                ),
            }
        )
    return True


def is_cleanup_intent(user_in: str) -> bool:
    """Recognize a bounded single-word spelling variant of ``cleanup``."""
    normalized = user_in.strip().lower()
    if not re.fullmatch(r"[a-z]{5,10}", normalized):
        return False
    return bool(get_close_matches(normalized, ("cleanup",), n=1, cutoff=0.82))


def handle_cleanup_intent(messages: list) -> bool:
    """Ask for a cleanup plan without authorizing or executing any command."""
    messages.append(
        {
            "role": "user",
            "content": (
                "User intent was normalized to cleanup planning only. Review the "
                "available diagnostic evidence for reclaimable space and stale "
                "resources. Return the required structured remediation plan with "
                "exact affected targets, effects, ordered commands and read-only "
                "verification. Do not execute anything and do not infer approval."
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
    action: RemediationAction,
    results: list[CmdResult],
    expected_steps: int,
    *,
    anonymization_context: AnonymizationContext | None = None,
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
        anonymous_command, _ = anonymize(result.cmd, context=anonymization_context)
        steps.append(
            {
                "phase": result.phase,
                "command": anonymous_command,
                "outcome": result.outcome,
                "returnCode": result.returncode,
            }
        )
        anonymous_output, _ = anonymize(
            result.stdout + "\n" + result.stderr,
            context=anonymization_context,
        )
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
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> str:
    """Execute one selected strategy, stopping mutation steps on first refusal."""
    results: list[CmdResult] = []
    for index, command in enumerate(action.commands, 1):
        resolved_cmd = _resolve_with_context(command, anonymization_context)
        result = run_cmd_fn(
            resolved_cmd,
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
            resolved_cmd = _resolve_with_context(command, anonymization_context)
            result = run_cmd_fn(
                resolved_cmd,
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
            "content": _remediation_feedback(
                action,
                results,
                expected_steps,
                anonymization_context=anonymization_context,
            ),
        }
    )
    return outcome


def handle_execute_all(
    fixes: list,
    messages: list,
    executed: list,
    run_cmd_fn,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> bool:
    """Handle [A] Execute all commands."""
    if not fixes:
        io.print_no_commands()
        return True

    if any(isinstance(fix, DiagnosticChoice) for fix in fixes):
        io.print_select_one()
        return True

    selected_fixes = fixes
    if all(isinstance(fix, RemediationAction) for fix in fixes):
        selected_fixes = select_recommended_actions(fixes)
    selected_fixes = _sort_fixes_by_priority(selected_fixes)
    io.print_executing_all(len(selected_fixes))

    if all(isinstance(fix, RemediationAction) for fix in selected_fixes):
        completed_findings: set[str] = set()
        for action in selected_fixes:
            outcome = _execute_remediation_action(
                action,
                messages,
                executed,
                run_cmd_fn,
                anonymization_context=anonymization_context,
            )
            if outcome == "SUCCEEDED":
                completed_findings.add(action.finding_ref)
            if outcome != "SUCCEEDED":
                break
        fixes[:] = [
            fix
            for fix in fixes
            if not (
                isinstance(fix, RemediationAction)
                and fix.finding_ref in completed_findings
            )
        ]
        return True

    summary_lines = []
    for cmd, comment in selected_fixes:
        resolved_cmd = _resolve_with_context(cmd, anonymization_context)
        result = run_cmd_fn(resolved_cmd, comment)
        executed.append(result)
        anon_cmd, _ = anonymize(resolved_cmd, context=anonymization_context)
        anon_out, _ = anonymize(
            result.stdout + result.stderr,
            context=anonymization_context,
        )
        status = "✅ sukces" if result.ok else f"❌ błąd (kod {result.returncode})"
        summary = f"- `{anon_cmd}`: {status}"
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
    user_in: str,
    fixes: list,
    messages: list,
    executed: list,
    run_cmd_fn,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> bool:
    """Handle [N] Execute specific fix by number."""
    idx = int(user_in) - 1
    if 0 <= idx < len(fixes):
        selected = fixes[idx]
        if isinstance(selected, DiagnosticChoice):
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The human selected exactly one diagnosed optimization "
                        "to address next. This selection is planning focus, not "
                        "execution authority.\n"
                        f"Diagnosis choice: Problem {selected.source_number}: "
                        f"{selected.title}\n"
                        f"Diagnosis severity: {selected.severity}\n\n"
                        "Return a fixos.remediation-plan/v2 PLAN for only this "
                        "problem. Include exact affected_targets, concrete repair "
                        "commands and read-only verification. Do not include "
                        "other findings."
                    ),
                }
            )
            return True
        if isinstance(selected, RemediationAction):
            outcome = _execute_remediation_action(
                selected,
                messages,
                executed,
                run_cmd_fn,
                anonymization_context=anonymization_context,
            )
            if outcome == "SUCCEEDED":
                fixes[:] = [
                    fix
                    for fix in fixes
                    if not (
                        isinstance(fix, RemediationAction)
                        and fix.finding_ref == selected.finding_ref
                    )
                ]
            return True
        cmd, comment = selected
        resolved_cmd = _resolve_with_context(cmd, anonymization_context)
        result = run_cmd_fn(resolved_cmd, comment)
        executed.append(result)
        anon_cmd, _ = anonymize(resolved_cmd, context=anonymization_context)
        anon_out, _ = anonymize(result.stdout, context=anonymization_context)
        anon_err, _ = anonymize(result.stderr, context=anonymization_context)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Executed: `{anon_cmd}`\n"
                    f"Success: {result.ok}\n"
                    f"Stdout:\n```\n{anon_out[:MAX_ANON_PREVIEW_LENGTH]}\n```\n"
                    f"Stderr:\n```\n{anon_err[:MAX_STDERR_PREVIEW_LENGTH]}\n```\n"
                    f"What next?"
                ),
            }
        )
        if result.ok:
            fixes.pop(idx)
    else:
        io.print_invalid_option(user_in, len(fixes))
    return True


def handle_direct_command(
    user_in: str,
    messages: list,
    executed: list,
    run_cmd_fn,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> bool:
    """Handle [!cmd] Direct command execution."""
    raw_cmd = user_in[1:].strip()
    resolved_cmd = _resolve_with_context(raw_cmd, anonymization_context)
    result = run_cmd_fn(resolved_cmd, "Komenda użytkownika")
    executed.append(result)
    anon_cmd, _ = anonymize(resolved_cmd, context=anonymization_context)
    anon_out, _ = anonymize(
        f"{result.stdout}\n{result.stderr}",
        context=anonymization_context,
    )
    messages.append(
        {
            "role": "user",
            "content": (
                f"User ran: `{anon_cmd}`\n"
                f"Result: {anon_out[:MAX_DIRECT_CMD_PREVIEW_LENGTH]}\n"
                f"What next?"
            ),
        }
    )
    return True


def handle_search(
    user_in: str,
    messages: list,
    serpapi_key: str | None,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> bool:
    """Handle [search <q>] Web search command."""
    query = user_in[7:].strip()
    results = search_all(query, serpapi_key)
    if results:
        web_ctx = format_results_for_llm(results)
        io.console.print(web_ctx)
        anon_query, _ = anonymize(query, context=anonymization_context)
        anon_ctx, _ = anonymize(web_ctx, context=anonymization_context)
        messages.append(
            {
                "role": "user",
                "content": f"Search results for '{anon_query}':\n{anon_ctx}\nWhat do you think?",
            }
        )
    else:
        io.print_no_results()
    return True


def handle_free_text(
    user_in: str,
    messages: list,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> bool:
    """Handle free text input → send anonymized payload to LLM."""
    anon_text, _ = anonymize(user_in, context=anonymization_context)
    messages.append({"role": "user", "content": anon_text})
    return True


def run_single_command(
    cmd: str,
    comment: str,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> CmdResult:
    """Run a command with full transparency and safety checks."""
    if anonymization_context is not None and ALIAS_RE.search(cmd):
        cmd = deanonymize(
            cmd,
            context=anonymization_context,
            allowed_aliases=set(anonymization_context.reverse_map),
        )
    else:
        cmd = deanonymize(cmd)
    cmd = elevate_cmd(cmd)

    package_guard = package_cleanup_guard(cmd)
    if package_guard:
        io.print_blocked_command(cmd, package_guard)
        return CmdResult(
            cmd=cmd,
            comment=comment,
            ok=False,
            stdout="",
            stderr=f"Zablokowano: {package_guard}",
            returncode=-98,
        )

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

    with io.suspend_timeout():
        ok, stdout, stderr, rc = run_command(cmd, timeout=timeout)

    io.console.print(f"\r{' ' * 30}\r", end="")
    result = CmdResult(
        cmd=cmd, comment=comment, ok=ok, stdout=stdout, stderr=stderr, returncode=rc
    )
    io.print_cmd_result(result)
    return result


def parse_user_input(
    user_in: str,
    fixes: list,
    messages: list,
    executed: list,
    serpapi_key: str | None,
    *,
    anonymization_context: AnonymizationContext | None = None,
) -> tuple[bool, bool]:
    """
    Parse user input and execute appropriate handler.

    Returns:
        Tuple of (should_continue, was_handled)
    """
    if not user_in:
        return True, True

    lo = user_in.lower()

    if lo in ("q", "quit", "exit", "koniec"):
        return handle_quit(), True

    if lo == "d":
        return (
            handle_describe_problem(
                messages,
                io.ask_user_problem,
                anonymization_context=anonymization_context,
            ),
            True,
        )

    if lo in ("s", "skip", "pomiń", "pomin"):
        return handle_skip_all(messages), True

    if lo in ("a", "all", "wszystkie"):
        return (
            handle_execute_all(
                fixes,
                messages,
                executed,
                run_single_command,
                anonymization_context=anonymization_context,
            ),
            True,
        )

    if user_in.isdigit():
        return (
            handle_fix_by_number(
                user_in,
                fixes,
                messages,
                executed,
                run_single_command,
                anonymization_context=anonymization_context,
            ),
            True,
        )

    if user_in.startswith("!"):
        return (
            handle_direct_command(
                user_in,
                messages,
                executed,
                run_single_command,
                anonymization_context=anonymization_context,
            ),
            True,
        )

    if lo.startswith("search "):
        return (
            handle_search(
                user_in,
                messages,
                serpapi_key,
                anonymization_context=anonymization_context,
            ),
            True,
        )

    if is_cleanup_intent(user_in):
        return handle_cleanup_intent(messages), True

    return True, False
