"""
Human-in-the-Loop (HITL) Session for fixOS Agent
Interactive session where user approves each action.
"""

import time
from typing import Dict, Any, List

from ..providers.llm import LLMClient, LLMError
from ..utils.anonymizer import anonymize, deanonymize, display_anonymized_preview
from ..utils.web_search import search_all, format_results_for_llm
from ..config import FixOsConfig
from ..platform_utils import (
    setup_signal_timeout,
    cancel_signal_timeout,
    get_os_info,
    get_package_manager,
)
from ..utils.timeout import SessionTimeout

from .session_core import (
    CmdResult,
    DiagnosticChoice,
    RemediationAction,
    SYSTEM_PROMPT,
    extract_diagnostic_choices,
    extract_remediation_actions,
    extract_search_topic,
    strip_remediation_plan,
    transform_remediation_commands,
)
from . import session_io as io
from . import session_handlers as handlers


class HITLSession:
    """Interactive Human-in-the-Loop diagnostic and repair session."""

    MAX_WEB_SEARCHES = 3

    def __init__(
        self,
        diagnostics: Dict[str, Any],
        config: FixOsConfig,
        show_data: bool = True,
    ):
        self.diagnostics = diagnostics
        self.config = config
        self.show_data = show_data
        self.llm = LLMClient(config)
        self.os_info = get_os_info()
        self.pkg_manager = get_package_manager() or "unknown"
        self.messages: List[Dict[str, str]] = []
        self.executed: List[CmdResult] = []
        self.web_search_count = 0
        self.last_fixes: List[RemediationAction | DiagnosticChoice] = []
        self._diagnosis_queue_active = False
        self._pending_optimizations: List[DiagnosticChoice] = []
        self._focused_optimization: DiagnosticChoice | None = None
        self._remediation_queue_active = False
        self._pending_remediations: List[RemediationAction] = []
        self._completed_finding_refs: set[str] = set()
        self.start_ts = time.time()
        self._setup_timeout()

    def _setup_timeout(self) -> None:
        """Setup session timeout handler."""
        from . import session_io

        def _timeout(signum, frame) -> None:
            raise SessionTimeout()

        # Store reference in session_io for reinstatement during user input
        session_io._setup_timeout_ref(self, self.config.session_timeout, _timeout)
        setup_signal_timeout(self.config.session_timeout, _timeout)

    def _clear_timeout(self) -> None:
        """Clear the timeout alarm."""
        cancel_signal_timeout()

    def remaining(self) -> int:
        """Get remaining session time in seconds."""
        from . import get_remaining_time

        return get_remaining_time(self)

    def _initialize_messages(self) -> bool:
        """Initialize LLM message history with system prompt and diagnostics."""
        anon_str, report = anonymize(str(self.diagnostics))

        if self.show_data:
            display_anonymized_preview(anon_str, report)
            if not io.ask_send_data():
                io.console.print("  Anulowano.")
                return False

        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"OS: {self.os_info['system']} {self.os_info['release']} | "
                    f"Package manager: {self.pkg_manager}\n\n"
                    f"Anonymized diagnostic data:\n```\n{anon_str}\n```\n\n"
                    f"Perform full analysis and list all detected problems."
                ),
            },
        ]
        return True

    def _print_header(self) -> None:
        """Print session header with system info."""
        io.print_session_header(
            self.os_info,
            self.pkg_manager,
            self.config.model,
            self.config.session_timeout,
            self.remaining,
        )

    def _handle_llm_error(self) -> bool:
        """Handle LLM error - try web search if enabled."""
        if (
            self.config.enable_web_search
            and self.web_search_count < self.MAX_WEB_SEARCHES
        ):
            self.web_search_count += 1
            io.print_searching()
            results = search_all(
                "linux system diagnostics repair", self.config.serpapi_key
            )
            if results:
                io.console.print(format_results_for_llm(results))
                return True
        return False

    def _check_low_confidence(self, reply: str) -> bool:
        """Check if LLM is uncertain and perform web search if enabled."""
        low_conf = any(
            p in reply.lower()
            for p in [
                "nie wiem",
                "nie jestem pewien",
                "i don't know",
                "not sure",
                "cannot determine",
            ]
        )
        if (
            low_conf
            and self.config.enable_web_search
            and self.web_search_count < self.MAX_WEB_SEARCHES
        ):
            if io.ask_low_confidence_search():
                self.web_search_count += 1
                topic = extract_search_topic(reply)
                results = search_all(topic, self.config.serpapi_key)
                if results:
                    web_ctx = format_results_for_llm(results)
                    io.console.print(web_ctx)
                    self.messages.append(
                        {
                            "role": "user",
                            "content": f"External sources:\n{web_ctx}\nUpdate analysis.",
                        }
                    )
                    return True
        return False

    def _select_turn_choices(
        self, reply: str
    ) -> list[RemediationAction | DiagnosticChoice]:
        """Build the next menu while preserving the iterative queue."""
        actions = [
            transform_remediation_commands(action, deanonymize)
            for action in extract_remediation_actions(reply)
            if action.finding_ref not in self._completed_finding_refs
        ]

        if self._diagnosis_queue_active:
            if self._focused_optimization is not None:
                if actions:
                    focused_ref = actions[0].finding_ref
                    return [
                        action
                        for action in actions
                        if action.finding_ref == focused_ref
                    ]
                return [self._focused_optimization]
            return list(self._pending_optimizations)

        if self._remediation_queue_active:
            if actions:
                updated_refs = {action.finding_ref for action in actions}
                self._pending_remediations = [
                    action
                    for action in self._pending_remediations
                    if action.finding_ref not in updated_refs
                ] + actions
            return list(self._pending_remediations)

        if actions:
            self._remediation_queue_active = True
            self._pending_remediations = actions
            return list(actions)

        diagnosed = extract_diagnostic_choices(reply)
        if diagnosed:
            self._diagnosis_queue_active = True
            self._pending_optimizations = diagnosed
            return list(diagnosed)
        return []

    def _record_completed_choices(self, before: list, after: list) -> None:
        """Remove successfully verified findings from the persistent queue."""
        before_refs = {
            choice.finding_ref
            for choice in before
            if isinstance(choice, RemediationAction)
        }
        after_refs = {
            choice.finding_ref
            for choice in after
            if isinstance(choice, RemediationAction)
        }
        completed_refs = before_refs - after_refs
        if not completed_refs:
            return

        self._completed_finding_refs.update(completed_refs)
        self._pending_remediations = [
            action
            for action in self._pending_remediations
            if action.finding_ref not in completed_refs
        ]
        if self._focused_optimization is not None:
            focused_ref = self._focused_optimization.finding_ref
            self._pending_optimizations = [
                choice
                for choice in self._pending_optimizations
                if choice.finding_ref != focused_ref
            ]
            self._focused_optimization = None

    def _reset_diagnosis_queue(self) -> None:
        """Let a newly described problem replace the current fallback queue."""
        self._diagnosis_queue_active = False
        self._pending_optimizations = []
        self._focused_optimization = None
        self._remediation_queue_active = False
        self._pending_remediations = []

    def _process_turn(self) -> bool:
        """Process one turn of the HITL session."""
        rem = self.remaining()
        if rem <= 0:
            raise SessionTimeout()

        io.print_thinking()
        try:
            reply = self.llm.chat(self.messages, max_tokens=4000, temperature=0.2)
            self.messages.append({"role": "assistant", "content": reply})
        except LLMError as e:
            io.clear_thinking()
            io.print_llm_error(e)
            if not self._handle_llm_error():
                return False
            return True
        io.clear_thinking()

        io.print_llm_reply(strip_remediation_plan(reply))
        self.last_fixes = self._select_turn_choices(reply)

        if self._check_low_confidence(reply):
            return True

        io.print_action_menu(
            self.last_fixes,
            rem,
            self.llm.total_tokens,
            completed_count=len(self._completed_finding_refs),
        )

        user_in = io.get_user_input(rem)
        if not user_in:
            return True

        selected = None
        if user_in.isdigit():
            index = int(user_in) - 1
            if 0 <= index < len(self.last_fixes):
                selected = self.last_fixes[index]
        choices_before = list(self.last_fixes)

        # Handle all command types via handlers module
        should_continue, was_handled = handlers.parse_user_input(
            user_in,
            self.last_fixes,
            self.messages,
            self.executed,
            self.config.serpapi_key,
        )

        if isinstance(selected, DiagnosticChoice):
            self._focused_optimization = selected
        else:
            self._record_completed_choices(choices_before, self.last_fixes)

        if not was_handled:
            # Free text → send to LLM
            self.messages.append({"role": "user", "content": user_in})
            self._reset_diagnosis_queue()
        elif user_in.lower() in ("d", "s", "skip", "pomiń", "pomin"):
            self._reset_diagnosis_queue()

        return should_continue

    def run(self) -> None:
        """Run the HITL session."""
        if not self._initialize_messages():
            return
        self._print_header()

        try:
            while True:
                should_continue = self._process_turn()
                if not should_continue:
                    break
        except SessionTimeout:
            io.print_timeout()
        finally:
            self._clear_timeout()

        self._print_summary()

    def _print_summary(self) -> None:
        """Print session summary."""
        elapsed = int(time.time() - self.start_ts)
        io.print_session_summary(
            len(self.messages) - 2, elapsed, self.llm.total_tokens, self.executed
        )


def run_hitl_session(
    diagnostics: Dict[str, Any],
    config: FixOsConfig,
    show_data: bool = True,
) -> None:
    """Run interactive HITL session (backward compatible wrapper)."""
    session = HITLSession(
        diagnostics=diagnostics,
        config=config,
        show_data=show_data,
    )
    session.run()


# Backward compatibility exports
__all__ = [
    "CmdResult",
    "HITLSession",
    "run_hitl_session",
    "SYSTEM_PROMPT",
]
