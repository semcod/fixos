# Ticket 015: Show exact remediation effects and prefer GLM 5.3

- **ID**: ticket-015
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-01

## Goal and scope

Make every executable remediation choice explain its exact filesystem or
system targets, effect and ordered commands before the human selects it. Reject
diagnostic prose that merely resembles a numbered legacy command, so log PIDs
and inline code cannot become executable menu entries.

For OpenRouter, prefer the currently verified GLM 5.3 model identifier and
migrate the obsolete model value previously documented by FixOS. The change is
bounded to runtime configuration, the HITL remediation contract/UI and their
unit tests; it does not execute cleanup, alter dependencies or change merge
policy.

## Acceptance criteria

- [x] AC-01: The request is recorded as `SESSION_EXECUTION_AUTHORIZATION` and
  implementation remains within the declared application scope.
- [x] AC-02: Every structured remediation action contains bounded affected
  targets, and the menu labels them together with the effect, exact ordered
  mutation commands and read-only verification commands.
- [x] AC-03: A diagnosis containing bracketed process IDs or other inline code
  produces no executable legacy actions; only explicit anchored legacy action
  syntax remains accepted.
- [x] AC-04: OpenRouter defaults to official model ID `z-ai/glm-5.3`; the exact
  obsolete FixOS value `openrouter/qwen/qwen3.7-plus` migrates to that model,
  while explicit valid custom models remain unchanged.
- [x] AC-05: Focused unit tests, the Python stack checks and the managed
  governance gate pass before publication through `goal -a`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
