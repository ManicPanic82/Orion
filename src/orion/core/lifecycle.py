"""Core process lifecycle state machine.

Phase 2 gives Orion an independent Core process. This module owns the state
model only; the supervisor and process entry own transitions, never the UI.

The state names are part of the external contract documented in
``docs/agent-guides/PHASE_02_CORE_SERVICE.md`` so the UI and diagnostics agree
on vocabulary.
"""

from __future__ import annotations

from enum import StrEnum


class CoreLifecycleState(StrEnum):
    """Lifecycle states an Orion Core process can be observed in."""

    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    FAILED = "failed"


_TRANSITIONS: dict[CoreLifecycleState, frozenset[CoreLifecycleState]] = {
    CoreLifecycleState.STOPPED: frozenset({CoreLifecycleState.STARTING}),
    CoreLifecycleState.STARTING: frozenset(
        {CoreLifecycleState.READY, CoreLifecycleState.DEGRADED, CoreLifecycleState.FAILED}
    ),
    CoreLifecycleState.READY: frozenset({CoreLifecycleState.STOPPING}),
    CoreLifecycleState.DEGRADED: frozenset({CoreLifecycleState.READY, CoreLifecycleState.STOPPING}),
    CoreLifecycleState.STOPPING: frozenset({CoreLifecycleState.STOPPED}),
    CoreLifecycleState.FAILED: frozenset(),
}


class LifecycleError(RuntimeError):
    """Raised when a lifecycle transition is not allowed."""


def transition(state: CoreLifecycleState, target: CoreLifecycleState) -> CoreLifecycleState:
    """Return the target state, or raise :class:`LifecycleError` when invalid."""
    if target not in _TRANSITIONS[state]:
        raise LifecycleError(f"invalid Orion Core transition: {state.value} -> {target.value}")
    return target
