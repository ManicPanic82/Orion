"""Windows login autostart registration.

Mechanism: ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run``. Per-user, no
elevation, inspectable in Task Manager, and trivially reversible.

Safety rules enforced here:

* only the value name :data:`VALUE_NAME` is ever written or deleted;
* deletion happens only when the stored command is exactly the command Orion
  would write, so a value rewritten by the user or another tool is reported and
  left alone;
* registration failure is reported, never swallowed, and never leaves the
  persisted preference claiming success.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from orion.config.settings import Settings
from orion.config.store import SettingsStore

__all__ = [
    "RUN_KEY",
    "VALUE_NAME",
    "RegistryBackend",
    "StartupController",
    "StartupError",
    "StartupRegistration",
    "StartupStatus",
    "UnregisterOutcome",
    "WinRegBackend",
    "build_run_command",
    "resolve_launch_command",
]

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "OrionWorkstation"


class StartupError(RuntimeError):
    """Raised when the registry could not be read or written."""


class UnregisterOutcome(StrEnum):
    REMOVED = "removed"
    ABSENT = "absent"
    FOREIGN = "foreign"


class RegistryBackend(Protocol):
    """Minimal registry surface, injected so tests never touch HKCU\\Run."""

    def read(self, name: str) -> str | None: ...

    def write(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...


class WinRegBackend:
    """``HKEY_CURRENT_USER`` implementation of :class:`RegistryBackend`."""

    def __init__(self, key_path: str = RUN_KEY) -> None:
        self._key_path = key_path

    def _winreg(self):
        import winreg  # imported lazily so the module loads on any platform

        return winreg

    def read(self, name: str) -> str | None:
        winreg = self._winreg()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key_path) as key:
                value, _kind = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return None
        except OSError as exc:  # pragma: no cover - depends on machine policy
            raise StartupError(f"could not read startup registration: {exc}") from exc
        return str(value)

    def write(self, name: str, value: str) -> None:
        winreg = self._winreg()
        try:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                self._key_path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        except OSError as exc:
            raise StartupError(f"could not write startup registration: {exc}") from exc

    def delete(self, name: str) -> None:
        winreg = self._winreg()
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self._key_path, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            return
        except OSError as exc:  # pragma: no cover - depends on machine policy
            raise StartupError(f"could not remove startup registration: {exc}") from exc


def resolve_launch_command(python_executable: str | None = None) -> str:
    """Build the command that login should run.

    ``pythonw.exe`` is preferred because the console launcher flashes a terminal
    window at sign-in, which looks like a fault. A packaged build launches its own
    executable. No working directory is available in a Run entry, so nothing here
    may depend on the current directory.
    """
    executable = Path(python_executable or sys.executable)

    if getattr(sys, "frozen", False):
        return build_run_command(executable, ["--minimised"])

    windowless = executable.with_name("pythonw.exe")
    launcher = windowless if windowless.is_file() else executable
    return build_run_command(launcher, ["-m", "orion", "--minimised"])


def build_run_command(executable: Path, arguments: list[str]) -> str:
    """Quote a command line the way Windows will parse it."""
    return subprocess.list2cmdline([str(executable), *arguments])


@dataclass(frozen=True, slots=True)
class StartupStatus:
    """What the UI is allowed to claim about login autostart."""

    desired: bool
    registered: bool
    matches_expected: bool
    note: str
    error: str | None = None


class StartupRegistration:
    """Reads and writes the single Run value Orion owns."""

    def __init__(
        self,
        backend: RegistryBackend,
        command: str,
        value_name: str = VALUE_NAME,
    ) -> None:
        self._backend = backend
        self._command = command
        self._value_name = value_name

    @property
    def command(self) -> str:
        return self._command

    def read_current(self) -> str | None:
        return self._backend.read(self._value_name)

    def is_registered(self) -> bool:
        return self.read_current() is not None

    def matches_expected(self) -> bool:
        return self.read_current() == self._command

    def register(self) -> None:
        self._backend.write(self._value_name, self._command)

    def unregister(self) -> UnregisterOutcome:
        current = self.read_current()
        if current is None:
            return UnregisterOutcome.ABSENT
        if current != self._command:
            log.warning(
                "startup value %s does not match this build; leaving it untouched",
                self._value_name,
            )
            return UnregisterOutcome.FOREIGN
        self._backend.delete(self._value_name)
        return UnregisterOutcome.REMOVED


class StartupController:
    """Applies the user's startup preference and reports the real state."""

    def __init__(
        self,
        registration: StartupRegistration,
        settings: Settings,
        store: SettingsStore,
    ) -> None:
        self._registration = registration
        self._settings = settings
        self._store = store

    @property
    def registration(self) -> StartupRegistration:
        return self._registration

    def status(self) -> StartupStatus:
        desired = self._settings.startup.enabled
        try:
            current = self._registration.read_current()
        except StartupError as exc:
            return StartupStatus(
                desired=desired,
                registered=False,
                matches_expected=False,
                note="Startup state could not be read.",
                error=str(exc),
            )

        registered = current is not None
        matches = current == self._registration.command

        if current is None:
            note = "Not registered. Orion will not start at sign-in."
        elif matches:
            note = "Registered. Orion starts in the notification area at sign-in."
        else:
            note = (
                "A different startup command is registered by something else; "
                "Orion will not change it."
            )

        if desired and not matches or not desired and matches:
            note += " The saved preference and the registry disagree."

        return StartupStatus(
            desired=desired,
            registered=registered,
            matches_expected=matches,
            note=note,
        )

    def set_enabled(self, enabled: bool) -> StartupStatus:
        """Apply ``enabled`` and persist it, reporting any failure honestly."""
        error: str | None = None
        try:
            if enabled:
                self._registration.register()
            else:
                outcome = self._registration.unregister()
                if outcome is UnregisterOutcome.FOREIGN:
                    error = (
                        "A startup entry with this name belongs to another command and "
                        "was left untouched."
                    )
        except StartupError as exc:
            error = str(exc)
            enabled = False

        self._settings.startup.enabled = enabled
        try:
            self._store.save(self._settings)
        except Exception as exc:  # noqa: BLE001 - surfaced, never swallowed
            error = error or f"settings could not be saved: {exc}"

        status = self.status()
        if error is None:
            return status
        return StartupStatus(
            desired=status.desired,
            registered=status.registered,
            matches_expected=status.matches_expected,
            note=status.note,
            error=error,
        )

    def mark_prompted(self) -> None:
        if self._settings.startup.prompted:
            return
        self._settings.startup.prompted = True
        try:
            self._store.save(self._settings)
        except Exception as exc:  # noqa: BLE001 - surfaced by the caller's log
            log.warning("could not persist startup prompt state: %s", exc)
