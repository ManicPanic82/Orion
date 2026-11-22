"""Single-instance enforcement and window activation.

Windows specifics discovered during Phase 1 validation: Qt's ``QLocalServer`` can
open *multiple* server objects on the same pipe name, because Win32 named pipes
support multiple instances. A second ``listen()`` therefore succeeds and cannot be
used to detect an existing instance.

Exclusivity is instead enforced with a per-session Win32 named mutex. The named
pipe is used only to carry the "activate your window" message to the instance that
owns the mutex. This is the standard Windows arrangement and needs no dependency
beyond ``ctypes``.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

from PySide6.QtCore import QEventLoop, QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

__all__ = ["SingleInstanceGuard"]

log = logging.getLogger(__name__)

_ERROR_ALREADY_EXISTS = 183
_ACTIVATE_MESSAGE = b"activate"
_ACK_MESSAGE = b"ack"
_CONNECT_TIMEOUT_MS = 400
_ACK_TIMEOUT_MS = 800


class _Mutex:
    """Thin Win32 named-mutex wrapper, or a no-op on non-Windows platforms."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._handle: int | None = None

    def acquire(self) -> bool:
        """Return True when this process created the mutex (i.e. is the primary)."""
        if sys.platform != "win32":
            return True
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        handle = kernel32.CreateMutexW(None, False, self._name)
        if not handle:
            log.warning("CreateMutexW failed for %s; continuing without exclusivity", self._name)
            return True
        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is None or sys.platform != "win32":
            self._handle = None
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle(self._handle)
        self._handle = None


class SingleInstanceGuard(QObject):
    """Owns instance exclusivity and the activation channel."""

    activate_requested = Signal()

    def __init__(self, key: str = "orion-workstation", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._key = key
        self._mutex = _Mutex(f"Local\\{key}")
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        self._connections: list[QLocalSocket] = []
        self._primary = False

    # -- lifecycle --------------------------------------------------------

    def acquire(self) -> bool:
        """Become the primary instance, or return False if one already exists."""
        if not self._mutex.acquire():
            return False
        if sys.platform != "win32":
            QLocalServer.removeServer(self._key)
        if not self._server.listen(self._key):
            # The mutex is authoritative; a pipe failure must not block startup.
            log.warning("activation channel unavailable: %s", self._server.errorString())
        self._primary = True
        return True

    def notify_existing(self) -> bool:
        """Ask the primary instance to raise its window.

        The write is acknowledged by the primary before this returns. Without an
        acknowledgement the message can be truncated when the secondary process
        exits immediately after writing.
        """
        socket = QLocalSocket(self)
        socket.connectToServer(self._key)
        if not socket.waitForConnected(_CONNECT_TIMEOUT_MS):
            return False

        delivered = {"ack": False}

        def _on_ready() -> None:
            if _ACK_MESSAGE in bytes(socket.readAll()):
                delivered["ack"] = True
            loop.quit()

        socket.readyRead.connect(_on_ready)
        socket.write(_ACTIVATE_MESSAGE)
        socket.flush()

        # A nested event loop, rather than waitForReadyRead, so the acknowledgement
        # can be processed even when both sides live in one process (tests).
        loop = QEventLoop(self)
        timeout = QTimer(self)
        timeout.setSingleShot(True)
        timeout.timeout.connect(loop.quit)
        timeout.start(_ACK_TIMEOUT_MS)
        loop.exec()
        timeout.stop()

        socket.disconnectFromServer()
        return delivered["ack"]

    def close(self) -> None:
        for connection in list(self._connections):
            connection.abort()
            connection.deleteLater()
        self._connections.clear()

        if self._primary:
            self._server.close()
            if sys.platform != "win32":
                QLocalServer.removeServer(self._key)
            self._primary = False
        self._mutex.release()

    # -- internals --------------------------------------------------------

    def _on_new_connection(self) -> None:
        connection = self._server.nextPendingConnection()
        if connection is None:
            return
        # Keep a Python reference: a wrapper collected while the C++ socket is
        # still live causes an access violation on the next signal.
        self._connections.append(connection)
        connection.readyRead.connect(self._drain)
        connection.disconnected.connect(self._drop)

    def _drain(self) -> None:
        connection = self.sender()
        if not isinstance(connection, QLocalSocket):
            return
        payload = bytes(connection.readAll())
        if _ACTIVATE_MESSAGE not in payload:
            return
        log.debug("activation request received from a second instance")
        connection.write(_ACK_MESSAGE)
        connection.flush()
        self.activate_requested.emit()

    def _drop(self) -> None:
        connection = self.sender()
        if not isinstance(connection, QLocalSocket):
            return
        if connection in self._connections:
            self._connections.remove(connection)
        connection.deleteLater()
