"""Validated task and task-step state transitions."""

from __future__ import annotations

from orion.tasks.models import TaskState, TaskStepState

_TASK_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.CREATED: frozenset({TaskState.PLANNED, TaskState.CANCELLED}),
    TaskState.PLANNED: frozenset({TaskState.RUNNING, TaskState.CANCELLED}),
    TaskState.RUNNING: frozenset(
        {
            TaskState.PAUSED,
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.PARTIAL,
            TaskState.CANCELLED,
        }
    ),
    TaskState.PAUSED: frozenset({TaskState.RUNNING, TaskState.CANCELLED}),
    TaskState.COMPLETED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.CANCELLED: frozenset(),
    TaskState.PARTIAL: frozenset(),
}

_STEP_TRANSITIONS: dict[TaskStepState, frozenset[TaskStepState]] = {
    TaskStepState.PENDING: frozenset(
        {TaskStepState.RUNNING, TaskStepState.SKIPPED, TaskStepState.CANCELLED}
    ),
    TaskStepState.RUNNING: frozenset(
        {TaskStepState.COMPLETED, TaskStepState.FAILED, TaskStepState.CANCELLED}
    ),
    TaskStepState.COMPLETED: frozenset(),
    TaskStepState.FAILED: frozenset(),
    TaskStepState.CANCELLED: frozenset(),
    TaskStepState.SKIPPED: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a state transition is not allowed."""


def can_transition_task(current: TaskState, target: TaskState) -> bool:
    return target in _TASK_TRANSITIONS[current]


def transition_task(current: TaskState, target: TaskState) -> TaskState:
    if not can_transition_task(current, target):
        raise InvalidTransitionError(f"invalid task transition: {current.value} -> {target.value}")
    return target


def can_transition_step(current: TaskStepState, target: TaskStepState) -> bool:
    return target in _STEP_TRANSITIONS[current]


def transition_step(current: TaskStepState, target: TaskStepState) -> TaskStepState:
    if not can_transition_step(current, target):
        raise InvalidTransitionError(f"invalid step transition: {current.value} -> {target.value}")
    return target
