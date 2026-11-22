"""Task manager for Orion's resident agent."""

from __future__ import annotations

import datetime
import threading
from pathlib import Path
from typing import Any

from orion.config.paths import app_data_dir
from orion.core.events import EventStream
from orion.tasks.models import IdempotencyClass, Objective, Task, TaskState, TaskStep, TaskStepState
from orion.tasks.repository import SQLiteTaskRepository, TaskRepository
from orion.tasks.state_machine import transition_step, transition_task


class TaskManager:
    def __init__(
        self,
        repository: TaskRepository | None = None,
        events: EventStream | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        # Durable by default: task history survives process restarts.
        self._repository = repository or SQLiteTaskRepository(
            db_path if db_path is not None else app_data_dir() / "orion.db"
        )
        self._events = events or EventStream()
        self._request_index: dict[str, str] = {}  # request_id -> task_id
        self._cancellations: dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    @property
    def events(self) -> EventStream:
        return self._events

    def create_objective(
        self, request: str, *, metadata: dict[str, Any] | None = None
    ) -> Objective:
        return Objective(request=request, metadata=dict(metadata or {}))

    def create_task(
        self,
        objective: Objective,
        *,
        title: str = "",
        steps: list[TaskStep] | None = None,
        request_id: str | None = None,
    ) -> Task:
        with self._lock:
            if request_id is not None and request_id in self._request_index:
                return self._repository.get(self._request_index[request_id])

            task = Task(
                objective_id=objective.objective_id,
                title=title or objective.request[:80],
                request_id=request_id,
            )
            for step in steps or []:
                step.task_id = task.task_id
                task.steps.append(step)
            if task.steps:
                task.state = transition_task(task.state, TaskState.PLANNED)
            self._repository.save(task)
            if request_id is not None:
                self._request_index[request_id] = task.task_id
            self._cancellations[task.task_id] = threading.Event()
            self._events.publish(
                "task.created", {"task_id": task.task_id, "objective_id": objective.objective_id}
            )
            return task

    def get_task(self, task_id: str) -> Task:
        return self._repository.get(task_id)

    def list_tasks(self) -> list[Task]:
        return self._repository.list()

    def cancel_task(self, task_id: str) -> Task:
        with self._lock:
            task = self._repository.get(task_id)
            if task.state in {
                TaskState.COMPLETED,
                TaskState.FAILED,
                TaskState.CANCELLED,
                TaskState.PARTIAL,
            }:
                return task
            event = self._cancellations.setdefault(task_id, threading.Event())
            event.set()
            # Cancel pending steps.
            for step in task.steps:
                if step.state is TaskStepState.PENDING:
                    step.state = transition_step(step.state, TaskStepState.CANCELLED)
            if task.state in {
                TaskState.CREATED,
                TaskState.PLANNED,
                TaskState.PAUSED,
                TaskState.RUNNING,
            }:
                task.state = transition_task(task.state, TaskState.CANCELLED)
            task.finished_at = task.finished_at or datetime.datetime.now(datetime.UTC).isoformat()
            self._repository.save(task)
            self._events.publish("task.cancelled", {"task_id": task_id})
            return task

    def cancellation_event(self, task_id: str) -> threading.Event:
        return self._cancellations.setdefault(task_id, threading.Event())

    def update_step(self, task_id: str, step_id: str, **changes: Any) -> TaskStep:
        with self._lock:
            task = self._repository.get(task_id)
            for step in task.steps:
                if step.step_id == step_id:
                    for key, value in changes.items():
                        setattr(step, key, value)
                    self._repository.save(task)
                    return step
            raise KeyError(f"step not found: {step_id}")

    def transition_task_state(self, task_id: str, target: TaskState) -> Task:
        with self._lock:
            task = self._repository.get(task_id)
            task.state = transition_task(task.state, target)
            self._repository.save(task)
            return task

    def update_task(self, task_id: str, **changes: Any) -> Task:
        """Persist arbitrary task field changes via the manager API.

        Used by callers that hold only a task snapshot: mutations are applied
        to the current repository state and saved, so snapshot staleness can
        not clobber concurrent transitions.
        """
        with self._lock:
            task = self._repository.get(task_id)
            for key, value in changes.items():
                setattr(task, key, value)
            self._repository.save(task)
            return task

    def transition_step_state(self, task_id: str, step_id: str, target: TaskStepState) -> TaskStep:
        with self._lock:
            task = self._repository.get(task_id)
            for step in task.steps:
                if step.step_id == step_id:
                    step.state = transition_step(step.state, target)
                    self._repository.save(task)
                    return step
            raise KeyError(f"step not found: {step_id}")

    def checkpoint(self, task_id: str, value: str) -> Task:
        with self._lock:
            task = self._repository.get(task_id)
            task.checkpoint = value
            self._repository.save(task)
            return task

    def recover_task(self, task_id: str) -> Task:
        task = self._repository.get(task_id)
        # Only resume if recovery_safe and no non-idempotent ambiguity.
        if not task.recovery_safe:
            return task
        # Reset running steps to pending for safe/idempotent steps.
        for step in task.steps:
            if step.state is TaskStepState.RUNNING:
                if step.idempotency in {IdempotencyClass.READ_ONLY, IdempotencyClass.IDEMPOTENT}:
                    step.state = TaskStepState.PENDING
                else:
                    task.recovery_safe = False
        if task.recovery_safe and task.state in {TaskState.RUNNING, TaskState.PAUSED}:
            task.state = TaskState.PAUSED
        self._repository.save(task)
        return task
