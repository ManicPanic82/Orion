"""Capability executor for Orion."""

from __future__ import annotations

import threading
from typing import Any

from orion.capabilities.permissions import PermissionDecision, PermissionGateway
from orion.capabilities.registry import CapabilityRegistry


_RESOURCE_ARGUMENT_KEYS = frozenset(
    {
        "resource",
        "path",
        "file_path",
        "target",
        "source",
        "destination",
        "directory",
        "working_dir",
        "cwd",
        "filename",
        "file",
        "paths",
        "files",
        "source_path",
        "destination_path",
        "url",
    }
)


def _request_resources(value: Any) -> list[str]:
    """Collect every declared resource path from nested capability arguments."""
    resources: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if isinstance(key, str) and key.lower() in _RESOURCE_ARGUMENT_KEYS:
                    values = child if isinstance(child, (list, tuple)) else [child]
                    for candidate in values:
                        if isinstance(candidate, (str, int, float)):
                            resource = str(candidate).strip()
                            if resource:
                                resources.add(resource)
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)
    return sorted(resources) or [""]


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

        # Resolve request context from the structured step, never from the
        # planner's claimed idempotency value. Capability metadata is trusted
        # application configuration; step input is request data.
        step_input = dict(getattr(step, "input", {}) or {})
        resources = _request_resources(step_input)
        scopes = list(capability.required_scopes) or [str(getattr(step, "scope", "") or "")]
        needs_permission = (
            capability.idempotency.value != "read_only"
            or any(scopes)
        )
        if needs_permission:
            gateway = self.permission_gateway
            if gateway is None:
                return {
                    "success": False,
                    "error": "permission gateway unavailable",
                    "error_code": "permission_unavailable",
                }
            for scope in scopes:
                for resource in resources:
                    decision = gateway.decide(
                        capability_id,
                        resource=resource,
                        action=str(getattr(step, "action", "") or capability_id),
                        scope=scope,
                        risk=capability.risk.value,
                        task_id=getattr(step, "task_id", None),
                        step_id=getattr(step, "step_id", ""),
                        idempotency=capability.idempotency.value,
                        args=step_input,
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
            return {"success": True, "output": {"echo": getattr(step, "input", {})}, "error": None}

        try:
            output = handler(dict(getattr(step, "input", {}) or {}), cancel_event=cancel_event)
            return {"success": True, "output": output, "error": None}
        except Exception as exc:
            return {"success": False, "error": str(exc), "error_code": "execution_failed"}
