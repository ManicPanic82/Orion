"""Permission gateway and autonomy for Orion."""

from orion.permissions.gateway import PermissionGateway
from orion.permissions.models import (
    POLICY_VERSION,
    ApprovalRequest,
    ApprovalStatus,
    AuditRecord,
    AutonomyMode,
    PermissionDecision,
    PermissionGrant,
    PolicyDecision,
)

__all__ = [
    "POLICY_VERSION",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditRecord",
    "AutonomyMode",
    "PermissionDecision",
    "PermissionGateway",
    "PermissionGrant",
    "PolicyDecision",
]
# Aliases
PermissionEngine = PermissionGateway
AutonomyLevel = AutonomyMode
