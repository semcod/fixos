# Ticket 010: Harden JetBrains AI helper control

- **ID**: ticket-010
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-20

## Goal and scope

Correct JetBrains main-process discovery so terminal commands and helpers are
never diagnosed as IDE JVMs. Add a read-only-by-default AI control that can
persistently disable the exact Qoder and JetBrains AI Assistant plugin IDs and
gracefully stop only identity-verified Qoder helpers, without terminating the
main JVM or closing IDE windows.

## Acceptance criteria

- [x] AC-01: Main IDE discovery uses the executable identity, not arbitrary
  command arguments, and excludes terminal shells plus MCP/native helpers.
- [x] AC-02: `fixos jetbrains ai` reports exact active Qoder helpers, inferred
  JetBrains configuration and disabled-plugin state without mutation by default.
- [x] AC-03: Plugin changes target only `com.qoder` and `com.intellij.ml.llm`,
  use atomic writes, preserve unrelated entries and require explicit apply.
- [x] AC-04: Helper termination revalidates PID creation time, executable,
  parent relationship and parent main-IDE identity before sending TERM.
- [x] AC-05: Human/JSON output, dry-run, confirmation, idempotence and refusal
  paths are covered by deterministic tests.
- [x] AC-06: Live verification reports only PyCharm PID 143907, confirms exact
  Qoder respawns can be stopped and both plugin IDs are disabled for the next
  IDE start; full validation passes.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
