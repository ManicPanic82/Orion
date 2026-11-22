"""Delegation domain models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class DelegationStatus(StrEnum):
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class DelegationPayload:
    objective: str = ""
    scope: str = ""
    constraints: list[str] = field(default_factory=list)
    allowed_workspace: str = ""
    expected_artifacts: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    permission_context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "scope": self.scope,
            "constraints": list(self.constraints),
            "allowed_workspace": self.allowed_workspace,
            "expected_artifacts": list(self.expected_artifacts),
            "acceptance_criteria": list(self.acceptance_criteria),
            "permission_context": dict(self.permission_context),
        }


@dataclass(slots=True)
class DelegationTask:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    parent_task_id: str | None = None
    provider_task_id: str = ""
    status: DelegationStatus = DelegationStatus.SUBMITTED
    payload: DelegationPayload = field(default_factory=DelegationPayload)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    result: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "provider_task_id": self.provider_task_id,
            "status": self.status.value,
            "payload": self.payload.as_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": dict(self.result),
            "artifacts": list(self.artifacts),
            "error": self.error,
        }
