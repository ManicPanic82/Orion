"""Memory domain models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class MemoryCategory(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    PROCEDURE = "procedure"
    PROJECT = "project"
    OTHER = "other"


class MemorySensitivity(StrEnum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class MemoryState(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DELETED = "deleted"
    EXCLUDED = "excluded"


@dataclass(slots=True)
class MemoryRecord:
    memory_id: str = field(default_factory=lambda: str(uuid4()))
    category: MemoryCategory = MemoryCategory.FACT
    content: str = ""
    provenance: str = ""
    source: str = ""
    scope: str = "global"
    project_id: str | None = None
    confidence: float = 1.0
    sensitivity: MemorySensitivity = MemorySensitivity.NORMAL
    state: MemoryState = MemoryState.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    verified_at: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    superseded_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.valid_until is None:
            return False
        now = now or datetime.now(UTC)
        try:
            return datetime.fromisoformat(self.valid_until) <= now
        except ValueError:
            return False

    def as_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "category": self.category.value,
            "content": self.content,
            "provenance": self.provenance,
            "source": self.source,
            "scope": self.scope,
            "project_id": self.project_id,
            "confidence": self.confidence,
            "sensitivity": self.sensitivity.value,
            "state": self.state.value,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "superseded_by": self.superseded_by,
            "metadata": dict(self.metadata),
        }
