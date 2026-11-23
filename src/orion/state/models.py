"""Immutable state models the presentation layer renders.

Phase 1 defines only what the shell displays. There is deliberately no objective,
memory, or profile model here: those belong to the Core database and arrive with
the phases that implement them. Adding them now would be speculative structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from orion.config.settings import Severity

__all__ = [
    "AppSnapshot",
    "CommandResult",
    "ComponentStatus",
    "EventRecord",
    "MAX_COMMAND_LENGTH",
    "StatusKind",
    "TaskState",
    "TaskSummary",
]

MAX_COMMAND_LENGTH = 2_000


class StatusKind(StrEnum):
    """How a component's state must be presented.

    ``MOCK`` exists as a first-class state so that no mock can be rendered as if
    it were a real connected component (CONTRACTS.md invariant 10).
    """

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    MOCK = "mock"


class TaskState(StrEnum):
    """Task states surfaced by the presentation layer.

    The real lifecycle states (created, planned, running, completed, failed,
    partial, paused, cancelled) arrived with the durable task engine in Phase 4;
    ``SIMULATED`` is retained for older mock snapshots so nothing relies on an
    invented vocabulary.
    """

    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    SIMULATED = "simulated"


@dataclass(frozen=True, slots=True)
class ComponentStatus:
    """Status of one named component shown on the Command Centre."""

    component_id: str
    label: str
    kind: StatusKind
    detail: str


@dataclass(frozen=True, slots=True)
class TaskSummary:
    """A task row as displayed in the shell."""

    task_id: str
    title: str
    state: TaskState
    note: str = ""


@dataclass(frozen=True, slots=True)
class EventRecord:
    """A single activity-console record."""

    event_id: str
    timestamp: datetime
    severity: Severity
    source: str
    message: str


@dataclass(frozen=True, slots=True)
class AppSnapshot:
    """Everything the shell renders at one point in time."""

    agent: ComponentStatus
    model: ComponentStatus
    tasks: tuple[TaskSummary, ...]
    events: tuple[EventRecord, ...]
    is_mock: bool


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Outcome of a command-composer submission."""

    request_id: str
    accepted: bool
    simulated: bool
    message: str
