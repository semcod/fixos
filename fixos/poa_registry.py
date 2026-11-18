"""Canonical POA/MCP Registry of FixOS Commands, URI Processes, and URN Resources.

Single source of truth (SSOT) for FixOS operational capabilities per:
- wellmanifest/mcp (`wellmanifest.mcp/registry/v1`)
- wellmanifest/poa (deterministic capability/URI/URN separation)

CLI commands, diagnostic plugins, and MCP tools are projections of this catalog.
Every public Click command/subcommand and builtin plugin must either map to a
canonical operation entry or carry an explicit non-exposure justification.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import click

from fixos import __version__

MCP_REGISTRY_SCHEMA = "wellmanifest.mcp/registry/v1"
OWNER_REPOSITORY = "semcod/fixos"
DEFAULT_REGISTRY_TTL_SECONDS = 86400

_OP_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_PROCESS_URI_RE = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s?#]+$")
_RESOURCE_URN_RE = re.compile(
    r"^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_RESOURCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")  # NAMESPACE_URL
_ALLOWED_CANONICAL_EFFECTS = frozenset({"read", "pure", "mutating"})

_EMPTY_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

_GENERIC_RESULT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["operation_id", "effect"],
    "properties": {
        "operation_id": {"type": "string", "minLength": 1},
        "effect": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}


def resource_type_urn(operation_id: str) -> str:
    """Derive a deterministic RFC 4122 UUIDv5 URN for an operation's output resource type."""
    derived = uuid.uuid5(
        _RESOURCE_NAMESPACE,
        f"https://wellmanifest.org/semcod/fixos/resource-type/{operation_id}",
    )
    return f"urn:uuid:{derived}"


def deployment_revision() -> str:
    """Return non-empty package deployment revision identifier."""
    return f"fixos-{__version__}"


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc_iso(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("INVALID_EXPIRY_TIMESTAMP")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("EXPIRY_TIMESTAMP_MISSING_TZ")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class OperationSpec:
    """Canonical operation contract separating operation ID, process URI, and resource URN."""

    operation_id: str
    process_uri: str
    resource_type: str
    title: str
    description: str
    effect: str  # "read" | "pure" | "mutating"
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    owner: str = OWNER_REPOSITORY
    mcp_tool_name: str = ""
    mcp_exposed: bool = False
    mcp_gateway_builtin: bool = False
    available: bool = True
    availability_reason: str = "Active in current FixOS deployment"
    capability_refs: tuple[str, ...] = ()
    destructive_hint: bool = False
    idempotent_hint: bool = True

    @property
    def resource_urn(self) -> str:
        return resource_type_urn(self.operation_id)

    @property
    def legacy_effect(self) -> str:
        if self.effect == "mutating":
            return "mutate"
        if self.effect == "pure":
            return "read"
        return self.effect

    @property
    def annotations(self) -> dict[str, bool]:
        return {
            "readOnlyHint": self.effect in ("read", "pure"),
            "destructiveHint": self.destructive_hint,
            "idempotentHint": self.idempotent_hint,
        }


@dataclass(frozen=True)
class NonExposedCapability:
    """Explicit justification for a public CLI command/subcommand not exposed as a URI operation."""

    capability_ref: str
    kind: str  # "interactive_tty" | "secret_hygiene" | "hitl_mutation" | "transport_entrypoint" | "command_group"
    reason: str
    owner: str = OWNER_REPOSITORY


def _cli_only_op(
    operation_id: str,
    process_uri: str,
    resource_type: str,
    title: str,
    description: str,
    capability_refs: tuple[str, ...],
) -> OperationSpec:
    return OperationSpec(
        operation_id=operation_id,
        process_uri=process_uri,
        resource_type=resource_type,
        title=title,
        description=description,
        effect="read",
        input_schema=_EMPTY_OBJECT_SCHEMA,
        output_schema=_GENERIC_RESULT_OUTPUT_SCHEMA,
        mcp_exposed=False,
        available=False,
        availability_reason="CLI/plugin read capability registered; unattended MCP adapter not enrolled in minimal profile",
        capability_refs=capability_refs,
    )


CANONICAL_OPERATIONS: tuple[OperationSpec, ...] = (
    # --- Enrolled MCP domain operations (indices 0..3 for consumer compatibility) ---
    OperationSpec(
        operation_id="diagnostics_quick",
        process_uri="fixos://diagnostics/quick",
        resource_type="fixos.snapshot.quick",
        title="Quick deterministic system & storage snapshot",
        description="Collect fast local CPU, RAM, disk, safe cache, and top process telemetry without LLM calls.",
        effect="read",
        mcp_tool_name="fixos_quick",
        mcp_exposed=True,
        capability_refs=("cli:quick",),
        input_schema=_EMPTY_OBJECT_SCHEMA,
        output_schema={
            "type": "object",
            "required": ["operation_id", "effect", "snapshot"],
            "properties": {
                "operation_id": {"const": "fixos://diagnostics/quick"},
                "effect": {"const": "read"},
                "snapshot": {"type": "object"},
            },
            "additionalProperties": False,
        },
    ),
    OperationSpec(
        operation_id="diagnostics_disk",
        process_uri="fixos://diagnostics/disk",
        resource_type="fixos.inventory.disk",
        title="Disk usage & safe cache inventory",
        description="Analyze root filesystem free space, safe user caches, and JetBrains/build cache candidates.",
        effect="read",
        mcp_tool_name="fixos_scan_disk",
        mcp_exposed=True,
        capability_refs=("plugin:disk",),
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "default": "/"},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["operation_id", "effect", "path", "disk", "reclaimable_summary", "candidates"],
            "properties": {
                "operation_id": {"const": "fixos://diagnostics/disk"},
                "effect": {"const": "read"},
                "path": {"type": "string", "minLength": 1},
                "disk": {"type": "object"},
                "reclaimable_summary": {"type": "object"},
                "candidates": {"type": "object"},
            },
            "additionalProperties": False,
        },
    ),
    OperationSpec(
        operation_id="diagnostics_projects",
        process_uri="fixos://diagnostics/projects",
        resource_type="fixos.inventory.projects",
        title="Scan stale developer project artifacts & state partitions",
        description="Discover unused developer build/venv artifacts and date-partitioned app state older than min_age_days.",
        effect="read",
        mcp_tool_name="fixos_scan_projects",
        mcp_exposed=True,
        capability_refs=("cli:projects",),
        input_schema={
            "type": "object",
            "properties": {
                "min_age_days": {"type": "number", "minimum": 1, "default": 7.0},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": [
                "operation_id",
                "effect",
                "min_age_days",
                "project_artifacts_count",
                "state_partitions_count",
                "total_reclaimable_bytes",
            ],
            "properties": {
                "operation_id": {"const": "fixos://diagnostics/projects"},
                "effect": {"const": "read"},
                "min_age_days": {"type": "number"},
                "project_artifacts_count": {"type": "integer", "minimum": 0},
                "state_partitions_count": {"type": "integer", "minimum": 0},
                "total_reclaimable_bytes": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": True,
        },
    ),
    OperationSpec(
        operation_id="cleanup_auto",
        process_uri="fixos://cleanup/auto",
        resource_type="fixos.receipt.cleanup",
        title="Deterministic safe disk cleanup",
        description="Reclaim disk space from safe caches, stale (>7d) unused project artifacts, and date-partitioned state.",
        effect="mutating",
        mcp_tool_name="fixos_auto_cleanup",
        mcp_exposed=True,
        capability_refs=("internal:cleanup_auto",),
        input_schema={
            "type": "object",
            "properties": {
                "dry_run": {"type": "boolean", "default": True},
                "min_age_days": {"type": "number", "minimum": 1, "default": 7.0},
                "include_projects": {"type": "boolean", "default": True},
                "request_id": {
                    "type": "string",
                    "default": "",
                    "maxLength": 128,
                    "description": "Opaque ID starting with a letter/digit, using letters, digits, dots, underscores or hyphens; no '..'. Empty generates an ID.",
                },
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["schema", "request_id", "operation_id", "state", "registry_digest", "receipt_hash"],
            "properties": {
                "schema": {"type": "string", "minLength": 1},
                "request_id": {"type": "string", "minLength": 1},
                "operation_id": {"const": "fixos://cleanup/auto"},
                "state": {"type": "string", "minLength": 1},
                "registry_digest": {"type": "string", "minLength": 64, "maxLength": 64},
                "receipt_hash": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "additionalProperties": True,
        },
    ),
    # --- MCP gateway control operations (wellmanifest/mcp) ---
    OperationSpec(
        operation_id="mcp_registry_search",
        process_uri="fixos://mcp/registry-search",
        resource_type="fixos.mcp.registry-view",
        title="Search canonical FixOS MCP/POA operations",
        description="Query registered FixOS URI operations, schemas, availability, and catalog digest.",
        effect="pure",
        mcp_tool_name="registry_search",
        mcp_exposed=True,
        mcp_gateway_builtin=True,
        capability_refs=("internal:registry_search",),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "default": ""},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 50},
            },
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["schema", "registry_digest", "count", "operations"],
            "properties": {
                "schema": {"const": MCP_REGISTRY_SCHEMA},
                "registry_digest": {"type": "string", "minLength": 64, "maxLength": 64},
                "count": {"type": "integer", "minimum": 0},
                "operations": {"type": "array"},
            },
            "additionalProperties": True,
        },
    ),
    OperationSpec(
        operation_id="mcp_task_plan",
        process_uri="fixos://mcp/task-plan",
        resource_type="fixos.poa.task-plan",
        title="Compile natural-language request into advisory URI plan",
        description="Deterministically map natural language intent to a canonical FixOS URI without granting authority or executing effects.",
        effect="pure",
        mcp_tool_name="task_plan",
        mcp_exposed=True,
        mcp_gateway_builtin=True,
        capability_refs=("internal:task_plan",),
        input_schema={
            "type": "object",
            "properties": {"task": {"type": "string"}},
            "required": ["task"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["schema", "advisory", "grants_authority", "executable", "registry_digest"],
            "properties": {
                "schema": {"type": "string", "minLength": 1},
                "advisory": {"const": True},
                "grants_authority": {"const": False},
                "executable": {"const": False},
                "registry_digest": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "additionalProperties": True,
        },
    ),
    OperationSpec(
        operation_id="mcp_task_execute",
        process_uri="fixos://mcp/task-execute",
        resource_type="fixos.mcp.execution-envelope",
        title="Execute registered FixOS URI operation",
        description="Dispatch an enrolled FixOS URI operation by ID or URI with schema, digest, and receipt bindings.",
        effect="mutating",
        mcp_tool_name="task_execute",
        mcp_exposed=True,
        mcp_gateway_builtin=True,
        capability_refs=("internal:task_execute",),
        input_schema={
            "type": "object",
            "properties": {
                "operation_id": {"type": "string", "minLength": 1},
                "payload": {"type": "object"},
                "registry_digest": {"type": "string", "default": ""},
                "request_id": {"type": "string", "default": ""},
            },
            "required": ["operation_id"],
            "additionalProperties": False,
        },
        output_schema=_GENERIC_RESULT_OUTPUT_SCHEMA,
    ),
    OperationSpec(
        operation_id="mcp_task_status",
        process_uri="fixos://mcp/task-status",
        resource_type="fixos.mcp.task-receipt",
        title="Read durable execution receipt without repeating effects",
        description="Read back a stored cleanup execution receipt by request_id without re-running host mutations.",
        effect="read",
        mcp_tool_name="fixos_task_status",
        mcp_exposed=True,
        mcp_gateway_builtin=True,
        capability_refs=("internal:task_status",),
        input_schema={
            "type": "object",
            "properties": {"request_id": {"type": "string"}},
            "required": ["request_id"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "required": ["schema", "found", "request_id"],
            "properties": {
                "schema": {"type": "string", "minLength": 1},
                "found": {"type": "boolean"},
                "request_id": {"type": "string"},
            },
            "additionalProperties": True,
        },
    ),
    # --- CLI & diagnostic plugin read capabilities ---
    _cli_only_op(
        "diagnostics_anomalies",
        "fixos://diagnostics/anomalies",
        "fixos.report.anomalies",
        "Host anomaly scan outside cache directories",
        "Detect service restart loops, oversized container logs, stale state directories, and zombie processes.",
        ("cli:anomalies",),
    ),
    _cli_only_op(
        "diagnostics_printers",
        "fixos://diagnostics/printers",
        "fixos.report.printers",
        "Network & local printer diagnostics",
        "Inspect CUPS/Windows Spooler queues, IPP attributes, hostname resolution, and multi-vantage reachability.",
        ("cli:printers", "plugin:printers"),
    ),
    _cli_only_op(
        "diagnostics_mesh",
        "fixos://diagnostics/mesh",
        "fixos.report.mesh",
        "Multi-vantage LAN/Tailscale/SSH reachability probe",
        "Verify target host reachability across local interfaces and discovered LAN/Tailscale/SSH peers.",
        ("cli:mesh", "plugin:mesh"),
    ),
    _cli_only_op(
        "diagnostics_storage",
        "fixos://diagnostics/storage",
        "fixos.report.storage-triage",
        "Large file & directory storage triage",
        "Inventory large files and directories with deterministic classification without LLM calls.",
        ("cli:storage",),
    ),
    _cli_only_op(
        "diagnostics_scan",
        "fixos://diagnostics/scan",
        "fixos.report.system-scan",
        "Deterministic multi-module OS scan",
        "Run selected diagnostic plugins without AI mutations.",
        ("cli:scan",),
    ),
    _cli_only_op(
        "diagnostics_report",
        "fixos://diagnostics/report",
        "fixos.report.export",
        "Diagnostic report export",
        "Render diagnostic findings to Markdown, HTML, or JSON.",
        ("cli:report",),
    ),
    _cli_only_op(
        "diagnostics_history",
        "fixos://diagnostics/history",
        "fixos.report.history",
        "Repair session history",
        "List recorded diagnostic and repair sessions.",
        ("cli:history",),
    ),
    _cli_only_op(
        "jetbrains_doctor",
        "fixos://jetbrains/doctor",
        "fixos.report.jetbrains-doctor",
        "JetBrains IDE health check",
        "Inspect JVM heap, EDT freezes, and IDE logs without closing open IDE windows.",
        ("cli:jetbrains doctor",),
    ),
    _cli_only_op(
        "config_show",
        "fixos://config/show",
        "fixos.config.redacted-view",
        "Show redacted FixOS configuration",
        "Display active provider and model configuration without exposing raw secrets.",
        ("cli:config show",),
    ),
    _cli_only_op(
        "features_audit",
        "fixos://features/audit",
        "fixos.report.features-audit",
        "Audit optional OS tools and dependencies",
        "Inspect optional diagnostic helper binaries available on the host.",
        ("cli:features audit",),
    ),
    _cli_only_op(
        "features_profiles",
        "fixos://features/profiles",
        "fixos.report.feature-profiles",
        "List feature installation profiles",
        "List supported optional dependency profiles.",
        ("cli:features profiles",),
    ),
    _cli_only_op(
        "features_system",
        "fixos://features/system",
        "fixos.report.features-system",
        "Inspect host package manager capabilities",
        "Report detected OS distribution and package manager capabilities.",
        ("cli:features system",),
    ),
    _cli_only_op(
        "profile_list",
        "fixos://profile/list",
        "fixos.profile.list",
        "List diagnostic profiles",
        "List available server, desktop, and developer diagnostic profiles.",
        ("cli:profile list",),
    ),
    _cli_only_op(
        "profile_show",
        "fixos://profile/show",
        "fixos.profile.detail",
        "Show diagnostic profile definition",
        "Inspect settings and thresholds of a diagnostic profile.",
        ("cli:profile show",),
    ),
    _cli_only_op(
        "rollback_list",
        "fixos://rollback/list",
        "fixos.rollback.list",
        "List recorded rollback checkpoints",
        "List reversible operations recorded in local rollback history.",
        ("cli:rollback list",),
    ),
    _cli_only_op(
        "rollback_show",
        "fixos://rollback/show",
        "fixos.rollback.detail",
        "Show rollback checkpoint details",
        "Inspect commands and metadata for a specific rollback entry.",
        ("cli:rollback show",),
    ),
    _cli_only_op(
        "providers_list",
        "fixos://providers/list",
        "fixos.providers.catalog",
        "List supported LLM providers",
        "List configured and supported LLM provider backends.",
        ("cli:providers",),
    ),
    _cli_only_op(
        "providers_llm",
        "fixos://providers/llm",
        "fixos.providers.quickstart",
        "LLM provider setup catalog",
        "Display supported LLM providers and setup metadata.",
        ("cli:llm",),
    ),
    _cli_only_op(
        "providers_test_llm",
        "fixos://providers/test-llm",
        "fixos.providers.connectivity",
        "Verify configured LLM provider connectivity",
        "Perform a bounded connectivity probe against the configured LLM provider.",
        ("cli:test-llm",),
    ),
    _cli_only_op(
        "plugin_audio",
        "fixos://plugins/audio",
        "fixos.plugin.audio",
        "Audio subsystem diagnostic plugin",
        "Inspect ALSA, PipeWire, PulseAudio, and SOF firmware state.",
        ("plugin:audio",),
    ),
    _cli_only_op(
        "plugin_hardware",
        "fixos://plugins/hardware",
        "fixos.plugin.hardware",
        "Hardware subsystem diagnostic plugin",
        "Inspect DMI, GPU, input devices, camera, and battery telemetry.",
        ("plugin:hardware",),
    ),
    _cli_only_op(
        "plugin_resources",
        "fixos://plugins/resources",
        "fixos.plugin.resources",
        "System resources diagnostic plugin",
        "Inspect CPU, RAM, top processes, and autostart units.",
        ("plugin:resources",),
    ),
    _cli_only_op(
        "plugin_security",
        "fixos://plugins/security",
        "fixos.plugin.security",
        "Security posture diagnostic plugin",
        "Inspect firewall, listening ports, SELinux/AppArmor, and SSH posture.",
        ("plugin:security",),
    ),
    _cli_only_op(
        "plugin_thumbnails",
        "fixos://plugins/thumbnails",
        "fixos.plugin.thumbnails",
        "Desktop thumbnailer diagnostic plugin",
        "Inspect desktop thumbnail cache, GStreamer plugins, and thumbnailer entries.",
        ("plugin:thumbnails",),
    ),
)


NON_EXPOSED_CAPABILITIES: tuple[NonExposedCapability, ...] = (
    NonExposedCapability(
        "cli:ask",
        "hitl_mutation",
        "Natural-language shell execution wrapper; MCP uses non-executing fixos://mcp/task-plan instead.",
    ),
    NonExposedCapability(
        "cli:auto",
        "hitl_mutation",
        "Interactive multi-stage repair CLI; unattended MCP uses bounded receipt-backed fixos://cleanup/auto.",
    ),
    NonExposedCapability(
        "cli:cleanup",
        "hitl_mutation",
        "Interactive multi-flag service cleanup command; MCP exposes bounded fixos://cleanup/auto instead.",
    ),
    NonExposedCapability(
        "cli:config",
        "command_group",
        "Click command group container; safe read subcommands are registered individually.",
    ),
    NonExposedCapability(
        "cli:config init",
        "interactive_tty",
        "Interactive configuration wizard requiring terminal input.",
    ),
    NonExposedCapability(
        "cli:config model",
        "hitl_mutation",
        "Mutates local user LLM model configuration; excluded from unattended MCP surface.",
    ),
    NonExposedCapability(
        "cli:config provider",
        "hitl_mutation",
        "Mutates local user LLM provider selection; excluded from unattended MCP surface.",
    ),
    NonExposedCapability(
        "cli:config set",
        "secret_hygiene",
        "Writes user configuration keys and potential credentials; excluded per secret-hygiene policy.",
    ),
    NonExposedCapability(
        "cli:dashboard",
        "interactive_tty",
        "Full-screen interactive terminal TUI requiring a live TTY.",
    ),
    NonExposedCapability(
        "cli:features",
        "command_group",
        "Click command group container; read-only audit subcommands are registered individually.",
    ),
    NonExposedCapability(
        "cli:features install",
        "hitl_mutation",
        "Installs system packages requiring privilege escalation and interactive operator consent.",
    ),
    NonExposedCapability(
        "cli:fix",
        "hitl_mutation",
        "Interactive AI-assisted human-in-the-loop repair session requiring live terminal approval.",
    ),
    NonExposedCapability(
        "cli:help",
        "interactive_tty",
        "CLI help text formatter; MCP clients discover schemas via registry_search and tools/list.",
    ),
    NonExposedCapability(
        "cli:jetbrains",
        "command_group",
        "Click command group container; jetbrains doctor is registered individually.",
    ),
    NonExposedCapability(
        "cli:jetbrains ai",
        "hitl_mutation",
        "Mutates local JetBrains IDE assistant configuration; excluded from unattended MCP surface.",
    ),
    NonExposedCapability(
        "cli:mcp",
        "transport_entrypoint",
        "Launches the stdio JSON-RPC MCP server transport itself rather than an invokable domain operation.",
    ),
    NonExposedCapability(
        "cli:orchestrate",
        "hitl_mutation",
        "Interactive multi-step repair graph executor requiring operator confirmation.",
    ),
    NonExposedCapability(
        "cli:profile",
        "command_group",
        "Click command group container; profile list and profile show are registered individually.",
    ),
    NonExposedCapability(
        "cli:quickfix",
        "hitl_mutation",
        "Executes host-level offline repairs requiring interactive confirmation.",
    ),
    NonExposedCapability(
        "cli:rollback",
        "command_group",
        "Click command group container; rollback list and rollback show are registered individually.",
    ),
    NonExposedCapability(
        "cli:rollback undo",
        "hitl_mutation",
        "Reverts system changes on the host; requires interactive human confirmation.",
    ),
    NonExposedCapability(
        "cli:shell",
        "interactive_tty",
        "Interactive prompt_toolkit REPL loop requiring a live TTY.",
    ),
    NonExposedCapability(
        "cli:token",
        "secret_hygiene",
        "Click command group managing API credentials; excluded per secret-hygiene policy.",
    ),
    NonExposedCapability(
        "cli:token clear",
        "secret_hygiene",
        "Mutates stored API token state; excluded from MCP surface per secret-hygiene policy.",
    ),
    NonExposedCapability(
        "cli:token set",
        "secret_hygiene",
        "Accepts raw secret API keys; never exposed over MCP transport.",
    ),
    NonExposedCapability(
        "cli:token show",
        "secret_hygiene",
        "Inspects credential storage state; excluded from MCP surface per secret-hygiene policy.",
    ),
    NonExposedCapability(
        "cli:watch",
        "interactive_tty",
        "Long-running background monitoring daemon loop, not a bounded request/response operation.",
    ),
)


def canonical_json_digest(payload: Any) -> str:
    """Compute deterministic SHA-256 hex digest over canonical UTF-8 JSON."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def validate_registry_entries(
    operations: Sequence[OperationSpec] = CANONICAL_OPERATIONS,
    *,
    expires_at: str | None = None,
    now: datetime | None = None,
) -> None:
    """Validate identifier separation, uniqueness, schemas, availability reasons, and freshness."""
    if not (1 <= len(operations) <= 128):
        raise ValueError("INVALID_REGISTRY_SIZE")

    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if expires_at is not None:
        exp_dt = _parse_utc_iso(expires_at)
        if exp_dt <= ref_now:
            raise ValueError("REGISTRY_EXPIRED")

    seen_ids: set[str] = set()
    seen_uris: set[str] = set()
    seen_urns: set[str] = set()
    seen_tools: set[str] = set()

    for spec in operations:
        if not _OP_ID_RE.fullmatch(spec.operation_id):
            raise ValueError(f"INVALID_OPERATION_ID: {spec.operation_id}")
        if not _PROCESS_URI_RE.fullmatch(spec.process_uri):
            raise ValueError(f"INVALID_PROCESS_URI: {spec.process_uri}")
        urn = spec.resource_urn
        if not _RESOURCE_URN_RE.fullmatch(urn):
            raise ValueError(f"INVALID_RESOURCE_URN: {urn}")
        if len({spec.operation_id, spec.process_uri, urn}) != 3:
            raise ValueError(f"IDENTIFIER_CONFLATION: {spec.operation_id}")
        if spec.operation_id in seen_ids:
            raise ValueError(f"DUPLICATE_OPERATION_ID: {spec.operation_id}")
        if spec.process_uri in seen_uris:
            raise ValueError(f"DUPLICATE_PROCESS_URI: {spec.process_uri}")
        if urn in seen_urns:
            raise ValueError(f"DUPLICATE_RESOURCE_URN: {urn}")
        seen_ids.add(spec.operation_id)
        seen_uris.add(spec.process_uri)
        seen_urns.add(urn)

        if spec.mcp_tool_name:
            if spec.mcp_tool_name in seen_tools:
                raise ValueError(f"DUPLICATE_MCP_TOOL_NAME: {spec.mcp_tool_name}")
            seen_tools.add(spec.mcp_tool_name)
        if spec.mcp_exposed and not spec.mcp_tool_name:
            raise ValueError(f"MISSING_MCP_TOOL_NAME: {spec.operation_id}")

        if not spec.owner.strip():
            raise ValueError(f"MISSING_OWNER: {spec.operation_id}")
        if spec.effect not in _ALLOWED_CANONICAL_EFFECTS:
            raise ValueError(f"INVALID_EFFECT: {spec.operation_id}")
        if type(spec.available) is not bool:
            raise TypeError(f"INVALID_AVAILABILITY_FLAG: {spec.operation_id}")
        if not spec.availability_reason.strip():
            raise ValueError(f"MISSING_AVAILABILITY_REASON: {spec.operation_id}")
        if (
            not isinstance(spec.input_schema, Mapping)
            or spec.input_schema.get("type") != "object"
            or not isinstance(spec.output_schema, Mapping)
            or spec.output_schema.get("type") != "object"
        ):
            raise ValueError(f"INVALID_OPERATION_SCHEMA: {spec.operation_id}")


def export_mcp_registry_v1(
    operations: Sequence[OperationSpec] = CANONICAL_OPERATIONS,
    *,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_REGISTRY_TTL_SECONDS,
) -> dict[str, Any]:
    """Export strict wellmanifest.mcp/registry/v1 document (additionalProperties: false compliant)."""
    if ttl_seconds <= 0:
        raise ValueError("REGISTRY_EXPIRED")
    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires_at = _utc_iso(ref_now + timedelta(seconds=int(ttl_seconds)))
    validate_registry_entries(operations, expires_at=expires_at, now=ref_now)
    rev = deployment_revision()

    serialized_ops: list[dict[str, Any]] = []
    for spec in operations:
        item: dict[str, Any] = {
            "id": spec.operation_id,
            "uri": spec.process_uri,
            "description": spec.description,
            "owner": spec.owner,
            "effect": spec.effect,
            "available": spec.available,
            "deploymentRevision": rev,
            "inputSchema": json.loads(json.dumps(dict(spec.input_schema))),
            "outputSchema": json.loads(json.dumps(dict(spec.output_schema))),
        }
        if not spec.available:
            item["unavailableReason"] = spec.availability_reason
        serialized_ops.append(item)

    return {
        "schema": MCP_REGISTRY_SCHEMA,
        "revision": rev,
        "expiresAt": expires_at,
        "operations": serialized_ops,
    }


def operations_catalog_projection(
    operations: Sequence[OperationSpec] = CANONICAL_OPERATIONS,
    *,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_REGISTRY_TTL_SECONDS,
) -> tuple[dict[str, Any], ...]:
    """Project all canonical operations with full POA/MCP metadata and consumer aliases."""
    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    expires_at = _utc_iso(ref_now + timedelta(seconds=max(1, int(ttl_seconds))))
    validate_registry_entries(operations, expires_at=expires_at, now=ref_now)
    rev = deployment_revision()

    projected: list[dict[str, Any]] = []
    for spec in operations:
        entry: dict[str, Any] = {
            "id": spec.operation_id,
            "uri": spec.process_uri,
            "operation_id": spec.process_uri,
            "stable_operation_id": spec.operation_id,
            "process_uri": spec.process_uri,
            "resource_urn": spec.resource_urn,
            "resource_type": spec.resource_type,
            "tool_name": spec.mcp_tool_name,
            "mcp_exposed": spec.mcp_exposed,
            "mcp_gateway_builtin": spec.mcp_gateway_builtin,
            "title": spec.title,
            "description": spec.description,
            "owner": spec.owner,
            "effect": spec.legacy_effect,
            "canonical_effect": spec.effect,
            "available": spec.available,
            "availability": {
                "available": spec.available,
                "reason": spec.availability_reason,
            },
            "deploymentRevision": rev,
            "expiresAt": expires_at,
            "annotations": spec.annotations,
            "capability_refs": list(spec.capability_refs),
            "input_schema": json.loads(json.dumps(dict(spec.input_schema))),
            "output_schema": json.loads(json.dumps(dict(spec.output_schema))),
            "inputSchema": json.loads(json.dumps(dict(spec.input_schema))),
            "outputSchema": json.loads(json.dumps(dict(spec.output_schema))),
        }
        if not spec.available:
            entry["unavailableReason"] = spec.availability_reason
        projected.append(entry)
    return tuple(projected)


def catalog_static_digest(catalog: Sequence[Mapping[str, Any]]) -> str:
    """Compute deterministic SHA-256 digest of catalog entries excluding wall-clock expiresAt."""
    normalized = [
        {k: v for k, v in entry.items() if k != "expiresAt"}
        for entry in catalog
    ]
    return canonical_json_digest(normalized)


def validate_timestamp_freshness(expires_at: str, *, now: datetime | None = None) -> None:
    """Raise ValueError('REGISTRY_EXPIRED') when expires_at is not strictly in the future."""
    ref_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if _parse_utc_iso(expires_at) <= ref_now:
        raise ValueError("REGISTRY_EXPIRED")


def discover_public_capabilities(
    *,
    cli_group: click.Group | None = None,
    plugin_registry: Any | None = None,
) -> set[str]:
    """Discover all public Click commands/subcommands and builtin diagnostic plugins."""
    if cli_group is None:
        from fixos.cli.main import cli as default_cli

        cli_group = default_cli
    if plugin_registry is None:
        from fixos.plugins.registry import PluginRegistry

        plugin_registry = PluginRegistry()
        plugin_registry._register_builtins()

    discovered: set[str] = set()
    for cmd_name in sorted(cli_group.commands):
        cmd_obj = cli_group.commands[cmd_name]
        discovered.add(f"cli:{cmd_name}")
        if isinstance(cmd_obj, click.Group):
            for sub_name in sorted(cmd_obj.commands):
                discovered.add(f"cli:{cmd_name} {sub_name}")

    plugins_map = getattr(plugin_registry, "_plugins", {})
    for plugin_name in sorted(plugins_map):
        discovered.add(f"plugin:{plugin_name}")

    return discovered


def verify_capability_parity(
    *,
    cli_group: click.Group | None = None,
    plugin_registry: Any | None = None,
    operations: Sequence[OperationSpec] = CANONICAL_OPERATIONS,
    non_exposed: Sequence[NonExposedCapability] = NON_EXPOSED_CAPABILITIES,
) -> dict[str, Any]:
    """Verify every public CLI command/subcommand and plugin has a catalog entry or non-exposure record."""
    validate_registry_entries(operations)
    discovered = discover_public_capabilities(cli_group=cli_group, plugin_registry=plugin_registry)

    registered_refs: set[str] = set()
    duplicate_refs: set[str] = set()
    for spec in operations:
        for ref in spec.capability_refs:
            if ref.startswith("internal:"):
                continue
            if ref in registered_refs:
                duplicate_refs.add(ref)
            registered_refs.add(ref)

    exempt_refs: set[str] = set()
    for item in non_exposed:
        if not item.capability_ref.strip() or not item.reason.strip() or not item.owner.strip():
            raise ValueError(f"INVALID_NON_EXPOSURE_RECORD: {item.capability_ref}")
        if item.capability_ref in exempt_refs:
            duplicate_refs.add(item.capability_ref)
        exempt_refs.add(item.capability_ref)

    overlap = sorted(registered_refs & exempt_refs)
    if overlap or duplicate_refs:
        raise ValueError(f"DUPLICATE_CAPABILITY_BINDING: {sorted(set(overlap) | duplicate_refs)}")

    accounted = registered_refs | exempt_refs
    missing = sorted(discovered - accounted)
    if missing:
        raise ValueError(f"UNREGISTERED_PUBLIC_CAPABILITIES: {missing}")

    stale = sorted(accounted - discovered)
    if stale:
        raise ValueError(f"STALE_CAPABILITY_BINDINGS: {stale}")

    return {
        "discovered_count": len(discovered),
        "registered_count": len(registered_refs),
        "non_exposed_count": len(exempt_refs),
        "internal_count": sum(
            1 for spec in operations for ref in spec.capability_refs if ref.startswith("internal:")
        ),
    }
