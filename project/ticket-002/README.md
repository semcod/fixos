# Ticket 002: Diagnose blocking chains and recover JetBrains responsiveness

- **ID**: ticket-002
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-20

## Goal and scope

Add a bounded process-chain diagnostic to FixOS that lists the newest
processes, identifies fresh child trees with evidence that they may block an
older application, and can terminate an explicitly selected tree without
signalling its older parent or shared process group.
Also diagnose a JetBrains IDE whose shared JVM remains overloaded after a
project window closes, and offer a bounded JVM recovery action that preserves
all open IDE windows.

## Acceptance criteria

- [x] AC-01: Recent processes are listed newest-first with stable identity,
  age, parent, status and resource metadata.
- [x] AC-02: Analysis reconstructs fresh process trees and distinguishes
  duplicate chains, uninterruptible tasks and direct Linux file-lock waits
  from unsupported guesses.
- [x] AC-03: Termination is dry-run by default, checks PID creation time to
  prevent PID-reuse races, protects the current/system process ancestry and
  signals only the selected tree from leaves to root.
- [x] AC-04: A live observation can compare process state before and after a
  bounded action without claiming that an application recovered when CPU/log
  evidence still shows contention.
- [x] AC-05: Unit tests cover ordering, tree selection, blocker evidence,
  safety refusals, PID reuse and graceful/escalated termination.
- [x] AC-06: Governance and the focused/full Python test suites pass.
- [x] AC-07: JetBrains diagnosis correlates recent IDE log symptoms, JVM
  resource pressure and EDT thread state without confusing helper MCP servers
  with the main IDE process.
- [x] AC-08: Recovery never closes or signals the IDE, is dry-run by default,
  validates PID identity and invokes only a discovered matching-JVM `jcmd
  GC.run` when memory-pressure evidence justifies it and the caller opts in.
- [x] AC-09: Before/after verification reports CPU, memory and new stall-log
  events without claiming success solely because the diagnostic command ran.

## Validation result

- The selected GLM/stdio MCP tree exited after a graceful termination and did
  not respawn during the validation window; the main PyCharm process remained
  alive.
- Immediate observation showed that one young duplicate was not the complete
  cause: PyCharm still logged a write-action loop and averaged about 526% CPU.
- The later observation showed no new write-action wait messages in three
  seconds and about 150% average PyCharm CPU. No user process or kernel file
  lock was waiting on another process; one unrelated USB kernel worker remained
  in uninterruptible sleep.
- The library's live dry run returned no actionable unprotected chain. UI-level
  responsiveness cannot be proven from the process table alone.
- The JetBrains live diagnosis found high CPU, 882 threads, repeated
  write-action/EDT stalls and a Git stash refresh loop over seven deleted
  working directories. Heap use was 67.9%, so recovery correctly remained a
  dry run and did not invoke `GC.run`.
- The focused JetBrains/process tests passed 26/26. The full suite passed with
  486 tests, 5 skips and 16 intentional deselections.
- The final governance gate passed with 0 errors and 0 warnings.

## Publication

- [PR #6](https://github.com/semcod/fixos/pull/6) passed the full target CI on
  exact head `70609fbbc006fedb0851d991f4639c90c9a849e8`.
- Repository-scoped Validator App review `4981125970` approved that exact head
  for `ticket-002` after deterministic validation and two stable policy reads.
- The protected validator merged PR #6 as
  `10c550c5aa3cbbdd849d9b582a1c7ac9d7fa9de2`; the remote implementation
  branch was deleted automatically.
- The temporary clean validator worktree and the released ticket worktree were
  removed through Git after confirming that both were clean and the head was
  reachable from integrated `main`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
