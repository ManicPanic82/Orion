"""Orion Core: the UI-independent background process.

Phase 2 introduces the Core as a process of its own. The UI (Phase 1 shell) is a
client of the state seam introduced in Phase 1; this package holds the Core-side
contracts and the first slice of implementation: lifecycle, health, events, API,
supervisor, and the service facade.
"""

from orion.core.api import (
    ALLOWED_PATHS,
    HEALTH_PATH,
    HOST,
    MAX_BODY_BYTES,
    ApiError,
    OrionApiServer,
)
from orion.core.events import EventStream, OrionEvent
from orion.core.health import HealthCheck, HealthMonitor, HealthSnapshot, HealthStatus
from orion.core.lifecycle import CoreLifecycleState, LifecycleError, transition
from orion.core.service import OrionCore, OrionCoreStatus
from orion.core.supervisor import CoreSupervisor, RestartPolicy

__all__ = [
    "ALLOWED_PATHS",
    "HEALTH_PATH",
    "HOST",
    "MAX_BODY_BYTES",
    "ApiError",
    "CoreLifecycleState",
    "CoreSupervisor",
    "EventStream",
    "HealthCheck",
    "HealthMonitor",
    "HealthSnapshot",
    "HealthStatus",
    "LifecycleError",
    "OrionApiServer",
    "OrionCore",
    "OrionCoreStatus",
    "OrionEvent",
    "RestartPolicy",
    "transition",
]
