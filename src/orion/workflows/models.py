"""Workflow/procedure models for Orion capability expansion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ReviewState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"


class TriggerType(StrEnum):
    DAILY = "daily"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    QUIET_HOURS = "quiet_hours"


@dataclass(slots=True)
class Procedure:
    procedure_id: str = field(default_factory=lambda: str(uuid4()))
    version: str = "1"
    name: str = ""
    purpose: str = ""
    preconditions: list[str] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)
    capability_ids: list[str] = field(default_factory=list)
    review_state: ReviewState = ReviewState.PENDING
    enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "version": self.version,
            "name": self.name,
            "purpose": self.purpose,
            "preconditions": list(self.preconditions),
            "steps": list(self.steps),
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "permissions": list(self.permissions),
            "capability_ids": list(self.capability_ids),
            "review_state": self.review_state.value,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }

    def validate(self) -> list[str]:
        problems = []
        if not self.name:
            problems.append("name required")
        if not self.steps:
            problems.append("steps required")
        return problems


@dataclass(slots=True)
class Goal:
    goal_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    success_criteria: list[str] = field(default_factory=list)
    scope: str = ""
    budget_calls: int = 100
    budget_tokens: int = 100000
    budget_seconds: float = 3600.0
    stop_conditions: list[str] = field(default_factory=list)
    schedule: dict[str, Any] = field(default_factory=dict)
    trigger_type: TriggerType = TriggerType.MANUAL
    enabled: bool = True
    last_run_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    permissions: list[str] = field(default_factory=list)
    procedure_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "success_criteria": list(self.success_criteria),
            "scope": self.scope,
            "budget_calls": self.budget_calls,
            "budget_tokens": self.budget_tokens,
            "budget_seconds": self.budget_seconds,
            "stop_conditions": list(self.stop_conditions),
            "schedule": dict(self.schedule),
            "trigger_type": self.trigger_type.value,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at,
            "created_at": self.created_at,
            "permissions": list(self.permissions),
            "procedure_ids": list(self.procedure_ids),
        }


@dataclass(slots=True)
class DailyBriefing:
    briefing_id: str = field(default_factory=lambda: str(uuid4()))
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    items: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "briefing_id": self.briefing_id,
            "generated_at": self.generated_at,
            "items": list(self.items),
        }
