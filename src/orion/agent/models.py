"""Agent-level planning and verification models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class PlannedStep:
    step_id: str = field(default_factory=lambda: str(uuid4()))
    capability_id: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    idempotency: str = "read_only"
    timeout_s: float = 30.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "capability_id": self.capability_id,
            "input": dict(self.input),
            "expected_outcome": self.expected_outcome,
            "idempotency": self.idempotency,
            "timeout_s": self.timeout_s,
        }


@dataclass(slots=True)
class VerificationResult:
    success: bool = False
    outcome: str = "inconclusive"  # success, partial, failure, inconclusive
    details: str = ""
    evidence: list[Any] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "outcome": self.outcome,
            "details": self.details,
            "evidence": list(self.evidence),
        }
