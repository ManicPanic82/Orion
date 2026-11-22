"""Orion Core event stream.

Events carry a stable ``event_id`` and a monotonic ``sequence``. Delivery is
treated as at-least-once: consumers tolerate duplicates, and republishing the
same ``event_id`` is a no-op for listeners.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

__all__ = ["EventStream", "OrionEvent"]


@dataclass(frozen=True, slots=True)
class OrionEvent:
    """A single Orion Core event."""

    event_id: str
    sequence: int
    type: str
    payload: dict[str, object]
    timestamp: datetime


EventListener = Callable[[OrionEvent], None]


class EventStream:
    """Sequence-assigned, duplicate-tolerant event stream."""

    def __init__(self) -> None:
        self._sequence = 0
        self._seen: set[str] = set()
        self._listeners: list[EventListener] = []

    @property
    def sequence(self) -> int:
        """The sequence assigned to the most recently accepted event."""
        return self._sequence

    def subscribe(self, listener: EventListener) -> Callable[[], None]:
        """Register a listener and return an unsubscribe callable."""
        self._listeners.append(listener)

        def _unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _unsubscribe

    def publish(
        self, event_type: str, payload: dict[str, object], *, event_id: str | None = None
    ) -> OrionEvent:
        """Publish an event, assigning a sequence; duplicates are ignored."""
        resolved_id = event_id or str(uuid.uuid4())
        if resolved_id in self._seen:
            # At-least-once delivery: an already-seen event is not re-emitted.
            return OrionEvent(
                event_id=resolved_id,
                sequence=self._sequence,
                type=event_type,
                payload=dict(payload),
                timestamp=datetime.now(),
            )

        self._sequence += 1
        event = OrionEvent(
            event_id=resolved_id,
            sequence=self._sequence,
            type=event_type,
            payload=dict(payload),
            timestamp=datetime.now(),
        )
        self._seen.add(resolved_id)
        for listener in list(self._listeners):
            listener(event)
        return event
