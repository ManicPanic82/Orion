"""Console buffer, filtering, and redaction."""

from __future__ import annotations

from datetime import UTC, datetime

from orion.config.settings import Severity
from orion.ui.viewmodels.console_vm import ConsoleViewModel, redact

FIXED_NOW = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)


def _console(capacity: int = 500) -> ConsoleViewModel:
    return ConsoleViewModel(capacity=capacity, clock=lambda: FIXED_NOW)


def test_entries_are_appended_with_clock_timestamps() -> None:
    console = _console()
    entry = console.append(Severity.INFO, "test", "hello")

    assert entry.timestamp == FIXED_NOW
    assert console.entries() == [entry]


def test_buffer_discards_oldest_beyond_capacity() -> None:
    console = _console(capacity=3)
    for index in range(5):
        console.append(Severity.INFO, "test", f"message {index}")

    messages = [entry.message for entry in console.entries()]
    assert messages == ["message 2", "message 3", "message 4"]


def test_filtering_respects_minimum_severity() -> None:
    console = _console()
    console.append(Severity.DEBUG, "t", "debug")
    console.append(Severity.INFO, "t", "info")
    console.append(Severity.WARNING, "t", "warning")
    console.append(Severity.ERROR, "t", "error")

    assert [e.message for e in console.entries(Severity.WARNING)] == ["warning", "error"]
    assert len(console.entries(Severity.DEBUG)) == 4


def test_clear_empties_the_buffer_and_notifies() -> None:
    console = _console()
    notifications: list[int] = []
    console.add_listener(lambda: notifications.append(1))

    console.append(Severity.INFO, "t", "one")
    console.clear()

    assert len(console) == 0
    assert len(notifications) == 2


def test_clear_on_empty_buffer_does_not_notify() -> None:
    console = _console()
    notifications: list[int] = []
    console.add_listener(lambda: notifications.append(1))

    console.clear()

    assert notifications == []


def test_listener_can_be_removed() -> None:
    console = _console()
    notifications: list[int] = []
    remove = console.add_listener(lambda: notifications.append(1))
    remove()

    console.append(Severity.INFO, "t", "one")

    assert notifications == []


def test_capacity_must_be_positive() -> None:
    import pytest

    with pytest.raises(ValueError):
        ConsoleViewModel(capacity=0)


def test_redaction_masks_bearer_tokens() -> None:
    assert redact("Authorization: Bearer abcdef1234567890") == "Authorization: Bearer [redacted]"


def test_redaction_masks_api_keys_and_passwords() -> None:
    assert "sk-secretvalue" not in redact("key sk-secretvalue loaded")
    assert redact("password=hunter2") == "password=[redacted]"
    assert redact("api_key: 12345") == "api_key: [redacted]"


def test_redaction_leaves_ordinary_text_alone() -> None:
    text = "Objective submitted for the roadmap review."
    assert redact(text) == text


def test_appended_messages_are_redacted() -> None:
    console = _console()
    console.append(Severity.INFO, "test", "token=abcdef123456")

    assert console.entries()[0].message == "token=[redacted]"
