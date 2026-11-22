"""Delegation manager for Orion."""

from __future__ import annotations

import threading
from collections.abc import Callable

from orion.delegation.models import DelegationPayload, DelegationStatus, DelegationTask
from orion.delegation.provider import DelegationProvider, MockDelegationProvider


class DelegationManager:
    def __init__(self, provider: DelegationProvider | None = None) -> None:
        self.provider = provider or MockDelegationProvider()
        self._tasks: dict[str, DelegationTask] = {}
        self._lock = threading.RLock()

    def submit(
        self, payload: DelegationPayload, *, parent_task_id: str | None = None
    ) -> DelegationTask:
        task = self.provider.submit(payload, parent_task_id=parent_task_id)
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> DelegationTask:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"delegation not found: {task_id}")
            return self._tasks[task_id]

    def list_tasks(self) -> list[DelegationTask]:
        with self._lock:
            return list(self._tasks.values())

    def progress(self, task_id: str) -> DelegationTask:
        self.get(task_id)
        updated = self.provider.progress(task_id)
        with self._lock:
            self._tasks[task_id] = updated
        return updated

    def cancel(self, task_id: str) -> DelegationTask:
        self.get(task_id)
        updated = self.provider.cancel(task_id)
        with self._lock:
            self._tasks[task_id] = updated
        return updated

    def verify_result(
        self, task_id: str, *, verifier: Callable[[DelegationTask], bool] | None = None
    ) -> bool:
        task = self.get(task_id)
        if verifier is not None:
            return verifier(task)
        return task.status is DelegationStatus.COMPLETED and len(task.artifacts) > 0

    def health(self) -> bool:
        return self.provider.health()
