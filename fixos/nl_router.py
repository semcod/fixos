"""Shared NL-to-URI Router conforming to wellmanifest/nl-uri-dsl-llm (`wellmanifest.nl-plan/v1`) (#167).

Unifies natural-language intent routing across `fixos ask`, interactive `shell`, and MCP `task_plan`:
- Full Polish/English diacritic normalization (`ą ć ę ł ń ó ś ź ż` -> ASCII stems) while preserving raw Unicode input
- Negation detection (`nie usuwaj`, `bez czyszczenia`, `don't delete`, etc.) blocking mutating selection
- Inquiry/question detection (`czy ...?`, `co usunie ...?`) abstaining to `clarify` without consent
- Standalone `auto` / `automatycznie` never selects or authorizes mutation
- Unknown or empty input abstains (`clarify` / `unsupported`) instead of defaulting to `quick`
- Optional LLM fallback strictly validated as closed `wellmanifest.nl-plan/v1` DSL (`grants_authority=False`)
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fixos.poa_registry import (
    CANONICAL_OPERATIONS,
    OperationSpec,
    catalog_static_digest,
    operations_catalog_projection,
)

NL_PLAN_SCHEMA = "wellmanifest.nl-plan/v1"
NL_PROFILE_ID = "semantic-v1"
ALLOWED_STATUSES = frozenset({"ok", "clarify", "unsupported"})

_PL_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "a",
        "Ć": "c",
        "Ę": "e",
        "Ł": "l",
        "Ń": "n",
        "Ó": "o",
        "Ś": "s",
        "Ź": "z",
        "Ż": "z",
    }
)

_NEGATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bnie\s+(?:usuw\w*|usun\w*|czysc\w*|wyczysc\w*|kasuj\w*|zwalni\w*|wylacz\w*|zatrzym\w*|napraw\w*|zmienia\w*|rusza\w*|dotyka\w*)\b"
    ),
    re.compile(r"\bbez\s+(?:usuwan\w*|czyszczen\w*|kasowan\w*|zmian\w*|napraw\w*)\b"),
    re.compile(
        r"\b(?:do\s+not|dont|don't|never)\s+(?:delete|remove|clean|cleanup|prune|wipe|clear|stop|kill|touch|modify)\b"
    ),
    re.compile(r"\bwithout\s+(?:deleting|removing|cleaning|pruning|modifying|wiping)\b"),
)

_CLEANUP_INQUIRY_RE = re.compile(
    r"(?:^\s*(?:czy|co|ile|jak|kiedy|what|which|how\s+much|would|can\s+i|should\s+i)\b.*\b(?:wyczysc\w*|czysc\w*|usun\w*|usuw\w*|cleanup|clean|prune|zwolni\w*)\b)"
    r"|(?:\b(?:wyczysc\w*|czysc\w*|usun\w*|usuw\w*|cleanup|clean|prune)\b.*\?\s*$)"
)

_STANDALONE_AUTO_RE = re.compile(
    r"^\s*(?:uruchom\s+|wlacz\s+|run\s+|tryb\s+|mode\s+)?(?:auto|automatycznie|automatic|autonomous)\s*[.!?]*\s*$"
)

_MUTATE_CLEANUP_STEMS = (
    "wyczysc",
    "czysc",
    "posprzataj",
    "zwolnij",
    "cleanup",
    "clean",
    "prune",
    "usun",
    "usuw",
    "skasuj",
)

_CLEANUP_TARGET_STEMS = (
    "dysk",
    "disk",
    "miejsc",
    "space",
    "cache",
    "artefakt",
    "artifact",
    "tmp",
    "smiec",
    "star",
    "stale",
    "projekt",
    "project",
    "pakiet",
    "package",
    "kontener",
    "container",
    "docker",
    "system",
)


def normalize_nl_text(text: str) -> str:
    """Normalize PL/EN text to lowercase ASCII tokens without losing word boundaries."""
    translated = (text or "").translate(_PL_TRANSLATION).lower()
    decomposed = unicodedata.normalize("NFKD", translated)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped).strip()


def has_mutation_negation(normalized_text: str) -> bool:
    """Return True when the normalized prompt negates destructive/mutating actions."""
    return any(pat.search(normalized_text) for pat in _NEGATION_PATTERNS)


def _spec_by_uri(uri: str, operations: Sequence[OperationSpec]) -> OperationSpec | None:
    return next((op for op in operations if op.process_uri == uri), None)


def validate_nl_plan_envelope(
    candidate: Mapping[str, Any],
    *,
    operations: Sequence[OperationSpec] = CANONICAL_OPERATIONS,
    registry_digest: str | None = None,
) -> dict[str, Any]:
    """Validate an NL plan envelope (including optional LLM DSL output) fail-closed."""
    if not isinstance(candidate, Mapping):
        raise TypeError("INVALID_NL_PLAN_OBJECT")
    if candidate.get("schema") != NL_PLAN_SCHEMA:
        raise ValueError("INVALID_NL_PLAN_SCHEMA")
    if candidate.get("profile") != NL_PROFILE_ID:
        raise ValueError("INVALID_NL_PLAN_PROFILE")
    if candidate.get("grants_authority") is not False or candidate.get("executable") is not False:
        raise ValueError("NL_PLAN_AUTHORITY_ESCALATION_FORBIDDEN")
    if candidate.get("advisory") is not True:
        raise ValueError("NL_PLAN_MUST_BE_ADVISORY")

    status = candidate.get("status")
    if status not in ALLOWED_STATUSES:
        raise ValueError("INVALID_NL_PLAN_STATUS")

    expected_digest = registry_digest or catalog_static_digest(
        operations_catalog_projection(operations)
    )
    if candidate.get("registry_digest") != expected_digest:
        raise ValueError("NL_PLAN_DIGEST_MISMATCH")

    known_uris = {op.process_uri: op for op in operations}
    op_uri = candidate.get("operation_id")

    if status == "ok":
        if not isinstance(op_uri, str) or op_uri not in known_uris:
            raise ValueError("NL_PLAN_UNKNOWN_URI")
        spec = known_uris[op_uri]
        if candidate.get("effect") not in (spec.legacy_effect, spec.effect):
            raise ValueError("NL_PLAN_EFFECT_MISMATCH")
    else:
        if op_uri is not None:
            raise ValueError("NL_PLAN_ABSTENTION_MUST_NOT_SELECT_URI")
        if not str(candidate.get("reason") or "").strip():
            raise ValueError("NL_PLAN_ABSTENTION_REASON_REQUIRED")

    return dict(candidate)


def _build_envelope(
    *,
    task: str,
    normalized: str,
    status: str,
    registry_digest: str,
    spec: OperationSpec | None = None,
    confidence: float = 0.0,
    reason: str = "",
    candidate_uris: Sequence[str] = (),
    negated: bool = False,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "schema": NL_PLAN_SCHEMA,
        "profile": NL_PROFILE_ID,
        "task": task,
        "normalized_task": normalized,
        "status": status,
        "advisory": True,
        "grants_authority": False,
        "executable": False,
        "negation_detected": negated,
        "operation_id": spec.process_uri if spec else None,
        "operation": spec.process_uri if spec else None,
        "stable_operation_id": spec.operation_id if spec else None,
        "tool_name": (spec.mcp_tool_name or None) if spec else None,
        "effect": spec.legacy_effect if spec else "none",
        "confidence": round(float(confidence), 2),
        "registry_digest": registry_digest,
    }
    if reason:
        envelope["reason"] = reason
    if candidate_uris:
        envelope["candidate_uris"] = list(candidate_uris)
    return envelope


def route_nl_to_uri(
    task: str,
    *,
    operations: Sequence[OperationSpec] = CANONICAL_OPERATIONS,
    registry_digest: str | None = None,
    llm_dsl_resolver: Callable[[str, Sequence[str]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deterministically compile natural-language input into a validated wellmanifest.nl-plan/v1 envelope."""
    raw_task = (task or "").strip()
    norm = normalize_nl_text(raw_task)
    digest = registry_digest or catalog_static_digest(operations_catalog_projection(operations))

    if not norm:
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="clarify",
                registry_digest=digest,
                reason="empty_intent",
            ),
            operations=operations,
            registry_digest=digest,
        )

    negated = has_mutation_negation(norm)

    if _STANDALONE_AUTO_RE.fullmatch(norm):
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="clarify",
                registry_digest=digest,
                reason="standalone_auto_does_not_authorize_mutation",
                candidate_uris=("fixos://diagnostics/quick", "fixos://diagnostics/disk"),
                negated=negated,
            ),
            operations=operations,
            registry_digest=digest,
        )

    if _CLEANUP_INQUIRY_RE.search(norm):
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="clarify",
                registry_digest=digest,
                reason="cleanup_inquiry_requires_explicit_confirmation",
                candidate_uris=("fixos://diagnostics/disk", "fixos://cleanup/auto"),
                negated=negated,
            ),
            operations=operations,
            registry_digest=digest,
        )

    raw_tokens = re.findall(r"[a-z0-9_./-]+", norm)
    tokens = {t.strip("./") for t in raw_tokens if t.strip("./")} | set(raw_tokens)

    def has_any(stems: Sequence[str]) -> bool:
        return any(
            stem in tokens or any(tok.startswith(stem) for tok in tokens)
            for stem in stems
        )

    wants_cleanup_verb = has_any(_MUTATE_CLEANUP_STEMS)
    has_cleanup_target = has_any(_CLEANUP_TARGET_STEMS)

    if negated and wants_cleanup_verb:
        has_read_verb = has_any(
            ("sprawdz", "pokaz", "zbadaj", "skanuj", "check", "show", "scan", "inspect")
        )
        if has_read_verb and has_any(("projekt", "project", "venv", "node_modules")):
            spec = _spec_by_uri("fixos://diagnostics/projects", operations)
            if spec is not None:
                return validate_nl_plan_envelope(
                    _build_envelope(
                        task=raw_task,
                        normalized=norm,
                        status="ok",
                        registry_digest=digest,
                        spec=spec,
                        confidence=0.86,
                        negated=True,
                    ),
                    operations=operations,
                    registry_digest=digest,
                )
        if has_read_verb and has_any(("dysk", "disk", "miejsc", "space", "cache", "rozmiar")):
            spec = _spec_by_uri("fixos://diagnostics/disk", operations)
            if spec is not None:
                return validate_nl_plan_envelope(
                    _build_envelope(
                        task=raw_task,
                        normalized=norm,
                        status="ok",
                        registry_digest=digest,
                        spec=spec,
                        confidence=0.86,
                        negated=True,
                    ),
                    operations=operations,
                    registry_digest=digest,
                )
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="clarify",
                registry_digest=digest,
                reason="negated_mutation_intent",
                candidate_uris=("fixos://diagnostics/disk", "fixos://diagnostics/projects"),
                negated=True,
            ),
            operations=operations,
            registry_digest=digest,
        )

    if negated:
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="clarify",
                registry_digest=digest,
                reason="negated_intent_requires_clarification",
                negated=True,
            ),
            operations=operations,
            registry_digest=digest,
        )

    matched_uris: list[tuple[str, float]] = []

    if wants_cleanup_verb and has_cleanup_target:
        matched_uris.append(("fixos://cleanup/auto", 0.92))
    elif wants_cleanup_verb and not has_cleanup_target:
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="clarify",
                registry_digest=digest,
                reason="cleanup_missing_explicit_target",
                candidate_uris=("fixos://diagnostics/disk", "fixos://cleanup/auto"),
            ),
            operations=operations,
            registry_digest=digest,
        )

    if not wants_cleanup_verb:
        if has_any(("projekt", "project", "venv", "node_modules", "tygodn", "7d", "partycj")):
            matched_uris.append(("fixos://diagnostics/projects", 0.90))
        if has_any(("dysk", "disk", "miejsc", "space", "cache", "rozmiar")):
            matched_uris.append(("fixos://diagnostics/disk", 0.88))
        if has_any(("drukark", "printer", "cups", "spooler", "ipp")):
            matched_uris.append(("fixos://diagnostics/printers", 0.90))
        if has_any(("mesh", "tailscale", "osiagalnosc", "reachability", "podsiec", "vlan")):
            matched_uris.append(("fixos://diagnostics/mesh", 0.90))
        if has_any(("anomali", "zombie", "restart_loop", "petl")):
            matched_uris.append(("fixos://diagnostics/anomalies", 0.89))
        if has_any(("duze", "large", "storage", "triage")):
            matched_uris.append(("fixos://diagnostics/storage", 0.87))
        if has_any(("audio", "dzwiek", "sound", "glosnik", "mikrofon", "pipewire", "alsa")):
            matched_uris.append(("fixos://plugins/audio", 0.89))
        if has_any(("bezpieczenstw", "security", "firewall", "selinux", "ssh")):
            matched_uris.append(("fixos://plugins/security", 0.89))
        if has_any(("jetbrains", "pycharm", "intellij", "clion", "goland", "webstorm")):
            matched_uris.append(("fixos://jetbrains/doctor", 0.89))
        if has_any(("szybk", "quick", "snapshot", "stan", "cpu", "ram", "telemetri")):
            matched_uris.append(("fixos://diagnostics/quick", 0.85))

    deduped: list[tuple[str, float]] = []
    seen: set[str] = set()
    for uri, score in matched_uris:
        if uri not in seen and _spec_by_uri(uri, operations) is not None:
            seen.add(uri)
            deduped.append((uri, score))

    distinct_domains = {
        uri for uri, _ in deduped if uri not in ("fixos://diagnostics/quick",)
    }
    if len(distinct_domains) > 1 and not (
        distinct_domains <= {"fixos://diagnostics/disk", "fixos://diagnostics/projects"}
        and "projekt" in norm
    ):
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="clarify",
                registry_digest=digest,
                reason="ambiguous_multiple_targets",
                candidate_uris=[u for u, _ in deduped],
            ),
            operations=operations,
            registry_digest=digest,
        )

    if len(deduped) >= 1:
        chosen_uri, chosen_conf = deduped[0]
        spec = _spec_by_uri(chosen_uri, operations)
        assert spec is not None
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status="ok",
                registry_digest=digest,
                spec=spec,
                confidence=chosen_conf,
            ),
            operations=operations,
            registry_digest=digest,
        )

    if llm_dsl_resolver is not None:
        allowed_uris = [op.process_uri for op in operations]
        llm_raw = llm_dsl_resolver(raw_task, allowed_uris)
        if not isinstance(llm_raw, Mapping):
            raise TypeError("INVALID_LLM_DSL_RESPONSE")
        if bool(llm_raw.get("grants_authority", False)) or bool(llm_raw.get("executable", False)):
            raise ValueError("LLM_DSL_AUTHORITY_FORBIDDEN")
        llm_status = str(llm_raw.get("status") or "unsupported")
        if llm_status == "ok":
            llm_uri = str(llm_raw.get("operation_id") or "")
            spec = _spec_by_uri(llm_uri, operations)
            if spec is None:
                raise ValueError("LLM_DSL_UNKNOWN_URI")
            return validate_nl_plan_envelope(
                _build_envelope(
                    task=raw_task,
                    normalized=norm,
                    status="ok",
                    registry_digest=digest,
                    spec=spec,
                    confidence=min(0.89, max(0.5, float(llm_raw.get("confidence", 0.75)))),
                ),
                operations=operations,
                registry_digest=digest,
            )
        return validate_nl_plan_envelope(
            _build_envelope(
                task=raw_task,
                normalized=norm,
                status=llm_status if llm_status in ("clarify", "unsupported") else "unsupported",
                registry_digest=digest,
                reason=str(llm_raw.get("reason") or "llm_abstained"),
            ),
            operations=operations,
            registry_digest=digest,
        )

    return validate_nl_plan_envelope(
        _build_envelope(
            task=raw_task,
            normalized=norm,
            status="unsupported",
            registry_digest=digest,
            reason="unknown_intent",
        ),
        operations=operations,
        registry_digest=digest,
    )
