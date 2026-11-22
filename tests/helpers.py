"""Shared test doubles.

Kept out of ``conftest.py`` so both unit and Qt tests can import them explicitly.
"""

from __future__ import annotations

from orion.startup import StartupError


class FakeRegistry:
    """In-memory stand-in for ``HKCU\\...\\Run``. Never touches the real registry."""

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = dict(values or {})
        self.writes: list[tuple[str, str]] = []
        self.deletes: list[str] = []
        self.fail_on_write: str | None = None
        self.fail_on_read: str | None = None

    def read(self, name: str) -> str | None:
        if self.fail_on_read:
            raise StartupError(self.fail_on_read)
        return self.values.get(name)

    def write(self, name: str, value: str) -> None:
        if self.fail_on_write:
            raise StartupError(self.fail_on_write)
        self.writes.append((name, value))
        self.values[name] = value

    def delete(self, name: str) -> None:
        self.deletes.append(name)
        self.values.pop(name, None)
