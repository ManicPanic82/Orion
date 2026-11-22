"""Supervisor restart policy behaviour for the Orion Core process."""

from __future__ import annotations

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
