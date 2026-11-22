"""Tests for task state machine and basic task manager."""

from __future__ import annotations

import pytest

from orion.tasks import (
    InMemoryTaskRepository,
    TaskManager,
    TaskState,
    TaskStep,
    TaskStepState,
    can_transition_task,
    transition_task,
)
from orion.tasks.models import IdempotencyClass


def _memory_manager() -> TaskManager:
    return TaskManager(repository=InMemoryTaskRepository())


def test_invalid_task_transition_rejected() -> None:
    assert can_transition_task(TaskState.COMPLETED, TaskState.RUNNING) is False
    with pytest.raises(ValueError):
        transition_task(TaskState.COMPLETED, TaskState.RUNNING)


def test_step_transition_rejected() -> None:
    from orion.tasks.state_machine import can_transition_step, transition_step

    assert can_transition_step(TaskStepState.COMPLETED, TaskStepState.RUNNING) is False
    with pytest.raises(ValueError):
        transition_step(TaskStepState.COMPLETED, TaskStepState.RUNNING)


def test_duplicate_request_id_does_not_duplicate_task() -> None:
    tm = _memory_manager()

    obj = tm.create_objective("do something")
    t1 = tm.create_task(obj, title="t", request_id="r1")
    t2 = tm.create_task(obj, title="t", request_id="r1")
    assert t1.task_id == t2.task_id
    assert len(tm.list_tasks()) == 1


def test_cancel_task() -> None:
    tm = _memory_manager()

    obj = tm.create_objective("slow")
    step = TaskStep(capability_id="slow", idempotency=IdempotencyClass.READ_ONLY)
    task = tm.create_task(obj, steps=[step])
    cancelled = tm.cancel_task(task.task_id)
    assert cancelled.state is TaskState.CANCELLED
