"""Orion Core: the UI-independent background process.

Phase 2 introduced the Core as a process of its own. This package holds the
Core-side contracts and implementation: lifecycle, health, events, API,
supervisor, the service facade, and the composed ``CoreServices`` (resident
agent, tasks, permissions, model manager, experience recorder, learning
manager) that the Workstation embeds.
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
