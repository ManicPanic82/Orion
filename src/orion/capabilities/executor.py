"""Capability executor for Orion."""

from __future__ import annotations

import threading
from typing import Any

from orion.capabilities.permissions import PermissionDecision, PermissionGateway
from orion.capabilities.registry import CapabilityRegistry


class CapabilityExecutor:
    def __init__(
        self,
        registry: CapabilityRegistry,
        permission_gateway: PermissionGateway | None = None,
    ) -> None:
        self.registry = registry
        self.permission_gateway = permission_gateway

    def execute(self, step: Any, *, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        capability_id = getattr(step, "capability_id", "")
        try:
            capability = self.registry.get(capability_id)
        except KeyError as exc:
            return {"success": False, "error": str(exc), "error_code": "unknown_capability"}

        if not capability.available:
            return {
                "success": False,
                "error": f"capability unavailable: {capability_id}",
                "error_code": "unavailable",
            }

        # Permission check for side-effecting capabilities.
        if capability.idempotency.value != "read_only":
            gateway = self.permission_gateway
            if gateway is None:
                return {
                    "success": False,
                    "error": "permission gateway unavailable",
                    "error_code": "permission_unavailable",
                }
            decision = gateway.decide(
                capability_id, resource="", context={"step": getattr(step, "step_id", "")}
            )
            if decision is not PermissionDecision.ALLOW:
                return {
                    "success": False,
                    "error": f"permission {decision.value}",
                    "error_code": "permission_denied",
                }

        if cancel_event is not None and cancel_event.is_set():
            return {"success": False, "error": "cancelled", "error_code": "cancelled"}

        handler = capability.handler
        if handler is None:
            return {"success": True, "output": {"echo": getattr(step, "input", {})}, "error": None}

        try:
            output = handler(dict(getattr(step, "input", {}) or {}), cancel_event=cancel_event)
            return {"success": True, "output": output, "error": None}
        except Exception as exc:
            return {"success": False, "error": str(exc), "error_code": "execution_failed"}
