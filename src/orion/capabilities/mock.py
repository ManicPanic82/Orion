"""Mock capabilities for Phase 4."""

from __future__ import annotations

import time
from typing import Any

from orion.capabilities.models import Capability, IdempotencyClass, RiskLevel


def echo_handler(inp: dict[str, Any], *, cancel_event: Any = None) -> dict[str, Any]:
    return {"text": inp.get("text", "")}


def sum_handler(inp: dict[str, Any], *, cancel_event: Any = None) -> dict[str, Any]:
    values = inp.get("values", [])
    return {"total": sum(values)}


def fail_handler(inp: dict[str, Any], *, cancel_event: Any = None) -> dict[str, Any]:
    raise RuntimeError("mock capability failure")


def slow_handler(inp: dict[str, Any], *, cancel_event: Any = None) -> dict[str, Any]:
    for _ in range(10):
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("cancelled")
        time.sleep(0.05)
    return {"done": True}


def write_handler(inp: dict[str, Any], *, cancel_event: Any = None) -> dict[str, Any]:
    # Side-effecting mock: does not touch the real filesystem.
    return {"written": inp.get("path", ""), "content": inp.get("content", "")}


def register_mock_capabilities(registry: Any) -> None:
    registry.register(
        Capability(
            capability_id="echo",
            name="Echo",
            handler=echo_handler,
            idempotency=IdempotencyClass.READ_ONLY,
        )
    )
    registry.register(
        Capability(
            capability_id="sum",
            name="Sum",
            handler=sum_handler,
            idempotency=IdempotencyClass.READ_ONLY,
        )
    )
    registry.register(
        Capability(
            capability_id="fail",
            name="Fail",
            handler=fail_handler,
            idempotency=IdempotencyClass.READ_ONLY,
        )
    )
    registry.register(
        Capability(
            capability_id="slow",
            name="Slow",
            handler=slow_handler,
            idempotency=IdempotencyClass.READ_ONLY,
            timeout_s=1.0,
        )
    )
    registry.register(
        Capability(
            capability_id="write_file",
            name="Write File (mock)",
            handler=write_handler,
            idempotency=IdempotencyClass.NON_IDEMPOTENT,
            risk=RiskLevel.HIGH,
            required_scopes=["files.write"],
            resource_fields=["path"],
        )
    )
