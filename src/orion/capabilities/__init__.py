"""Capability framework for Orion."""

from orion.capabilities.executor import CapabilityExecutor
from orion.capabilities.mock import register_mock_capabilities
from orion.capabilities.models import Capability, IdempotencyClass, RiskLevel
from orion.capabilities.permissions import (
    MockPermissionGateway,
    PermissionDecision,
    PermissionGateway,
)
from orion.capabilities.registry import CapabilityRegistry

__all__ = [
    "Capability",
    "CapabilityExecutor",
    "CapabilityRegistry",
    "IdempotencyClass",
    "MockPermissionGateway",
    "PermissionDecision",
    "PermissionGateway",
    "RiskLevel",
    "register_mock_capabilities",
]
# Aliases
CapabilityEngine = CapabilityRegistry
