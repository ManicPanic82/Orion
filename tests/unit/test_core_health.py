"""Health reporting behaviour for the Orion Core process."""

from __future__ import annotations

from orion.core.health import HealthCheck, HealthMonitor, HealthSnapshot, HealthStatus
from orion.core.lifecycle import CoreLifecycleState


def _check(status: HealthStatus, name: str = "check") -> HealthCheck:
    return HealthCheck(name=name, status=status, detail="detail")


def test_snapshot_with_only_ok_checks_is_ok() -> None:
    monitor = HealthMonitor()
    monitor.register("process", lambda: _check(HealthStatus.OK, "process"))
    snapshot = monitor.snapshot(state=CoreLifecycleState.READY)

    assert snapshot.ok is True
    assert snapshot.degraded is False
    assert snapshot.failed is False
    assert snapshot.state is CoreLifecycleState.READY
    assert monitor.overall(snapshot) is HealthStatus.OK


def test_degraded_check_is_reported_without_failing() -> None:
    monitor = HealthMonitor()
    monitor.register("process", lambda: _check(HealthStatus.DEGRADED, "process"))
    snapshot = monitor.snapshot()

    assert snapshot.degraded is True
    assert snapshot.failed is False
    assert snapshot.ok is False
    assert monitor.overall(snapshot) is HealthStatus.DEGRADED


def test_failed_check_fails_the_snapshot() -> None:
    monitor = HealthMonitor()
    monitor.register("process", lambda: _check(HealthStatus.FAILED, "process"))
    snapshot = monitor.snapshot()

    assert snapshot.failed is True
    assert snapshot.degraded is False
    assert monitor.overall(snapshot) is HealthStatus.FAILED


def test_checks_are_sorted_by_name_for_a_stable_snapshot() -> None:
    monitor = HealthMonitor()
    monitor.register("zeta", lambda: _check(HealthStatus.OK, "zeta"))
    monitor.register("alpha", lambda: _check(HealthStatus.OK, "alpha"))
    snapshot = monitor.snapshot()

    assert [check.name for check in snapshot.checks] == ["alpha", "zeta"]


def test_clearing_a_check_removes_it_from_the_snapshot() -> None:
    monitor = HealthMonitor()
    monitor.register("process", lambda: _check(HealthStatus.OK, "process"))
    monitor.clear("process")
    snapshot = monitor.snapshot()

    assert snapshot.checks == ()
    assert snapshot.ok is True
