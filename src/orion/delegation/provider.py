"""Delegation provider interface and mock."""

from __future__ import annotations

from typing import Protocol

from orion.delegation.models import DelegationPayload, DelegationStatus, DelegationTask


class DelegationProvider(Protocol):
    def submit(
        self, payload: DelegationPayload, *, parent_task_id: str | None = None
    ) -> DelegationTask: ...
    def progress(self, task_id: str) -> DelegationTask: ...
    def cancel(self, task_id: str) -> DelegationTask: ...
    def health(self) -> bool: ...


class MockDelegationProvider:
    def __init__(self, *, fail: bool = False, timeout: bool = False) -> None:
        self.fail = fail
        self.timeout = timeout
        self._tasks: dict[str, DelegationTask] = {}
        self.is_mock = True

    def submit(
        self, payload: DelegationPayload, *, parent_task_id: str | None = None
    ) -> DelegationTask:
        task = DelegationTask(
            parent_task_id=parent_task_id,
            payload=payload,
            provider_task_id=f"mock-{len(self._tasks) + 1}",
        )
        if self.fail:
            task.status = DelegationStatus.FAILED
            task.error = "mock failure"
        elif self.timeout:
            task.status = DelegationStatus.TIMED_OUT
            task.error = "timeout"
        else:
            task.status = DelegationStatus.COMPLETED
            task.result = {"summary": "mock completed"}
            task.artifacts = ["mock_artifact.py"]
        self._tasks[task.task_id] = task
        return task

    def progress(self, task_id: str) -> DelegationTask:
        if task_id not in self._tasks:
            raise KeyError(f"delegation not found: {task_id}")
        return self._tasks[task_id]

    def cancel(self, task_id: str) -> DelegationTask:
        if task_id not in self._tasks:
            raise KeyError(f"delegation not found: {task_id}")
        self._tasks[task_id].status = DelegationStatus.CANCELLED
        return self._tasks[task_id]

    def health(self) -> bool:
        return True
