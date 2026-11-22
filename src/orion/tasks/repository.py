"""Task repositories."""

from __future__ import annotations

from orion.tasks.models import Task


class TaskRepository:
    def save(self, task: Task) -> None: ...
    def get(self, task_id: str) -> Task: ...
    def list(self) -> list[Task]: ...
    def delete(self, task_id: str) -> None: ...


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def save(self, task: Task) -> None:
        self._tasks[task.task_id] = task

    def get(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise KeyError(f"task not found: {task_id}")
        return self._tasks[task_id]

    def list(self) -> list[Task]:
        return list(self._tasks.values())

    def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    def clear(self) -> None:
        self._tasks.clear()
