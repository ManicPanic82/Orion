"""Permission gateway interface used by the capability executor.

The capability framework uses the same gateway contract as
:mod:`orion.permissions`: :meth:`PermissionGateway.decide` returns a
:class:`~orion.permissions.models.PolicyDecision`, and the enum is shared
through :data:`PermissionDecision` so both sides can never disagree.
"""

from __future__ import annotations

from typing import Any, Protocol

from orion.permissions.models import PermissionDecision, PolicyDecision

__all__ = ["MockPermissionGateway", "PermissionDecision", "PermissionGateway"]


class PermissionGateway(Protocol):
    def decide(
        self,
        capability_id: str,
        resource: str = "",
        *,
        action: str = "",
        scope: str = "",
        risk: str = "medium",
        task_id: str | None = None,
        step_id: str | None = None,
        args: dict[str, Any] | None = None,
        approval_id: str | None = None,
        idempotency: str = "non_idempotent",
        mode: Any = None,
        autonomy_mode: Any = None,
    ) -> PolicyDecision: ...


class MockPermissionGateway:
    """Explicitly permissive mock gateway for Phase 4.

    Labelled as a mock in every path (``is_mock``); it must never be presented
    as the real permission system.
    """

    def decide(
        self,
        capability_id: str,
        resource: str = "",
        *,
        action: str = "",
        scope: str = "",
        risk: str = "medium",
        task_id: str | None = None,
        step_id: str | None = None,
        args: dict[str, Any] | None = None,
        approval_id: str | None = None,
        idempotency: str = "non_idempotent",
        mode: Any = None,
        autonomy_mode: Any = None,
    ) -> PolicyDecision:
        return PolicyDecision(decision=PermissionDecision.ALLOW, rationale_code="mock_permit")

    @property
    def is_mock(self) -> bool:
        return True
