"""Orion Core service facade: lifecycle, health, events, and API wiring."""

from __future__ import annotations

from orion.core.api import OrionApiServer
from orion.core.events import EventStream, OrionEvent
from orion.core.health import HealthCheck, HealthMonitor, HealthSnapshot, HealthStatus
from orion.core.lifecycle import CoreLifecycleState

__all__ = ["OrionCore", "OrionCoreStatus"]


class OrionCoreStatus:
    """Snapshot of the Core service as observed by the facade."""

    def __init__(
        self,
        state: CoreLifecycleState,
        status: HealthStatus,
        api_listening: bool,
        version: str,
    ) -> None:
        self.state = state
        self.status = status
        self.api_listening = api_listening
        self.version = version

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "status": self.status.value,
            "api_listening": self.api_listening,
            "version": self.version,
        }


def _process_check() -> HealthCheck:
    """Build the placeholder process health check for the first slice."""
    return HealthCheck(name="process", status=HealthStatus.OK, detail="ok")


class OrionCore:
    """Independent Orion Core process facade.

    Owns the lifecycle state machine, health monitor, event stream, and the
    loopback API for the lifetime of the service. It owns no children in this
    phase, so there is nothing to clean up beyond the API listener.
    """

    def __init__(
        self,
        *,
        version: str = "0.1.0",
        token: str = "",
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.version = version
        self._health_monitor = HealthMonitor()
        self._health_monitor.register("process", _process_check)
        self._events = EventStream()
        self._api = OrionApiServer((host, port), token=token)
        self._state = CoreLifecycleState.STOPPED
        self._status = OrionCoreStatus(
            state=self._state,
            status=HealthStatus.OK,
            api_listening=False,
            version=version,
        )

    # -- lifecycle ---------------------------------------------------------

    @property
    def state(self) -> CoreLifecycleState:
        return self._state

    @property
    def status(self) -> OrionCoreStatus:
        return self._status

    @property
    def api(self) -> OrionApiServer:
        return self._api

    @property
    def events(self) -> EventStream:
        return self._events

    def start(self) -> OrionCoreStatus:
        """Start the Core: STARTING -> READY/DEGRADED/FAILED, then serve API."""
        if self._state is not CoreLifecycleState.STOPPED:
            raise RuntimeError(f"cannot start Orion Core from state {self._state.value}")

        self._state = CoreLifecycleState.STARTING
        self._status = OrionCoreStatus(
            state=self._state,
            status=HealthStatus.OK,
            api_listening=False,
            version=self.version,
        )

        snapshot = self._health_monitor.snapshot(state=self._state)
        overall = self._health_monitor.overall(snapshot)
        self._state = (
            CoreLifecycleState.READY if overall is HealthStatus.OK else CoreLifecycleState.DEGRADED
        )

        self._api.set_health(
            {
                "status": overall.value,
                "checks": [
                    {"name": check.name, "status": check.status.value, "detail": check.detail}
                    for check in snapshot.checks
                ],
                "state": self._state.value,
            }
        )
        self._api.start()
        self._status = OrionCoreStatus(
            state=self._state,
            status=overall,
            api_listening=True,
            version=self.version,
        )
        return self.status

    def stop(self) -> OrionCoreStatus:
        """Stop the Core: STOPPING -> STOPPED, then shut the API down."""
        if self._state is CoreLifecycleState.STOPPED:
            return self.status

        self._state = CoreLifecycleState.STOPPING
        self._api.stop()
        self._state = CoreLifecycleState.STOPPED
        self._status = OrionCoreStatus(
            state=self._state,
            status=HealthStatus.OK,
            api_listening=False,
            version=self.version,
        )
        return self.status

    # -- queries ------------------------------------------------------------

    def health(self) -> HealthSnapshot:
        """Return the latest composed health snapshot."""
        return self._health_monitor.snapshot(state=self._state)

    def event_stream(self) -> EventStream:
        return self._events

    # -- events -------------------------------------------------------------

    def publish(self, event_type: str, payload: dict[str, object]) -> OrionEvent:
        """Publish an event into the Core stream."""
        return self._events.publish(event_type, payload)
