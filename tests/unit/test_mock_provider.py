"""Behaviour of the Phase 1 mock state provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from orion.mock.state_provider import MockStateProvider
from orion.state.models import MAX_COMMAND_LENGTH, StatusKind, TaskState
from orion.state.provider import StateProvider

FIXED_NOW = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)


def _provider() -> MockStateProvider:
    return MockStateProvider(clock=lambda: FIXED_NOW)


def test_provider_satisfies_the_protocol() -> None:
    assert isinstance(_provider(), StateProvider)


def test_provider_reports_itself_as_mock() -> None:
    assert _provider().is_mock is True


def test_every_component_is_reported_as_mock() -> None:
    snapshot = _provider().snapshot()

    assert snapshot.is_mock is True
    assert snapshot.agent.kind is StatusKind.MOCK
    assert snapshot.model.kind is StatusKind.MOCK
    assert snapshot.agent.detail
    assert snapshot.model.detail


def test_no_task_is_fabricated_before_a_submission() -> None:
    assert _provider().snapshot().tasks == ()


def test_snapshot_is_deterministic_for_a_fixed_clock() -> None:
    provider = _provider()
    first = provider.snapshot()
    second = provider.snapshot()

    assert first == second
    assert all(event.timestamp == FIXED_NOW for event in first.events)


def test_submission_creates_a_simulated_task_and_never_a_success() -> None:
    provider = _provider()
    result = provider.submit_command("Summarise the Orion roadmap", "req-1")

    assert result.accepted is True
    assert result.simulated is True
    assert result.request_id == "req-1"
    assert "No agent, model, or tool executed" in result.message

    tasks = provider.snapshot().tasks
    assert len(tasks) == 1
    assert tasks[0].state is TaskState.SIMULATED
    assert tasks[0].task_id == "sim-0001"
    assert "Nothing was executed" in tasks[0].note


def test_submission_is_recorded_as_an_event() -> None:
    provider = _provider()
    before = len(provider.snapshot().events)
    provider.submit_command("Check the build", "req-2")

    events = provider.snapshot().events
    assert len(events) == before + 1
    assert events[-1].source == "composer"
    assert "sim-0001" in events[-1].message


def test_blank_command_is_rejected() -> None:
    provider = _provider()
    result = provider.submit_command("   \n  ", "req-3")

    assert result.accepted is False
    assert provider.snapshot().tasks == ()


def test_overlong_command_is_rejected() -> None:
    provider = _provider()
    result = provider.submit_command("x" * (MAX_COMMAND_LENGTH + 1), "req-4")

    assert result.accepted is False
    assert "exceeds" in result.message
    assert provider.snapshot().tasks == ()


def test_long_command_title_is_truncated() -> None:
    provider = _provider()
    provider.submit_command("word " * 60, "req-5")

    title = provider.snapshot().tasks[0].title
    assert len(title) <= 72
    assert title.endswith("…")


def test_event_buffer_is_bounded() -> None:
    from orion.mock.state_provider import MAX_RETAINED_EVENTS

    provider = _provider()
    for index in range(MAX_RETAINED_EVENTS + 20):
        provider.submit_command(f"command {index}", f"req-{index}")

    events = provider.snapshot().events
    assert len(events) == MAX_RETAINED_EVENTS


def test_events_are_ordered_and_identified() -> None:
    provider = _provider()
    provider.submit_command("first", "a")
    provider.submit_command("second", "b")

    ids = [event.event_id for event in provider.snapshot().events]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("command", ["", "   "])
def test_empty_command_never_creates_a_task(command: str) -> None:
    assert _provider().submit_command(command, "x").accepted is False
