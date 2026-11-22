"""Deterministic mock state provider for the Phase 1 shell.

This provider exists to exercise the presentation layer honestly. It:

* reports every component as :attr:`StatusKind.MOCK`, never as connected;
* records submitted commands as *simulated* tasks, never as completed work;
* takes an injected clock so tests are deterministic;
* holds no model, task, or permission logic.

It is not a stub for Orion Core. When Core exists, it is replaced, not extended.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from orion.config.settings import Severity
from orion.state.models import (
    MAX_COMMAND_LENGTH,
    AppSnapshot,
    CommandResult,
    ComponentStatus,
    EventRecord,
    StatusKind,
    TaskState,
    TaskSummary,
)

__all__ = ["MockStateProvider"]

MAX_RETAINED_EVENTS = 200


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MockStateProvider:
    """In-memory, deterministic, explicitly simulated state."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or _utc_now
        self._events: list[EventRecord] = []
        self._tasks: list[TaskSummary] = []
        self._event_counter = 0
        self._task_counter = 0

        self._record(
            Severity.INFO,
            "workstation",
            "Orion Workstation started. No Core service, model, or task engine is connected.",
        )

    # -- StateProvider protocol ------------------------------------------

    @property
    def is_mock(self) -> bool:
        return True

    def snapshot(self) -> AppSnapshot:
        return AppSnapshot(
            agent=ComponentStatus(
                component_id="agent",
                label="Resident Agent",
                kind=StatusKind.MOCK,
                detail="Not connected. The resident agent arrives in Phase 4.",
            ),
            model=ComponentStatus(
                component_id="model",
                label="Model Runtime",
                kind=StatusKind.MOCK,
                detail="No model loaded. Model Manager arrives in Phase 3.",
            ),
            tasks=tuple(self._tasks),
            events=tuple(self._events),
            is_mock=True,
        )

    def submit_command(self, text: str, request_id: str) -> CommandResult:
        command = text.strip()
        if not command:
            return CommandResult(
                request_id=request_id,
                accepted=False,
                simulated=True,
                message="Command is empty.",
            )
        if len(command) > MAX_COMMAND_LENGTH:
            return CommandResult(
                request_id=request_id,
                accepted=False,
                simulated=True,
                message=f"Command exceeds {MAX_COMMAND_LENGTH} characters.",
            )

        self._task_counter += 1
        task = TaskSummary(
            task_id=f"sim-{self._task_counter:04d}",
            title=_summarise(command),
            state=TaskState.SIMULATED,
            note="Simulated locally. Nothing was executed.",
        )
        self._tasks.append(task)
        self._record(
            Severity.INFO,
            "composer",
            f"Simulated submission {task.task_id}: {_summarise(command)}",
        )

        return CommandResult(
            request_id=request_id,
            accepted=True,
            simulated=True,
            message=(
                f"Recorded simulated request {task.task_id}. "
                "No agent, model, or tool executed this command."
            ),
        )

    # -- internals --------------------------------------------------------

    def _record(self, severity: Severity, source: str, message: str) -> None:
        self._event_counter += 1
        self._events.append(
            EventRecord(
                event_id=f"evt-{self._event_counter:05d}",
                timestamp=self._clock(),
                severity=severity,
                source=source,
                message=message,
            )
        )
        if len(self._events) > MAX_RETAINED_EVENTS:
            del self._events[: len(self._events) - MAX_RETAINED_EVENTS]


def _summarise(command: str, limit: int = 72) -> str:
    single_line = " ".join(command.split())
    if len(single_line) <= limit:
        return single_line
    return single_line[: limit - 1] + "…"
