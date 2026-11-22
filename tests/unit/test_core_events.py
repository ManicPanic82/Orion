"""Event stream behaviour for the Orion Core process."""

from __future__ import annotations

from orion.core.events import EventStream, OrionEvent


def _event_type() -> str:
    return "task.created"


def test_publish_assigns_sequential_ids_and_types() -> None:
    stream = EventStream()
    first = stream.publish(_event_type(), {"task_id": "t1"})
    second = stream.publish(_event_type(), {"task_id": "t2"})

    assert isinstance(first, OrionEvent)
    assert isinstance(second, OrionEvent)
    assert first.sequence == 1
    assert second.sequence == 2
    assert first.event_id != second.event_id
    assert stream.sequence == 2


def test_subscribers_receive_events_in_order() -> None:
    stream = EventStream()
    received: list[OrionEvent] = []
    unsubscribe = stream.subscribe(received.append)

    stream.publish(_event_type(), {"task_id": "t1"})
    stream.publish(_event_type(), {"task_id": "t2"})

    assert [event.payload["task_id"] for event in received] == ["t1", "t2"]
    assert unsubscribe is not None
    unsubscribe()
    stream.publish(_event_type(), {"task_id": "t3"})
    assert len(received) == 2


def test_duplicate_event_ids_are_not_replayed() -> None:
    stream = EventStream()
    received: list[OrionEvent] = []
    stream.subscribe(received.append)

    first = stream.publish(_event_type(), {"task_id": "t1"}, event_id="evt-1")
    second = stream.publish(_event_type(), {"task_id": "t1"}, event_id="evt-1")

    assert first.sequence == 1
    assert second.sequence == 1
    assert len(received) == 1
    assert stream.sequence == 1
