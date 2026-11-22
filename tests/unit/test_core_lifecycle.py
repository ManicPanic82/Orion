"""Lifecycle state machine behaviour for the Orion Core process."""

from __future__ import annotations

import pytest

from orion.core.lifecycle import CoreLifecycleState, LifecycleError, transition


def test_start_transition_is_valid() -> None:
    state = transition(CoreLifecycleState.STOPPED, CoreLifecycleState.STARTING)
    assert state is CoreLifecycleState.STARTING


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (CoreLifecycleState.STARTING, CoreLifecycleState.READY),
        (CoreLifecycleState.STARTING, CoreLifecycleState.DEGRADED),
        (CoreLifecycleState.STARTING, CoreLifecycleState.FAILED),
    ],
)
def test_running_transitions_are_valid(
    source: CoreLifecycleState, target: CoreLifecycleState
) -> None:
    assert transition(source, target) is target


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (CoreLifecycleState.READY, CoreLifecycleState.STOPPING),
        (CoreLifecycleState.DEGRADED, CoreLifecycleState.STOPPING),
        (CoreLifecycleState.DEGRADED, CoreLifecycleState.READY),
        (CoreLifecycleState.STOPPING, CoreLifecycleState.STOPPED),
    ],
)
def test_shutdown_transitions_are_valid(
    source: CoreLifecycleState, target: CoreLifecycleState
) -> None:
    assert transition(source, target) is target


def test_stopped_can_restart_after_stopping() -> None:
    assert (
        transition(CoreLifecycleState.STOPPING, CoreLifecycleState.STOPPED)
        is CoreLifecycleState.STOPPED
    )
    assert (
        transition(CoreLifecycleState.STOPPED, CoreLifecycleState.STARTING)
        is CoreLifecycleState.STARTING
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (CoreLifecycleState.STOPPED, CoreLifecycleState.READY),
        (CoreLifecycleState.READY, CoreLifecycleState.STARTING),
        (CoreLifecycleState.STOPPED, CoreLifecycleState.STOPPING),
    ],
)
def test_non_transitions_are_rejected(
    source: CoreLifecycleState, target: CoreLifecycleState
) -> None:
    with pytest.raises(LifecycleError):
        transition(source, target)
