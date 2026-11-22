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
    resource_fields: list[str] = field(default_factory=list)
    risk: RiskLevel = RiskLevel.LOW
    timeout_s: float = 30.0
    supports_cancellation: bool = True
    idempotency: IdempotencyClass = IdempotencyClass.NON_IDEMPOTENT
    handler: Callable[..., Any] | None = None
    available: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.idempotency, str):
            self.idempotency = IdempotencyClass(self.idempotency)
        if isinstance(self.risk, str):
            self.risk = RiskLevel(self.risk)
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be empty")
        if any(not isinstance(scope, str) or not scope.strip() for scope in self.required_scopes):
            raise ValueError("required_scopes must contain non-empty strings")
        if any(
            not isinstance(field_name, str) or not field_name.strip()
            for field_name in self.resource_fields
        ):
            raise ValueError("resource_fields must contain non-empty strings")
        if len(set(self.resource_fields)) != len(self.resource_fields):
            raise ValueError("resource_fields must not contain duplicates")
        if "*" in self.resource_fields and self.resource_fields != ["*"]:
            raise ValueError("global resource selector '*' must be declared alone")
        if (
            self.idempotency is IdempotencyClass.NON_IDEMPOTENT
            and not self.resource_fields
        ):
            raise ValueError(
                "side-effecting capabilities must declare resource_fields or explicit ['*']"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "version": self.version,
            "name": self.name or self.capability_id,
            "description": self.description,
            "required_scopes": list(self.required_scopes),
            "resource_fields": list(self.resource_fields),
            "risk": self.risk.value,
            "timeout_s": self.timeout_s,
            "supports_cancellation": self.supports_cancellation,
            "idempotency": self.idempotency.value,
            "available": self.available,
        }
