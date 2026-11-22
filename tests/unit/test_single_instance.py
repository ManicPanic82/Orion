"""Single-instance exclusivity and window activation.

These run on Windows, where the mutex is authoritative. The pipe carries only the
activation message.
"""

from __future__ import annotations

import uuid

from PySide6.QtNetwork import QLocalSocket

from orion.single_instance import SingleInstanceGuard


def _key() -> str:
    return f"orion-test-{uuid.uuid4().hex}"


def test_first_guard_becomes_primary(qtbot) -> None:
    guard = SingleInstanceGuard(_key())
    assert guard.acquire() is True
    guard.close()


def test_second_guard_is_refused_while_primary_holds_the_mutex(qtbot) -> None:
    key = _key()
    first = SingleInstanceGuard(key)
    assert first.acquire() is True

    second = SingleInstanceGuard(key)
    assert second.acquire() is False

    first.close()
    second.close()


def test_primary_can_be_acquired_again_after_release(qtbot) -> None:
    key = _key()
    first = SingleInstanceGuard(key)
    assert first.acquire() is True
    first.close()

    second = SingleInstanceGuard(key)
    assert second.acquire() is True
    second.close()


def test_notify_existing_raises_the_primary_window(qtbot) -> None:
    key = _key()
    primary = SingleInstanceGuard(key)
    assert primary.acquire() is True

    secondary = SingleInstanceGuard(key)
    assert secondary.acquire() is False

    with qtbot.waitSignal(primary.activate_requested, timeout=3_000):
        assert secondary.notify_existing() is True

    primary.close()
    secondary.close()


def test_notify_existing_fails_when_nothing_is_listening(qtbot) -> None:
    guard = SingleInstanceGuard(_key())
    assert guard.notify_existing() is False


def test_activation_message_reaches_the_server(qtbot) -> None:
    """Guard against the pipe name silently changing format."""
    key = _key()
    primary = SingleInstanceGuard(key)
    assert primary.acquire() is True

    socket = QLocalSocket()
    socket.connectToServer(key)
    assert socket.waitForConnected(2_000)

    with qtbot.waitSignal(primary.activate_requested, timeout=3_000):
        socket.write(b"activate")
        socket.flush()
        socket.waitForBytesWritten(2_000)

    socket.disconnectFromServer()
    primary.close()
