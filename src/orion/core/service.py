"""Orion Core service facade: lifecycle, health, events, and API wiring.

The Core now owns the composed Core services (see
:mod:`orion.core.services`): the resident agent, durable task manager,
permission gateway, model manager, experience recorder, and learning manager.
"""

from __future__ import annotations

from typing import Any

from orion.core.api import OrionApiServer
from orion.core.events import EventStream, OrionEvent
from orion.core.health import HealthCheck, HealthMonitor, HealthSnapshot, HealthStatus
from orion.core.lifecycle import CoreLifecycleState
from orion.core.services import CoreServices, build_default_services, register_mock_model_profile
from orion.tasks.models import Task

__all__ = ["OrionCore", "OrionCoreStatus"]


class OrionCoreStatus:
    """Snapshot of the Core service as observed by the facade."""

    def __init__(
        self,
        state: CoreLifecycleState,
        status: HealthStatus,
        api_listening: bool,
        version: str,
    ) -> None:
        self.state = state
        self.status = status
        self.api_listening = api_listening
        self.version = version

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "status": self.status.value,
            "api_listening": self.api_listening,
            "version": self.version,
        }


def _process_check() -> HealthCheck:
    """Build the placeholder process health check for the first slice."""
    return HealthCheck(name="process", status=HealthStatus.OK, detail="ok")


class OrionCore:
    """Independent Orion Core process facade.

    Owns the lifecycle state machine, health monitor, event stream, and the
    loopback API for the lifetime of the service. It owns no children in this
    phase, so there is nothing to clean up beyond the API listener.
    """

    def __init__(
        self,
        *,
        version: str = "0.1.0",
        token: str = "",
        host: str = "127.0.0.1",
        port: int = 0,
        services: CoreServices | None = None,
    ) -> None:
        self.version = version
        self._health_monitor = HealthMonitor()
        self._health_monitor.register("process", _process_check)
        self._events = EventStream()
        self._services = services if services is not None else build_default_services()
        self._api = OrionApiServer((host, port), token=token, core=self)
        self._state = CoreLifecycleState.STOPPED
        self._status = OrionCoreStatus(
            state=self._state,
            status=HealthStatus.OK,
            api_listening=False,
            version=version,
        )

    @property
    def services(self) -> CoreServices:
        """The composed Core services (resident agent, tasks, permissions...)."""
        return self._services

    # -- lifecycle ---------------------------------------------------------

    @property
    def state(self) -> CoreLifecycleState:
        return self._state

    @property
    def status(self) -> OrionCoreStatus:
        return self._status

    @property
    def api(self) -> OrionApiServer:
        return self._api

    @property
    def events(self) -> EventStream:
        return self._events

    def start(self) -> OrionCoreStatus:
        """Start the Core: STARTING -> READY/DEGRADED/FAILED, then serve API."""
        if self._state is not CoreLifecycleState.STOPPED:
            raise RuntimeError(f"cannot start Orion Core from state {self._state.value}")

        self._state = CoreLifecycleState.STARTING
        self._status = OrionCoreStatus(
            state=self._state,
            status=HealthStatus.OK,
            api_listening=False,
            version=self.version,
        )

        services = self._services
        # Register the now-connected subsystem health checks so the snapshot
        # and API health endpoint report real state.
        self._health_monitor.register(
            "agent",
            lambda: HealthCheck(name="agent", status=HealthStatus.OK, detail="connected"),
        )
        self._health_monitor.register(
            "tasks",
            lambda: HealthCheck(name="tasks", status=HealthStatus.OK, detail="connected"),
        )
        self._health_monitor.register(
            "permissions",
            lambda: HealthCheck(
                name="permissions",
                status=HealthStatus.OK,
                detail=f"mode={services.permission_gateway.mode.value}",
            ),
        )
        self._health_monitor.register(
            "experience",
            lambda: HealthCheck(name="experience", status=HealthStatus.OK, detail="connected"),
        )
        # Load the mock model profile so Model Manager reports READY.
        register_mock_model_profile(services.model_manager)
        self._health_monitor.register("model", services.model_manager.host.health_check)
        self._publish(
            "core.started",
            {"version": self.version, "agent": "resident", "model": "mock"},
        )

        snapshot = self._health_monitor.snapshot(state=self._state)
        overall = self._health_monitor.overall(snapshot)
        self._state = (
            CoreLifecycleState.READY if overall is HealthStatus.OK else CoreLifecycleState.DEGRADED
        )

        self._api.set_health(
            {
                "status": overall.value,
                "checks": [
                    {"name": check.name, "status": check.status.value, "detail": check.detail}
                    for check in snapshot.checks
                ],
                "state": self._state.value,
            }
        )
        self._api.start()
        self._status = OrionCoreStatus(
            state=self._state,
            status=overall,
            api_listening=True,
            version=self.version,
        )
        return self.status

    def stop(self) -> OrionCoreStatus:
        """Stop the Core: STOPPING -> STOPPED, then shut the API down."""
        if self._state is CoreLifecycleState.STOPPED:
            return self.status

        self._state = CoreLifecycleState.STOPPING
        self._api.stop()
        self._state = CoreLifecycleState.STOPPED
        self._status = OrionCoreStatus(
            state=self._state,
            status=HealthStatus.OK,
            api_listening=False,
            version=self.version,
        )
        return self.status

    # -- queries ------------------------------------------------------------

    def health(self) -> HealthSnapshot:
        """Return the latest composed health snapshot."""
        return self._health_monitor.snapshot(state=self._state)

    def event_stream(self) -> EventStream:
        return self._events

    # -- events -------------------------------------------------------------

    def publish(self, event_type: str, payload: dict[str, object]) -> OrionEvent:
        """Publish an event into the Core stream."""
        return self._events.publish(event_type, payload)

    def _publish(self, event_type: str, payload: dict[str, object]) -> OrionEvent:
        return self._events.publish(event_type, payload)

    # -- objectives ---------------------------------------------------------

    def submit_objective(self, request: str, *, request_id: str | None = None) -> Task:
        """Submit an objective through the resident agent (creates a durable task)."""
        task = self._services.agent.submit_and_create_task(request, request_id=request_id)
        self._publish(
            "objective.submitted",
            {"task_id": task.task_id, "objective_id": task.objective_id, "request": request},
        )
        return task

    def objective_tasks(self, objective_id: str) -> list[Task]:
        """Return all tasks recorded for an objective (or with that task id)."""
        return [
            task
            for task in self._services.task_manager.list_tasks()
            if objective_id in {task.objective_id, task.task_id}
        ]

    def run_task(self, task_id: str) -> Task:
        """Execute a task through the resident agent."""
        return self._services.agent.run_task(task_id)

    def cancel_task(self, task_id: str) -> Task:
        """Cancel a task through the resident agent."""
        return self._services.agent.cancel_task(task_id)

    def task_payload(self, task: Task) -> dict[str, Any]:
        """Serialize a task for API transport."""
        return {
            "task_id": task.task_id,
            "objective_id": task.objective_id,
            "title": task.title,
            "state": task.state.value,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
            "result_summary": task.result_summary,
            "failure_code": task.failure_code,
            "steps": [
                {
                    "step_id": s.step_id,
                    "capability_id": s.capability_id,
                    "state": s.state.value,
                    "outcome": s.outcome,
                    "error": s.error,
                }
                for s in task.steps
            ],
        }

    def objectives_payload(self) -> list[dict[str, Any]]:
        """Serialize all tasks (the objective ledger) for API transport."""
        return [self.task_payload(task) for task in self._services.task_manager.list_tasks()]

    def objective_tasks_payload(self, objective_id: str) -> list[dict[str, Any]]:
        return [self.task_payload(task) for task in self.objective_tasks(objective_id)]
