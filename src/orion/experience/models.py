"""Experience/episode domain models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class OutcomeClass(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    CORRECTED = "corrected"
    ABANDONED = "abandoned"
    INCONCLUSIVE = "inconclusive"
    NOT_ELIGIBLE = "not_eligible"


class PrivacyState(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    REDACTED = "redacted"


class QualityState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(slots=True)
class ExperienceAction:
    action_id: str = field(default_factory=lambda: str(uuid4()))
    capability_id: str = ""
    capability_version: str = "1"
    input: dict[str, Any] = field(default_factory=dict)
    attempted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    observed_result: Any = None
    verified_outcome: str = ""
    permission_decision: str = ""

    def as_dict(self, *, redact: bool = False) -> dict[str, Any]:
        data = {
            "action_id": self.action_id,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "input": dict(self.input),
            "attempted_at": self.attempted_at,
            "observed_result": self.observed_result,
            "verified_outcome": self.verified_outcome,
            "permission_decision": self.permission_decision,
        }
        if redact:
            data["input"] = {k: "[REDACTED]" for k in data["input"]}
            data["observed_result"] = "[REDACTED]"
        return data


@dataclass(slots=True)
class ExperienceFeedback:
    feedback_id: str = field(default_factory=lambda: str(uuid4()))
    feedback_type: str = "correction"
    content: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    author: str = "user"

    def as_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "feedback_type": self.feedback_type,
            "content": self.content,
            "created_at": self.created_at,
            "author": self.author,
        }


@dataclass(slots=True)
class Experience:
    experience_id: str = field(default_factory=lambda: str(uuid4()))
    objective_id: str = ""
    task_id: str = ""
    outcome: OutcomeClass = OutcomeClass.INCONCLUSIVE
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    actions: list[ExperienceAction] = field(default_factory=list)
    feedback: list[ExperienceFeedback] = field(default_factory=list)
    privacy_state: PrivacyState = PrivacyState.PENDING
    quality_state: QualityState = QualityState.PENDING
    eligible_for_training: bool = False
    excluded: bool = False
    redacted_fields: list[str] = field(default_factory=list)
    scope: str = "global"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self, *, redact: bool = False) -> dict[str, Any]:
        data = {
            "experience_id": self.experience_id,
            "objective_id": self.objective_id,
            "task_id": self.task_id,
            "outcome": self.outcome.value,
            "created_at": self.created_at,
            "actions": [a.as_dict(redact=redact) for a in self.actions],
            "feedback": [
                {
                    **f.as_dict(),
                    "content": (
                        "[REDACTED]"
                        if redact and ("content" in self.redacted_fields or "feedback" in self.redacted_fields)
                        else f.content
                    ),
                }
                for f in self.feedback
            ],
            "privacy_state": self.privacy_state.value,
            "quality_state": self.quality_state.value,
            "eligible_for_training": self.eligible_for_training,
            "excluded": self.excluded,
            "redacted_fields": list(self.redacted_fields),
            "scope": self.scope,
            "metadata": dict(self.metadata),
        }
        if redact:
            for field_name in self.redacted_fields:
                if field_name in data:
                    data[field_name] = "[REDACTED]"
                metadata = data.get("metadata")
                if isinstance(metadata, dict) and field_name in metadata:
                    metadata[field_name] = "[REDACTED]"
        return data
