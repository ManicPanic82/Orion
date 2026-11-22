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

        args = dict(getattr(step, "input", {}) or {})
        # Required scopes are application-owned capability metadata. A single
        # scope maps directly to the gateway's scope field; combinations are
        # rejected until the gateway supports an explicit multi-scope contract.
        required_scopes = tuple(capability.required_scopes)
        if len(required_scopes) > 1:
            return {
                "success": False,
                "error": "capability declares multiple unsupported permission scopes",
                "error_code": "unsupported_permission_scopes",
            }
        scope = required_scopes[0] if required_scopes else str(getattr(step, "scope", "") or "")
        resource = str(args.get("resource") or args.get("path") or "")
        idempotency = capability.idempotency.value

        # Only capabilities explicitly registered by application code as
        # READ_ONLY may bypass the gateway. The default classification is
        # NON_IDEMPOTENT, never read-only.
        if idempotency != "read_only":
            gateway = self.permission_gateway
            if gateway is None:
                return {
                    "success": False,
                    "error": "permission gateway unavailable",
                    "error_code": "permission_unavailable",
                }
            decision = gateway.decide(
                capability_id,
                resource=resource,
                action=capability_id,
                scope=scope,
                risk=capability.risk.value,
                task_id=getattr(step, "task_id", None) or None,
                step_id=getattr(step, "step_id", "") or None,
                args=args,
                idempotency=idempotency,
            )
            if decision.decision is not PermissionDecision.ALLOW:
                return {
                    "success": False,
                    "error": f"permission {decision.decision.value}",
                    "error_code": "permission_denied",
                }

        if cancel_event is not None and cancel_event.is_set():
            return {"success": False, "error": "cancelled", "error_code": "cancelled"}

        handler = capability.handler
        if handler is None:
            return {"success": True, "output": {"echo": args}, "error": None}

        try:
            output = handler(args, cancel_event=cancel_event)
            return {"success": True, "output": output, "error": None}
        except Exception as exc:
            return {"success": False, "error": str(exc), "error_code": "execution_failed"}
