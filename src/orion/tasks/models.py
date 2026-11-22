"""Task and objective domain models for Orion's resident agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskState(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"

    # Aliases used by some callers.
    PENDING = "created"
    DONE = "completed"


class TaskStepState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class IdempotencyClass(StrEnum):
    READ_ONLY = "read_only"
    IDEMPOTENT = "idempotent"
    NON_IDEMPOTENT = "non_idempotent"


class ObjectiveState(StrEnum):
    RECEIVED = "received"
    PLANNED = "planned"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Objective:
    objective_id: str = field(default_factory=lambda: str(uuid4()))
    request: str = ""
    state: ObjectiveState = ObjectiveState.RECEIVED
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "request": self.request,
            "state": self.state.value,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class TaskStep:
    step_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    sequence: int = 0
    capability_id: str = ""
    capability_version: str = "1"
    input: dict[str, Any] = field(default_factory=dict)
    state: TaskStepState = TaskStepState.PENDING
    idempotency: IdempotencyClass = IdempotencyClass.READ_ONLY
    permission_decision: str = "not_evaluated"
    started_at: str | None = None
    ended_at: str | None = None
    outcome: str = ""
    output: Any = None
    output_ref: str | None = None
    error: str | None = None
    retry_count: int = 0
    timeout_s: float = 30.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "task_id": self.task_id,
            "sequence": self.sequence,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "input": dict(self.input),
            "state": self.state.value,
            "idempotency": self.idempotency.value,
            "permission_decision": self.permission_decision,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "outcome": self.outcome,
            "output": self.output,
            "output_ref": self.output_ref,
            "error": self.error,
            "retry_count": self.retry_count,
            "timeout_s": self.timeout_s,
        }


@dataclass(slots=True)
class Task:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    objective_id: str = ""
    title: str = ""
    state: TaskState = TaskState.CREATED
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    steps: list[TaskStep] = field(default_factory=list)
    current_step: int = 0
    checkpoint: str = ""
    result_summary: str = ""
    failure_code: str | None = None
    request_id: str | None = None
    recovery_safe: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective_id": self.objective_id,
            "title": self.title,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "steps": [s.as_dict() for s in self.steps],
            "current_step": self.current_step,
            "checkpoint": self.checkpoint,
            "result_summary": self.result_summary,
            "failure_code": self.failure_code,
            "request_id": self.request_id,
            "recovery_safe": self.recovery_safe,
        }
