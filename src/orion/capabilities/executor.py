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


def _request_resources(value: Any, resource_fields: list[str]) -> list[str]:
    """Resolve every resource from capability-declared argument fields.

    Recognized resource-like keys that are not declared by the capability fail
    closed. This prevents a handler from smuggling a second path through an
    argument that the permission layer did not inspect.
    """
    declared = {field_name.lower() for field_name in resource_fields}
    global_resources = declared == {"*"}
    if global_resources:
        declared.clear()
    resources: set[str] = set()
    found_fields: set[str] = set()

    def visit(item: Any, prefix: str = "") -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    continue
                field_path = f"{prefix}.{key.lower()}" if prefix else key.lower()
                has_declared_child = any(
                    field_name.startswith(field_path + ".") for field_name in declared
                )
                if (
                    key.lower() in _RESOURCE_ARGUMENT_KEYS
                    and field_path not in declared
                    and not has_declared_child
                    and not global_resources
                ):
                    raise ValueError(f"resource field {field_path!r} is not declared by capability")
                if field_path in declared or (
                    global_resources and key.lower() in _RESOURCE_ARGUMENT_KEYS
                ):
                    values = child if isinstance(child, (list, tuple)) else [child]
                    extracted = [
                        str(candidate).strip()
                        for candidate in values
                        if isinstance(candidate, (str, int, float)) and str(candidate).strip()
                    ]
                    if not extracted:
                        raise ValueError(f"declared resource field {field_path!r} is missing")
                    resources.update(extracted)
                    found_fields.add(field_path)
                visit(child, field_path)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child, prefix)

    visit(value)
    missing = declared - found_fields
    if missing:
        raise ValueError(f"declared resource fields are missing: {', '.join(sorted(missing))}")
    if global_resources:
        # A global capability must receive a global grant, never a narrower
        # grant accidentally matched against only one of its inputs.
        return ["*"]
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
        try:
            resources = _request_resources(step_input, capability.resource_fields)
        except ValueError as exc:
            return {
                "success": False,
                "error": str(exc),
                "error_code": "resource_scope_missing",
            }
        scopes = list(capability.required_scopes) or [str(getattr(step, "scope", "") or "")]
        # Medium/high/critical risk requires a gateway decision even when
        # the operation is technically read-only. This prevents a sensitive
        # read from inheriting the unscoped read-only default.
        permission_idempotency = capability.idempotency.value
        if capability.risk.value != "low" or any(resources):
            permission_idempotency = "non_idempotent"
        needs_permission = permission_idempotency != "read_only" or any(scopes)
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
                        idempotency=permission_idempotency,
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
