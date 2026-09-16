# Ticket 033: Make disk cleanup effective and honest under critical disk pressure

- **ID**: ticket-033
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

On 2026-09-15 the root filesystem of the owner's workstation reached 100%
(0 bytes free). `fixos cleanup` promised "4.16 GB" of safe cleanup, freed
0.64 GB, and listed the 65 GB JetBrains cache only as a manual command that
refuses to run while the JetBrains Toolbox daemon is alive. `fixos fix` retried
an LLM call four times after an authentication error. Deleting the JetBrains
cache by hand freed 66 GB immediately.

Make cleanup report what it can actually reclaim, clean the caches it
promises, offer large rebuildable IDE caches, degrade gracefully when Docker
is slow, and stop retrying non-retryable LLM authentication failures.

## Acceptance criteria

- [ ] AC-01: Tool-managed prunes (pnpm, conda) are not counted as guaranteed
  reclaimable space; the plan labels them as "prune unreferenced" and reports
  the measured change after running.
- [ ] AC-02: Poetry cleanup clears every Poetry cache and its artifacts, never
  `~/.cache/pypoetry/virtualenvs`, and does not silently succeed with no effect.
- [ ] AC-03: The JetBrains cache is a safe, rebuildable cache offered in the
  interactive plan. Running-IDE detection matches IDE executables only, not
  JetBrains Toolbox or its daemon.
- [ ] AC-04: When `docker system df` times out, cleanup still lists bounded,
  reviewable Docker actions instead of dropping Docker from the report.
- [ ] AC-05: An LLM authentication error ends the fix session after one attempt
  with actionable guidance, without generic external searches or retries.
- [ ] AC-06: `fixos help` shows the command help.
- [ ] AC-07: Unit tests cover each case; the existing suite and governance pass.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION`: on 2026-09-15 the owner asked the agent to
fix the fixos package ("popraw paczkę fixos") after comparing `fixos cleanup`
with the manual cleanup. Publication uses the protected OneDev and Validator
route only.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
