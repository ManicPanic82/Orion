"""Supervisor restart policy behaviour for the Orion Core process."""

from __future__ import annotations

import threading

import pytest

from orion.core.lifecycle import CoreLifecycleState
from orion.core.supervisor import CoreSupervisor, RestartPolicy


def test_restart_policy_allows_within_budget() -> None:
    policy = RestartPolicy(max_restarts=2, initial_delay_s=0.0)
    assert policy.should_restart(1) is True
    assert policy.should_restart(2) is True
    assert policy.should_restart(3) is False


def test_restart_backoff_is_exponential_and_bounded() -> None:
    policy = RestartPolicy(max_restarts=5, initial_delay_s=1.0, max_delay_s=10.0)
    assert policy.backoff_s(1) == pytest.approx(1.0)
    assert policy.backoff_s(2) == pytest.approx(2.0)
    assert policy.backoff_s(10) == pytest.approx(10.0)


def test_supervisor_records_crashes_and_stops_when_budget_is_exhausted() -> None:
    supervisor = CoreSupervisor()
    assert supervisor.attempts == 0
    assert supervisor.crashes == ()

    supervisor.record_crash(reason="crash", exit_code=1)
    assert supervisor.attempts == 1
    assert supervisor.crashes[0]["reason"] == "crash"

    assert supervisor.should_restart() is True
    supervisor.record_crash(reason="crash", exit_code=2)
    assert supervisor.should_restart() is False

    assert supervisor.final_state(crashed=True) is CoreLifecycleState.FAILED
    assert supervisor.final_state(crashed=False) is CoreLifecycleState.STOPPED


def test_supervisor_reset_clears_crash_history() -> None:
    supervisor = CoreSupervisor()
    supervisor.record_crash(reason="crash", exit_code=1)
    assert supervisor.attempts == 1

    supervisor.reset()
    assert supervisor.attempts == 0
    assert supervisor.crashes == ()


class _FakeChild:
    def __init__(self, exit_code: int) -> None:
        self._exit_code = exit_code

    def wait(self) -> int:
        return self._exit_code


def test_supervise_restarts_crashed_child_within_budget() -> None:
    supervisor = CoreSupervisor(
        policy=RestartPolicy(max_restarts=2, initial_delay_s=0.0, max_delay_s=0.0)
    )
    spawns: list[int] = []

    def spawn() -> _FakeChild:
        spawns.append(1)
        return _FakeChild(1 if len(spawns) < 3 else 0)

    rc = supervisor.supervise(spawn)
    assert rc == 0
    assert len(spawns) == 3
    assert supervisor.attempts == 2


def test_supervise_returns_failure_when_budget_exhausted() -> None:
    supervisor = CoreSupervisor(
        policy=RestartPolicy(max_restarts=1, initial_delay_s=0.0, max_delay_s=0.0)
    )
    spawns: list[int] = []

    def spawn() -> _FakeChild:
        spawns.append(1)
        return _FakeChild(1)

    rc = supervisor.supervise(spawn)
    assert rc == 1
    assert len(spawns) == 2
    assert supervisor.final_state(crashed=True) is CoreLifecycleState.FAILED


def test_supervise_stop_event_returns_zero() -> None:
    stop = threading.Event()
    stop.set()
    supervisor = CoreSupervisor(
        policy=RestartPolicy(max_restarts=5, initial_delay_s=0.0, max_delay_s=0.0)
    )
    spawns: list[int] = []
    rc = supervisor.supervise(lambda: (spawns.append(1), _FakeChild(0))[1], stop_event=stop)
    assert rc == 0
    assert supervisor.attempts == 0


def test_supervise_child_exit_zero_is_clean() -> None:
    supervisor = CoreSupervisor(
        policy=RestartPolicy(max_restarts=3, initial_delay_s=0.0, max_delay_s=0.0)
    )
    spawns: list[int] = []

    def spawn() -> _FakeChild:
        spawns.append(1)
        return _FakeChild(0)

    assert supervisor.supervise(spawn) == 0
    assert len(spawns) == 1

def test_supervisor_terminates_running_child_when_stopped() -> None:
    import time

    class _BlockingChild:
        def __init__(self) -> None:
            self.finished = threading.Event()
            self.terminated = threading.Event()

        def wait(self) -> int:
            self.finished.wait()
            return 0

        def poll(self):
            return None if not self.finished.is_set() else 0

        def terminate(self) -> None:
            self.terminated.set()
            self.finished.set()

    child = _BlockingChild()
    stop = threading.Event()
    supervisor = CoreSupervisor()
    result = []
    worker = threading.Thread(
        target=lambda: result.append(supervisor.supervise(lambda: child, stop_event=stop))
    )
    worker.start()
    time.sleep(0.05)
    stop.set()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert child.terminated.is_set()
    assert result == [0]


def test_supervisor_stop_interrupts_restart_backoff() -> None:
    import time

    stop = threading.Event()
    supervisor = CoreSupervisor(
        policy=RestartPolicy(max_restarts=3, initial_delay_s=5.0, max_delay_s=5.0)
    )
    result = []
    worker = threading.Thread(
        target=lambda: result.append(supervisor.supervise(lambda: _FakeChild(1), stop_event=stop))
    )
    worker.start()
    deadline = time.monotonic() + 1.0
    while supervisor.attempts < 1 and time.monotonic() < deadline:
        time.sleep(0.01)
    stop.set()
    worker.join(timeout=1)
    assert not worker.is_alive()
    assert result == [0]
