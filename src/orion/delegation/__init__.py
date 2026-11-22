"""Main-agent delegation for Orion."""

from orion.delegation.manager import DelegationManager
from orion.delegation.models import DelegationPayload, DelegationStatus, DelegationTask
from orion.delegation.provider import DelegationProvider, MockDelegationProvider

__all__ = [
    "DelegationManager",
    "DelegationPayload",
    "DelegationProvider",
    "DelegationStatus",
    "DelegationTask",
    "MockDelegationProvider",
]
# Aliases
DelegationEngine = DelegationManager
