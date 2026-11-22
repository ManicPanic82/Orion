"""Task engine for Orion."""

from orion.tasks.manager import TaskManager
from orion.tasks.models import (
    IdempotencyClass,
    Objective,
    ObjectiveState,
    Task,
    TaskState,
    TaskStep,
    TaskStepState,
)
from orion.tasks.repository import InMemoryTaskRepository, SQLiteTaskRepository, TaskRepository
from orion.tasks.state_machine import (
    InvalidTransitionError,
    can_transition_step,
    can_transition_task,
    transition_step,
    transition_task,
)

__all__ = [
    "IdempotencyClass",
    "InMemoryTaskRepository",
    "InvalidTransitionError",
    "Objective",
    "ObjectiveState",
    "SQLiteTaskRepository",
    "Task",
    "TaskManager",
    "TaskRepository",
    "TaskState",
    "TaskStep",
    "TaskStepState",
    "can_transition_step",
    "can_transition_task",
    "transition_step",
    "transition_task",
]
# Aliases
TaskEngine = TaskManager
TaskManagerAlias = TaskManager
