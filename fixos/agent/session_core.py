"""
Core session types and constants for HITL agent.
"""

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Tuple

from ..constants import (
    MAX_SUMMARY_LENGTH,
    MAX_TECH_TERMS,
)


@dataclass
class CmdResult:
    """Result of executed command."""

    cmd: str
    comment: str
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    skipped: bool = False
    timestamp: float = field(default_factory=time.time)
    finding_ref: str | None = None
    action_id: str | None = None
    phase: str = "remediation"

    @property
    def outcome(self) -> str:
        """Return a bounded wellmanifest/logs-aligned operation outcome."""
        if self.skipped:
            return "REJECTED"
        return "SUCCEEDED" if self.ok else "FAILED"


@dataclass(frozen=True)
class RemediationAction:
    """One policy-labelled strategy for resolving a diagnostic finding."""

    finding_ref: str
    finding_title: str
    severity: str
    category: str
    action_id: str
    label: str
    risk: str
    recommended: bool
    commands: tuple[str, ...]
    verification: tuple[str, ...]
    explanation: str
    evidence: tuple[str, ...] = ()

    @property
    def command(self) -> str:
        """Compatibility view for callers that still expect one command."""
        return " && ".join(self.commands)

    @property
    def comment(self) -> str:
        return self.explanation

    def __iter__(self) -> Iterator[str]:
        """Keep legacy ``cmd, comment = action`` callers working."""
        yield self.command
        yield self.comment


@dataclass(frozen=True)
class DiagnosticChoice:
    """A diagnosed problem that is selectable but has no executable plan yet."""

    finding_ref: str
    source_number: int
    title: str
    severity: str


SYSTEM_PROMPT = """You are an expert Linux/Windows/macOS system diagnostics assistant.

You receive anonymized diagnostic data OR a user-described problem. Your tasks:

1. DIAGNOSE – identify ALL problems (🔴 critical → 🟡 important → 🟢 minor)
2. STRATEGIES – provide concrete, evidence-bound alternatives for each problem
3. VERIFY – every strategy must include read-only verification commands
4. FORMAT – show the human diagnosis, then append one machine-readable plan

━━━ DIAGNOZA ━━━
🔴 Problem 1: [description and the evidence that triggered it]

🟡 Problem 2: [description and evidence]

After the diagnosis append exactly one fenced JSON block in this shape:

```fixos-remediation
{
  "schema": "fixos.remediation-plan/v1",
  "mode": "PLAN",
  "findings": [
    {
      "ref": "finding:fixos:stable-kebab-case-id",
      "severity": "CRITICAL",
      "category": "STORAGE",
      "title": "short problem title",
      "evidence": ["specific anonymized signal=value"],
      "strategies": [
        {
          "id": "stable-kebab-case-action-id",
          "label": "short selectable label",
          "risk": "CAUTION",
          "recommended": true,
          "commands": ["one concrete mutating command per ordered step"],
          "verification": ["read-only command proving the outcome"],
          "explanation": "what this strategy changes and its trade-off"
        }
      ]
    }
  ]
}
```

IMPORTANT RULES:
- Treat each finding as an observed fact, not execution authority. The application
  will ask the human before every command.
- Allowed severities are CRITICAL, ERROR, WARNING and INFO. Allowed categories
  are AUTHORITY, CHAIN, CONCURRENCY, CONFIGURATION, CONTRACT, DEPENDENCY,
  DOCUMENTATION, PROTOBUF, RESOURCE, RUNTIME, SAFETY, SECURITY, STORAGE and
  TRANSPORT. Allowed risks are LOW, CAUTION and HIGH.
- Use stable finding refs and action IDs. Keep independent problems in separate
  findings and bind every strategy only to evidence present in the input.
- Provide two strategies when there are genuinely different safe trade-offs
  (for example immediate recovery versus deeper cleanup). Never invent a risky
  alternative just to increase the option count.
- Mark exactly one strategy as recommended for each finding. `recommended` is a
  policy-filtered default, not approval.
- Commands must be concrete one-line repair steps. Do not use placeholders,
  ellipses or read-only diagnostics in `commands`.
- Put ordered logical steps in separate `commands` array entries. Use shell
  chaining inside one entry only when the operations are an atomic unit.
- Put read-only checks only in `verification`. A successful exit code without
  verification is not proof that the problem is resolved.
- For package upgrades and heavy operations, provide the real fix command (e.g. `dnf upgrade -y`).
- When disk usage is critically high (>90%), ALWAYS propose cleanup commands FIRST.
- NEVER suggest package upgrades or installations BEFORE cleanup has freed sufficient space and been verified.
- Never truncate active systemd journal files, delete active log files, remove an
  enabled swap file, disable a service, kill an application or change persistent
  kernel settings unless the diagnostic evidence establishes the exact target and
  the strategy explains the impact. Use risk HIGH for destructive or persistent
  system changes.

PACKAGE ANALYSIS rules (when "packages" data is present):
- For orphaned packages: propose `sudo dnf autoremove` or remove only exact package names present in evidence.
- For debug/devel packages on desktop: propose `sudo dnf remove '*-debuginfo*'` or specific removals.
- For duplicate RPM+Flatpak apps: propose removing one version (prefer Flatpak for GUI apps).
- For unused Flatpak runtimes: propose `flatpak uninstall --unused`.
- For leaf packages not used in 90+ days: propose specific `sudo dnf remove <pkg>`.
- Always warn user about dependencies that will be removed.

STORAGE OPTIMIZATION rules (when "storage" data is present):
- If unallocated disk space exists: propose `sudo growpart` or `sudo lvextend + resize2fs/xfs_growfs`.
- For btrfs without compression: propose adding `compress=zstd:1` to fstab.
- For old btrfs snapshots: use only exact snapshot IDs present in evidence.
- For swap/zram optimization: propose tuning swappiness or enabling zram.
- If fstrim.timer is disabled on SSD: propose `sudo systemctl enable --now fstrim.timer`.

FILE ANALYSIS rules (when "files" data is present):
- For large files >200MB: list them and propose review/deletion commands.
- For duplicate files: propose `fdupes -d` or `rdfind` commands for interactive dedup.
- For media files (ebooks, mp3, mp4, images): propose organizing/archiving commands:
  - `mkdir -p ~/Archive/{ebooks,muzyka,wideo,obrazy}` + `mv` commands.
  - For compression, use the exact detected source path and an explicit archive path.
- For old downloads (>30 days): propose cleanup of ~/Downloads.
- For trash: propose `rm -rf ~/.local/share/Trash/files/*`.
- Always group suggestions by category (video, music, ebooks, archives, etc.).

IMPORTANT: Adapt commands to the detected OS (Linux/Windows/macOS).
"""


REMEDIATION_PLAN_SCHEMA = "fixos.remediation-plan/v1"
_PLAN_BLOCK_RE = re.compile(
    r"```fixos-remediation\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL
)
_ANY_PLAN_BLOCK_RE = re.compile(
    r"```fixos-remediation\b.*?```", re.IGNORECASE | re.DOTALL
)
_FINDING_REF_RE = re.compile(r"^finding:fixos:[a-z0-9][a-z0-9.-]{2,80}$")
_ACTION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{2,80}$")
_SEVERITIES = {"CRITICAL", "ERROR", "WARNING", "INFO"}
_CATEGORIES = {
    "AUTHORITY",
    "CHAIN",
    "CONCURRENCY",
    "CONFIGURATION",
    "CONTRACT",
    "DEPENDENCY",
    "DOCUMENTATION",
    "PROTOBUF",
    "RESOURCE",
    "RUNTIME",
    "SAFETY",
    "SECURITY",
    "STORAGE",
    "TRANSPORT",
}
_RISKS = {"LOW", "CAUTION", "HIGH"}


def _is_diagnostic_only_command(cmd: str) -> bool:
    """Return True if command is read-only and not a repair action."""
    # Split by common shell delimiters to check each part
    parts = re.split(r"\s*(?:&&|\|\||;|\|)\s*", cmd)

    # If any part of a compound command looks like a repair, the whole thing is actionable
    for part in parts:
        if not _is_part_diagnostic_only(part):
            return False
    return True


def _is_part_diagnostic_only(part: str) -> bool:
    """Helper for _is_diagnostic_only_command to check a single command part."""
    normalized = part.strip().lower()
    if normalized.startswith("sudo "):
        normalized = normalized[5:].strip()

    # Special case: diagnostic tools used for cleanup/repair
    if normalized.startswith("journalctl"):
        if (
            "--vacuum-" in normalized
            or "--flush" in normalized
            or "--rotate" in normalized
        ):
            return False

    if normalized.startswith("find ") and re.search(
        r"(?:\s-delete\b|\s-exec(?:dir)?\s+(?:rm|shred)\b)", normalized
    ):
        return False

    if normalized.startswith("sysctl ") and (
        "=" in normalized or re.search(r"\s-w(?:\s|$)", normalized)
    ):
        return False

    diagnostic_prefixes = (
        "df ",
        "free ",
        "ls ",
        "cat ",
        "grep ",
        "find ",
        "du ",
        "stat ",
        "head ",
        "tail ",
        "wc ",
        "awk ",
        "sed -n ",
        "test ",
        "which ",
        "whereis ",
        "journalctl",
        "dmesg",
        "uptime",
        "top ",
        "ps ",
        "swapon ",
        "sysctl ",
        "systemctl status",
        "systemctl show",
        "systemctl is-",
        "systemctl --failed",
        "dnf check-update",
        "apt list --upgradable",
        "pacman -qu",
        "flatpak list",
        "snap list",
    )
    return normalized.startswith(diagnostic_prefixes)


def _extract_co_robi(text: str) -> str:
    """Extract 'Co robi:' comment from text following a command match."""
    m = re.search(r"\s*\*{0,2}Co robi:\*{0,2}\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _pattern_strict_bold(reply: str) -> List[Tuple[str, str]]:
    """Pattern 1: **Komenda:** `command` (strict: bold + backticks)."""
    fixes: List[Tuple[str, str]] = []
    for m in re.finditer(
        r"\*\*Komenda:\*\*\s*`([^`]+)`(?:[^\n]*?\*\*Co robi:\*\*\s*(.+?))?(?=\n|$)",
        reply,
        re.IGNORECASE,
    ):
        cmd = m.group(1).strip()
        if cmd:
            fixes.append((cmd, (m.group(2) or "").strip()))
    return fixes


def _pattern_backticks(reply: str) -> List[Tuple[str, str]]:
    """Pattern 2: Komenda: `command` (backticks, optional bold)."""
    fixes: List[Tuple[str, str]] = []
    for m in re.finditer(
        r"\*{0,2}Komenda:\*{0,2}\s*`([^`]+)`",
        reply,
        re.IGNORECASE,
    ):
        cmd = m.group(1).strip()
        if cmd:
            fixes.append((cmd, _extract_co_robi(reply[m.end() :])))
    return fixes


def _pattern_no_backticks(reply: str) -> List[Tuple[str, str]]:
    """Pattern 3: Komenda: command (no backticks — until next section)."""
    fixes: List[Tuple[str, str]] = []
    for m in re.finditer(
        r"\*{0,2}Komenda:\*{0,2}\s*"
        r"(.+?)"
        r"(?=\n\s*\*{0,2}Co robi:|\n[🔴🟡🟢]|\n━|\n─|\n\[[\dA-Z]|\Z)",
        reply,
        re.IGNORECASE | re.DOTALL,
    ):
        cmd = re.sub(r"\s*\n\s*", " ", m.group(1)).strip()
        if cmd:
            fixes.append((cmd, _extract_co_robi(reply[m.end() :])))
    return fixes


def _pattern_fallbacks(reply: str) -> List[Tuple[str, str]]:
    """Fallback patterns: → Fix, [N] command, EXEC."""
    fixes: List[Tuple[str, str]] = []
    for m in re.finditer(r"→\s*Fix:\s*`([^`]+)`", reply, re.IGNORECASE):
        fixes.append((m.group(1).strip(), ""))
    if not fixes:
        for m in re.finditer(r"\[(\d+)\][^`\n]+`([^`]+)`", reply):
            fixes.append((m.group(2).strip(), f"Fix #{m.group(1)}"))
    if not fixes:
        for m in re.finditer(r"EXEC:\s*`([^`]+)`", reply, re.IGNORECASE):
            fixes.append((m.group(1).strip(), ""))
    return fixes


def _deduplicate(fixes: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Remove diagnostic-only commands and deduplicate."""
    filtered = [
        (cmd, comment) for cmd, comment in fixes if not _is_diagnostic_only_command(cmd)
    ]
    seen: set[str] = set()
    unique: List[Tuple[str, str]] = []
    for cmd, comment in filtered:
        if cmd not in seen:
            seen.add(cmd)
            unique.append((cmd, comment))
    return unique


def extract_fixes(reply: str) -> List[Tuple[str, str]]:
    """Extract (command, comment) pairs from LLM reply."""
    fixes = (
        _pattern_strict_bold(reply)
        or _pattern_backticks(reply)
        or _pattern_no_backticks(reply)
        or _pattern_fallbacks(reply)
    )
    return _deduplicate(fixes)


def _closed_keys(value: object, expected: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == expected


def _bounded_text(value: object, *, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        return None
    return normalized


def _bounded_text_list(
    value: object,
    *,
    minimum: int,
    maximum: int,
    item_maximum: int,
) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        return None
    items: list[str] = []
    for candidate in value:
        item = _bounded_text(candidate, maximum=item_maximum)
        if item is None or "\n" in item or "\r" in item:
            return None
        items.append(item)
    if len(set(items)) != len(items):
        return None
    return tuple(items)


def _has_command_placeholder(command: str) -> bool:
    """Reject obvious model placeholders instead of offering fake commands."""
    return bool(
        re.search(
            r"(?:\.\.\.|\{\{.+?\}\}|<(?:name|path|pid|service|package|user)>)",
            command,
            re.IGNORECASE,
        )
    )


def _parse_strategy(
    raw: object,
    *,
    finding_ref: str,
    finding_title: str,
    severity: str,
    category: str,
    evidence: tuple[str, ...],
) -> RemediationAction | None:
    expected = {
        "id",
        "label",
        "risk",
        "recommended",
        "commands",
        "verification",
        "explanation",
    }
    if not _closed_keys(raw, expected):
        return None

    action_id = _bounded_text(raw["id"], maximum=81)
    label = _bounded_text(raw["label"], maximum=120)
    explanation = _bounded_text(raw["explanation"], maximum=500)
    risk = raw["risk"]
    recommended = raw["recommended"]
    commands = _bounded_text_list(
        raw["commands"], minimum=1, maximum=5, item_maximum=4000
    )
    verification = _bounded_text_list(
        raw["verification"], minimum=1, maximum=3, item_maximum=1000
    )

    if (
        action_id is None
        or _ACTION_ID_RE.fullmatch(action_id) is None
        or label is None
        or explanation is None
        or risk not in _RISKS
        or not isinstance(recommended, bool)
        or commands is None
        or verification is None
    ):
        return None
    if any(
        _is_diagnostic_only_command(command) or _has_command_placeholder(command)
        for command in commands
    ):
        return None
    if any(
        not _is_diagnostic_only_command(command)
        or _has_command_placeholder(command)
        for command in verification
    ):
        return None

    return RemediationAction(
        finding_ref=finding_ref,
        finding_title=finding_title,
        severity=severity,
        category=category,
        action_id=action_id,
        label=label,
        risk=risk,
        recommended=recommended,
        commands=commands,
        verification=verification,
        explanation=explanation,
        evidence=evidence,
    )


def _parse_remediation_document(raw: object) -> list[RemediationAction] | None:
    if not _closed_keys(raw, {"schema", "mode", "findings"}):
        return None
    if raw["schema"] != REMEDIATION_PLAN_SCHEMA or raw["mode"] != "PLAN":
        return None

    findings = raw["findings"]
    if not isinstance(findings, list) or not 1 <= len(findings) <= 20:
        return None

    actions: list[RemediationAction] = []
    finding_refs: set[str] = set()
    action_ids: set[str] = set()
    finding_keys = {"ref", "severity", "category", "title", "evidence", "strategies"}

    for finding in findings:
        if not _closed_keys(finding, finding_keys):
            return None
        finding_ref = _bounded_text(finding["ref"], maximum=94)
        title = _bounded_text(finding["title"], maximum=160)
        severity = finding["severity"]
        category = finding["category"]
        evidence = _bounded_text_list(
            finding["evidence"], minimum=1, maximum=12, item_maximum=300
        )
        strategies = finding["strategies"]
        if (
            finding_ref is None
            or _FINDING_REF_RE.fullmatch(finding_ref) is None
            or finding_ref in finding_refs
            or title is None
            or severity not in _SEVERITIES
            or category not in _CATEGORIES
            or evidence is None
            or not isinstance(strategies, list)
            or not 1 <= len(strategies) <= 4
        ):
            return None

        parsed_strategies: list[RemediationAction] = []
        for strategy in strategies:
            action = _parse_strategy(
                strategy,
                finding_ref=finding_ref,
                finding_title=title,
                severity=severity,
                category=category,
                evidence=evidence,
            )
            if action is None or action.action_id in action_ids:
                return None
            parsed_strategies.append(action)
            action_ids.add(action.action_id)

        if sum(action.recommended for action in parsed_strategies) != 1:
            return None
        finding_refs.add(finding_ref)
        actions.extend(parsed_strategies)

    return actions


def _legacy_remediation_actions(reply: str) -> list[RemediationAction]:
    actions: list[RemediationAction] = []
    for command, comment in extract_fixes(reply):
        digest = hashlib.sha256(
            f"{comment}\0{command}".encode("utf-8", errors="replace")
        ).hexdigest()[:12]
        explanation = comment or "Legacyjna propozycja naprawy z odpowiedzi modelu."
        actions.append(
            RemediationAction(
                finding_ref=f"finding:fixos:legacy-{digest}",
                finding_title=comment or "Proponowana remediacja",
                severity="ERROR",
                category="RUNTIME",
                action_id=f"legacy-{digest}",
                label=comment or "Wykonaj proponowaną naprawę",
                risk="CAUTION",
                recommended=True,
                commands=(command,),
                verification=(),
                explanation=explanation,
            )
        )
    return actions


def extract_remediation_actions(reply: str) -> list[RemediationAction]:
    """Parse a closed remediation plan, falling back to legacy command syntax."""
    match = _PLAN_BLOCK_RE.search(reply)
    if match:
        try:
            document = json.loads(match.group(1))
        except json.JSONDecodeError:
            document = None
        parsed = _parse_remediation_document(document)
        if parsed is not None:
            return parsed
    return _legacy_remediation_actions(reply)


def strip_remediation_plan(reply: str) -> str:
    """Hide the machine plan block from the human-readable diagnosis."""
    return _ANY_PLAN_BLOCK_RE.sub("", reply).rstrip()


_DIAGNOSTIC_PROBLEM_RE = re.compile(
    r"^problem(?:\s+(?:nr|no)\.?)?\s*(\d+)\s*[:.)-]\s*(.+)$",
    re.IGNORECASE,
)


def extract_diagnostic_choices(reply: str) -> list[DiagnosticChoice]:
    """Extract non-executable choices from numbered diagnosis headings."""
    choices: list[DiagnosticChoice] = []
    seen_numbers: set[int] = set()
    severity = "UNSPECIFIED"

    for raw_line in strip_remediation_plan(reply).splitlines():
        line = raw_line.strip()
        line = re.sub(r"^(?:(?:#{1,6}|[-+*>])\s*)+", "", line)
        line = line.strip(" *_`").strip()
        if not line:
            continue

        match = _DIAGNOSTIC_PROBLEM_RE.match(line)
        if match:
            source_number = int(match.group(1))
            title = match.group(2).strip(" *_`").strip()
            if not title or source_number in seen_numbers:
                continue
            digest = hashlib.sha256(
                f"{source_number}\0{title}".encode("utf-8", errors="replace")
            ).hexdigest()[:10]
            choices.append(
                DiagnosticChoice(
                    finding_ref=(
                        f"diagnosis:fixos:problem-{source_number}-{digest}"
                    ),
                    source_number=source_number,
                    title=title,
                    severity=severity,
                )
            )
            seen_numbers.add(source_number)
            continue

        normalized = line.upper()
        if "🔴" in line or normalized in {"CRITICAL", "KRYTYCZNE"}:
            severity = "CRITICAL"
        elif "🟡" in line or normalized in {"IMPORTANT", "WAŻNE", "WAZNE"}:
            severity = "IMPORTANT"
        elif "🟢" in line or normalized in {"MINOR", "DROBNE"}:
            severity = "MINOR"

    return choices


def transform_remediation_commands(
    action: RemediationAction, transform: Callable[[str], str]
) -> RemediationAction:
    """Apply anonymization reversal to executable fields only."""
    return RemediationAction(
        finding_ref=action.finding_ref,
        finding_title=action.finding_title,
        severity=action.severity,
        category=action.category,
        action_id=action.action_id,
        label=action.label,
        risk=action.risk,
        recommended=action.recommended,
        commands=tuple(transform(command) for command in action.commands),
        verification=tuple(transform(command) for command in action.verification),
        explanation=action.explanation,
        evidence=action.evidence,
    )


def select_recommended_actions(
    actions: list[RemediationAction],
) -> list[RemediationAction]:
    """Return at most one recommended strategy for each finding."""
    selected: list[RemediationAction] = []
    seen: set[str] = set()
    for action in actions:
        if action.recommended and action.finding_ref not in seen:
            selected.append(action)
            seen.add(action.finding_ref)
    return selected


def extract_search_topic(llm_reply: str) -> str:
    """Extract search keywords from LLM reply."""
    tech_terms = re.findall(
        r"\b(sof-firmware|pipewire|alsa|thumbnails?|nautilus|"
        r"dnf|apt|systemctl|journalctl|codec|driver|nvidia|amd|"
        r"snd_hda|intel_sst|avs|wireplumber|pulseaudio|bluetooth|wifi)\b",
        llm_reply,
        re.IGNORECASE,
    )
    if tech_terms:
        return " ".join(dict.fromkeys(tech_terms[:MAX_TECH_TERMS]))
    first_sentence = llm_reply.split(".")[0][:MAX_SUMMARY_LENGTH]
    return first_sentence or "linux system diagnostics"
