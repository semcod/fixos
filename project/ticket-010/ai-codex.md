---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-010
---
# Participant: codex (AI agent)

## Understanding

Live diagnosis found a Qoder child using about 1.2 GB RSS and 10--11% CPU and a
separate JetBrains AI quota failure every 23 seconds in the main JVM. Qoder was
already pending disablement but remained loaded in the long-running IDE. The
doctor also falsely selected terminal shells because it searched every command
argument for the word `pycharm`.

## Execution plan

1. Match a main JetBrains process only from its launcher identity.
2. Add an evidence-led AI status/disable/helper-stop service with exact identity
   revalidation and atomic plugin configuration writes.
3. Expose it as a read-only-by-default `fixos jetbrains ai` command.
4. Add deterministic discovery, dry-run, mutation, idempotence and safety tests.
5. Verify live state without closing windows and publish through Validator App.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Recorded authorization to stop the exact Qoder helper and disable the two
  confirmed plugin IDs while preserving the main IDE JVM and every open window.
- Before implementation, revalidated and terminated Qoder PID 156099 with TERM.
  PyCharm PID 143907 remained alive and Qoder did not restart.
- Added `com.intellij.ml.llm` to the existing disabled plugin configuration;
  `com.qoder` was already present. This takes full effect at the next IDE start.
- Replaced command-text matching with exact JetBrains launcher matching. Live
  doctor output now contains only the real PyCharm PID 143907 instead of shell,
  terminal, MCP and diagnostic-command false positives.
- Added `fixos jetbrains ai` status, dry-run and explicit-apply flows. It infers
  only active-product configuration, atomically preserves disabled plugin
  entries and revalidates Qoder PID, creation time, executable, parent PID and
  parent IDE identity before TERM. It never uses SIGKILL or signals the JVM.
- Live application discovered that the already-loaded plugin respawns Qoder
  about once per minute until IDE restart. FixOS successfully stopped exact
  respawn PIDs 3221424 and 3290938; PyCharm PID 143907 stayed alive. Both plugin
  IDs are persistently disabled, so respawn and the quota loop will not return
  after the next ordinary IDE start.
- Focused validation passes 25 tests. Full validation passes 535 tests with 5
  skipped and 16 deselected; scoped Ruff, compileall and governance are clean.
- Advanced the validated implementation to PUBLICATION for exact-head review.
- Published PR #20 at exact head `d500e3f...`. Validator run 32365098029
  approved it as review 4982270230 after two stable policy reads, merged it as
  `f38c473...` and deleted the remote implementation branch.
- Began this governance-only closure from the integrated merge commit and
  marked the ticket `DONE / DONE` without changing executable code.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
