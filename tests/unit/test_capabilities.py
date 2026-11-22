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
