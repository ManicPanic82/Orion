"""Core-backed state provider for the Orion Workstation.

Unlike :class:`~orion.mock.state_provider.MockStateProvider` (the Phase 1
shell, which simulates state), this provider reads state from the real Orion
Core services and submits commands through the resident agent. The UI is a
client of the Core; it does not own task execution.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from orion.config.settings import Severity
from orion.core.service import OrionCore
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
from orion.tasks.models import Task, TaskStepState

__all__ = ["CoreStateProvider"]


def _map_task_state(state: Task) -> TaskState:
    try:
        return TaskState(state.state.value)
    except ValueError:
        return TaskState.SIMULATED


def _task_summary(task: Task) -> TaskSummary:
    total = len(task.steps)
    done = sum(1 for step in task.steps if step.state is TaskStepState.COMPLETED)
    notes: list[str] = []
    if total:
        notes.append(f"{done}/{total} steps done")
    if task.result_summary:
        notes.append(task.result_summary)
    return TaskSummary(
        task_id=task.task_id,
        title=task.title or task.task_id[:8],
        state=_map_task_state(task),
        note="; ".join(notes),
    )


class CoreStateProvider:
    """Implements :class:`StateProvider` against the embedded Orion Core."""

    def __init__(self, core: OrionCore | None = None, *, token: str = "") -> None:
        self._core = core or OrionCore(token=token)
        self._events: list[EventRecord] = []
        self._started = False

    # -- StateProvider protocol -------------------------------------------

    @property
    def core(self) -> OrionCore:
        """The embedded Core facade that backs this provider."""
        return self._core

    @property
    def services(self):  # noqa: ANN201 - services.CoreServices
        """The composed Core services (same as ``core.services``)."""
        return self._core.services

    @property
    def is_mock(self) -> bool:
        return False

    def snapshot(self) -> AppSnapshot:
        services = self._core.services
        model_status = services.model_manager.status
        tasks = tuple(_task_summary(t) for t in services.task_manager.list_tasks())
        return AppSnapshot(
            agent=ComponentStatus(
                component_id="agent",
                label="Resident Agent",
                kind=StatusKind.OPERATIONAL,
                detail=("Connected. Objectives plan and execute through the permission gateway."),
            ),
            model=ComponentStatus(
                component_id="model",
                label="Model Runtime",
                kind=StatusKind.OPERATIONAL
                if services.model_manager.is_ready
                else StatusKind.DEGRADED,
                detail=f"{model_status.state.value} — mock host (Phase 3)",
            ),
            tasks=tasks,
            events=tuple(self._events),
            is_mock=False,
        )

    def submit_command(self, text: str, request_id: str) -> CommandResult:
        command = text.strip()
        if not command:
            return CommandResult(
                request_id=request_id,
                accepted=False,
                simulated=False,
                message="Command is empty.",
            )
        if len(command) > MAX_COMMAND_LENGTH:
            return CommandResult(
                request_id=request_id,
                accepted=False,
                simulated=False,
                message=f"Command exceeds {MAX_COMMAND_LENGTH} characters.",
            )
        task = self._core.submit_objective(command, request_id=request_id)
        finished = self._core.run_task(task.task_id)
        return CommandResult(
            request_id=request_id,
            accepted=True,
            simulated=False,
            message=(
                f"Accepted. Objective {task.objective_id} -> task {task.task_id} "
                f"(state: {finished.state.value})."
            ),
        )

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Start the embedded Orion Core (idempotent)."""
        if self._started:
            return
        self._core.start()
        self._started = True
        self._publish_event(
            Severity.INFO, "core", f"Orion Core {self._core.status.version} started (resident)."
        )

    def stop(self) -> None:
        if self._started:
            self._started = False
            self._core.stop()

    # -- internals ---------------------------------------------------------

    def _publish_event(self, severity: Severity, source: str, message: str) -> None:
        self._events.append(
            EventRecord(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(UTC),
                severity=severity,
                source=source,
                message=message,
            )
        )
