"""Tests for capabilities and executor."""

from __future__ import annotations

from orion.capabilities import CapabilityRegistry, register_mock_capabilities
from orion.capabilities.executor import CapabilityExecutor
from orion.capabilities.permissions import MockPermissionGateway


def test_mock_capabilities_execute() -> None:
    reg = CapabilityRegistry()
    register_mock_capabilities(reg)
    assert "echo" in reg.list_ids()
    executor = CapabilityExecutor(reg, MockPermissionGateway())
    from orion.tasks.models import TaskStep

    step = TaskStep(capability_id="echo", input={"text": "hi"})
    result = executor.execute(step)
    assert result["success"] is True
    assert result["output"]["text"] == "hi"


def test_fail_capability() -> None:
    reg = CapabilityRegistry()
    register_mock_capabilities(reg)
    executor = CapabilityExecutor(reg, MockPermissionGateway())
    from orion.tasks.models import TaskStep

    step = TaskStep(capability_id="fail", input={})
    result = executor.execute(step)
    assert result["success"] is False


def test_permission_denied_for_side_effect_without_gateway() -> None:
    reg = CapabilityRegistry()
    register_mock_capabilities(reg)
    executor = CapabilityExecutor(reg, permission_gateway=None)
    from orion.tasks.models import TaskStep

    step = TaskStep(capability_id="write_file", input={"path": "x"})
    result = executor.execute(step)
    assert result["success"] is False
    assert result["error_code"] == "permission_unavailable"

def test_unclassified_capability_defaults_to_non_idempotent() -> None:
    from orion.capabilities.models import Capability, IdempotencyClass

    capability = Capability(capability_id="custom_side_effect")
    assert capability.idempotency is IdempotencyClass.NON_IDEMPOTENT


def test_required_scope_is_passed_to_permission_gateway() -> None:
    from orion.permissions import AutonomyMode, PermissionDecision, PermissionGateway, PermissionGrant
    from orion.tasks.models import TaskStep

    registry = CapabilityRegistry()
    register_mock_capabilities(registry)
    gateway = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gateway.add_grant(
        PermissionGrant(
            capability_id="write_file",
            action="write_file",
            resource="/workspace/project/*",
            scope="",
        )
    )
    executor = CapabilityExecutor(registry, gateway)
    step = TaskStep(capability_id="write_file", input={"path": "/workspace/project/a.txt"})
    result = executor.execute(step)
    assert result["success"] is False
    assert result["error_code"] == "permission_denied"

    gateway.add_grant(
        PermissionGrant(
            capability_id="write_file",
            action="write_file",
            resource="/workspace/project/*",
            scope="files.write",
        )
    )
    allowed = executor.execute(step)
    assert allowed["success"] is True


def test_side_effecting_capability_without_gateway_is_denied_by_default() -> None:
    from orion.capabilities.models import Capability

    registry = CapabilityRegistry()
    called = []
    registry.register(
        Capability(
            capability_id="custom",
            handler=lambda args, **kwargs: called.append(True),
        )
    )
    result = CapabilityExecutor(registry).execute(
        type("Step", (), {"capability_id": "custom", "input": {}})()
    )
    assert result["success"] is False
    assert result["error_code"] == "permission_unavailable"
    assert called == []
