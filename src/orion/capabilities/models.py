"""Capability contracts for Orion."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IdempotencyClass(StrEnum):
    READ_ONLY = "read_only"
    IDEMPOTENT = "idempotent"
    NON_IDEMPOTENT = "non_idempotent"


@dataclass(slots=True)
class Capability:
    capability_id: str
    version: str = "1"
    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    required_scopes: list[str] = field(default_factory=list)
    risk: RiskLevel = RiskLevel.LOW
    timeout_s: float = 30.0
    supports_cancellation: bool = True
    idempotency: IdempotencyClass = IdempotencyClass.NON_IDEMPOTENT
    handler: Callable[..., Any] | None = None
    available: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "version": self.version,
            "name": self.name or self.capability_id,
            "description": self.description,
            "required_scopes": list(self.required_scopes),
            "risk": self.risk.value,
            "timeout_s": self.timeout_s,
            "supports_cancellation": self.supports_cancellation,
            "idempotency": self.idempotency.value,
            "available": self.available,
        }
