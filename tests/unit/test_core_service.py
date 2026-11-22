"""Orion Core service facade behaviour."""

from __future__ import annotations

from orion.core.lifecycle import CoreLifecycleState
from orion.core.service import OrionCore, OrionCoreStatus
from orion.core.health import HealthStatus


def test_core_starts_into_ready_state_and_serves_the_api() -> None:
    core = OrionCore(version="0.1.0", token="token", host="127.0.0.1", port=0)

    status = core.start()

    assert isinstance(status, OrionCoreStatus)
    assert core.state is CoreLifecycleState.READY
    assert status.state is CoreLifecycleState.READY
    assert status.status is HealthStatus.OK
    assert status.api_listening is True
    assert status.version == "0.1.0"
    assert core.api.listening is True


def test_core_health_snapshot_reflects_the_running_state() -> None:
    core = OrionCore()
    core.start()

    snapshot = core.health()

    assert snapshot.state is CoreLifecycleState.READY
    assert snapshot.ok is True
    assert snapshot.checks[0].name == "process"


def test_core_stop_returns_to_stopped_state() -> None:
    core = OrionCore()
    core.start()
    status = core.stop()

    assert core.state is CoreLifecycleState.STOPPED
    assert status.state is CoreLifecycleState.STOPPED
    assert status.api_listening is False
    assert core.api.listening is False


def test_core_cannot_start_twice() -> None:
    core = OrionCore()

    core.start()
    try:
        core.start()
        raise AssertionError("expected a RuntimeError when starting twice")
    except RuntimeError as error:
        assert "cannot start Orion Core" in str(error)
    finally:
        core.stop()


def test_core_publishes_events_into_its_stream() -> None:
    core = OrionCore()
    received = []
    core.events.subscribe(received.append)

    core.publish("task.created", {"task_id": "t1"})

    assert len(received) == 1
    assert received[0].type == "task.created"
    assert core.events.sequence == 1
