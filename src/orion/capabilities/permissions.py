"""Permission gateway interface used by the capability executor."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol


class PermissionDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PermissionGateway(Protocol):
    def decide(
        self, capability_id: str, resource: str = "", context: dict[str, Any] | None = None
    ) -> PermissionDecision: ...


class MockPermissionGateway:
    """Explicitly permissive mock gateway for Phase 4."""

    def decide(
        self, capability_id: str, resource: str = "", context: dict[str, Any] | None = None
    ) -> PermissionDecision:
        return PermissionDecision.ALLOW

    @property
    def is_mock(self) -> bool:
        return True
