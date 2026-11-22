"""Health reporting for Orion Core.

A health snapshot is a composed answer over named checks. It never fabricates a
green result: if a check has not run or failed, the snapshot says so honestly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from orion.core.lifecycle import CoreLifecycleState

__all__ = ["HealthCheck", "HealthSnapshot", "HealthStatus", "HealthMonitor"]


class HealthStatus(StrEnum):
    """Outcome of a single health check."""

    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class HealthCheck:
    """One named, individually scored health fact."""

    name: str
    status: HealthStatus
    detail: str = ""
    latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    """The composed answer for the Core process."""

    state: CoreLifecycleState | None = None
    checks: tuple[HealthCheck, ...] = ()

    @property
    def ok(self) -> bool:
        return all(check.status is HealthStatus.OK for check in self.checks)

    @property
    def degraded(self) -> bool:
        return any(check.status is HealthStatus.DEGRADED for check in self.checks)

    @property
    def failed(self) -> bool:
        return any(check.status is HealthStatus.FAILED for check in self.checks)


CheckFn = Callable[[], HealthCheck]


class HealthMonitor:
    """Runs named checks and composes health snapshots."""

    def __init__(self) -> None:
        self._checks: dict[str, CheckFn] = {}

    def register(self, name: str, check: CheckFn) -> None:
        """Register a named check. Later registrations replace earlier ones."""
        self._checks[name] = check

    def clear(self, name: str) -> None:
        """Remove a check; clearing does not fail health on its own."""
        self._checks.pop(name, None)

    def snapshot(self, *, state: CoreLifecycleState | None = None) -> HealthSnapshot:
        """Run all registered checks and compose the snapshot."""
        checks = tuple(self._checks[name]() for name in sorted(self._checks))
        return HealthSnapshot(state=state, checks=checks)

    def overall(self, snapshot: HealthSnapshot) -> HealthStatus:
        """Derive the overall status from the composed checks."""
        if snapshot.failed:
            return HealthStatus.FAILED
        if snapshot.degraded:
            return HealthStatus.DEGRADED
        return HealthStatus.OK
