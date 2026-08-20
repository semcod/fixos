"""Unit tests for evidence-led recent process-chain diagnostics."""

from __future__ import annotations

import pytest

from fixos.diagnostics.process_chains import (
    FileLockWait,
    ProcessChainInspector,
    ProcessChainSafetyError,
    ProcessRecord,
    parse_proc_locks,
)


NOW = 10_000.0


def _process(
    pid: int,
    ppid: int,
    age: float,
    command: str,
    *,
    status: str = "sleeping",
    cpu: float = 0.0,
    memory: float = 0.0,
) -> ProcessRecord:
    argv = tuple(command.split())
    return ProcessRecord(
        pid=pid,
        ppid=ppid,
        name=argv[0],
        cmdline=argv,
        create_time=NOW - age,
        status=status,
        cpu_percent=cpu,
        memory_percent=memory,
        username="tester",
    )


def _glm_records() -> list[ProcessRecord]:
    return [
        _process(10, 1, 10_000, "pycharm"),
        _process(20, 10, 5_000, "npm exec glm-agent"),
        _process(21, 20, 4_999, "node glm-agent"),
        _process(22, 21, 4_998, "pycharm stdioMcpServer"),
        _process(30, 10, 300, "npm exec glm-agent"),
        _process(31, 30, 299, "node glm-agent"),
        _process(32, 31, 298, "pycharm stdioMcpServer"),
    ]


def _inspector(records, **kwargs) -> ProcessChainInspector:
    return ProcessChainInspector(
        snapshot_provider=lambda: list(records),
        lock_wait_provider=lambda: [],
        clock=lambda: NOW,
        self_pid=999,
        **kwargs,
    )


def test_recent_processes_are_newest_first_and_limited():
    records = [
        _process(10, 1, 5000, "old"),
        _process(20, 10, 30, "newer"),
        _process(30, 10, 10, "newest"),
    ]

    recent = _inspector(records).list_recent(max_age_seconds=60, limit=2)

    assert [item.pid for item in recent] == [30, 20]
    assert recent[0].to_dict(now=NOW)["age_seconds"] == 10.0


def test_duplicate_fresh_tree_is_possible_but_needs_more_evidence_to_act():
    findings = _inspector(_glm_records()).find_suspicious_chains(
        max_age_seconds=600
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.root.pid == 30
    assert [item.pid for item in finding.members] == [30, 31, 32]
    assert [item.pid for item in finding.older_duplicate_roots] == [20]
    assert finding.confidence == "possible"
    assert finding.actionable is False
    assert "duplicates-older-process-chain" in finding.reason_codes
    assert "multi-process-chain" in finding.reason_codes


def test_direct_lock_wait_confirms_fresh_chain_blocks_older_process():
    records = [
        _process(10, 1, 5000, "editor"),
        _process(30, 1, 60, "helper"),
        _process(31, 30, 59, "worker"),
    ]
    waits = [FileLockWait(waiter_pid=10, holder_pid=31, lock_id="7", resource="x")]

    finding = _inspector(records).find_suspicious_chains(
        max_age_seconds=120,
        lock_waits=waits,
    )[0]

    assert finding.confidence == "confirmed"
    assert finding.blocking_older_pids == (10,)
    assert finding.actionable is True
    assert "holds-lock-needed-by-older-process" in finding.reason_codes


def test_proc_locks_parser_links_waiter_to_preceding_holder():
    waits = parse_proc_locks(
        "7: POSIX ADVISORY WRITE 31 fc:00:123 0 EOF\n"
        "7: -> POSIX ADVISORY WRITE 10 fc:00:123 0 EOF\n"
        "8: FLOCK ADVISORY WRITE 99 fc:00:456 0 EOF\n"
    )

    assert waits == [
        FileLockWait(waiter_pid=10, holder_pid=31, lock_id="7", resource="fc:00:123")
    ]


def test_normal_recent_process_is_listed_but_not_called_suspicious():
    records = [_process(10, 1, 30, "ordinary-app")]
    inspector = _inspector(records)

    assert [item.pid for item in inspector.list_recent(max_age_seconds=60)] == [10]
    assert inspector.find_suspicious_chains(max_age_seconds=60) == []


def test_current_process_ancestry_is_protected_from_termination():
    records = [
        _process(10, 1, 5000, "terminal"),
        _process(20, 10, 50, "codex"),
        _process(30, 1, 5000, "codex"),
    ]
    inspector = ProcessChainInspector(
        snapshot_provider=lambda: records,
        lock_wait_provider=lambda: [],
        clock=lambda: NOW,
        self_pid=20,
    )
    finding = inspector.find_suspicious_chains(
        max_age_seconds=60,
        suspicious_only=False,
    )[0]

    assert finding.protected is True
    with pytest.raises(ProcessChainSafetyError, match="contains FixOS"):
        inspector.terminate_chain(finding, dry_run=True, require_actionable=False)


def test_privileged_chain_is_protected_by_default():
    record = ProcessRecord(
        pid=30,
        ppid=1,
        name="root-worker",
        cmdline=("root-worker",),
        create_time=NOW - 30,
        status="disk-sleep",
        username="root",
    )
    finding = _inspector([record]).find_suspicious_chains(
        max_age_seconds=60
    )[0]

    assert finding.protected is True


def test_termination_dry_run_targets_leaves_first_without_signalling():
    records = _glm_records()
    calls: list[tuple[int, bool]] = []
    inspector = _inspector(records, terminator=lambda pid, force: calls.append((pid, force)))
    finding = inspector.find_suspicious_chains(max_age_seconds=600)[0]

    result = inspector.terminate_chain(finding)

    assert result.dry_run is True
    assert result.target_pids == (32, 31, 30)
    assert result.surviving_pids == (32, 31, 30)
    assert calls == []


def test_graceful_termination_signals_only_selected_tree_leaf_to_root():
    records = _glm_records()
    alive = {record.pid for record in records}
    identities = {record.pid: record.create_time for record in records}
    calls: list[tuple[int, bool]] = []

    def terminate(pid: int, force: bool) -> None:
        calls.append((pid, force))
        alive.discard(pid)

    inspector = _inspector(
        records,
        terminator=terminate,
        identity_provider=identities.get,
        alive_provider=lambda pid, expected: pid in alive,
    )
    finding = inspector.find_suspicious_chains(max_age_seconds=600)[0]

    result = inspector.terminate_chain(
        finding,
        dry_run=False,
        grace_seconds=0,
        require_actionable=False,
    )

    assert calls == [(32, False), (31, False), (30, False)]
    assert result.success is True
    assert result.terminated_pids == (32, 31, 30)
    assert 10 in alive and 20 in alive and 21 in alive and 22 in alive


def test_pid_reuse_is_refused_before_any_signal():
    records = _glm_records()
    calls: list[tuple[int, bool]] = []
    identities = {record.pid: record.create_time for record in records}
    identities[30] += 1
    inspector = _inspector(
        records,
        terminator=lambda pid, force: calls.append((pid, force)),
        identity_provider=identities.get,
    )
    finding = inspector.find_suspicious_chains(max_age_seconds=600)[0]

    result = inspector.terminate_chain(
        finding,
        dry_run=False,
        grace_seconds=0,
        require_actionable=False,
    )

    assert calls == [(32, False), (31, False)]
    assert result.success is False
    assert result.errors == ("pid 30: identity changed before termination",)


def test_escalation_is_opt_in_and_rechecks_identity():
    records = _glm_records()
    alive = {record.pid for record in records}
    identities = {record.pid: record.create_time for record in records}
    calls: list[tuple[int, bool]] = []

    def terminate(pid: int, force: bool) -> None:
        calls.append((pid, force))
        if force:
            alive.discard(pid)

    inspector = _inspector(
        records,
        terminator=terminate,
        identity_provider=identities.get,
        alive_provider=lambda pid, expected: pid in alive,
    )
    finding = inspector.find_suspicious_chains(max_age_seconds=600)[0]

    result = inspector.terminate_chain(
        finding,
        dry_run=False,
        grace_seconds=0,
        escalate=True,
        require_actionable=False,
    )

    assert calls == [
        (32, False),
        (31, False),
        (30, False),
        (32, True),
        (31, True),
        (30, True),
    ]
    assert result.escalated_pids == (32, 31, 30)
    assert result.success is True


def test_possible_evidence_requires_override_for_termination():
    records = [
        _process(10, 1, 5000, "old-root"),
        _process(30, 1, 30, "new-root", status="disk-sleep"),
    ]
    inspector = _inspector(records)
    finding = inspector.find_suspicious_chains(max_age_seconds=60)[0]

    assert finding.confidence == "possible"
    assert finding.actionable is False
    with pytest.raises(ProcessChainSafetyError, match="lacks likely"):
        inspector.terminate_chain(finding, dry_run=False)


def test_single_repeated_worker_is_not_suspicious_without_more_evidence():
    records = [
        _process(10, 1, 50, "udev-worker"),
        _process(20, 1, 40, "udev-worker"),
    ]

    assert _inspector(records).find_suspicious_chains(max_age_seconds=60) == []
