"""Console buffer and filtering, free of Qt.

Keeping this pure Python means the bounded-buffer and redaction rules are tested
directly, without an event loop, and the widget stays a thin renderer.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from orion.config.settings import Severity

__all__ = ["ConsoleEntry", "ConsoleViewModel", "DEFAULT_CAPACITY", "redact"]

DEFAULT_CAPACITY = 500

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{8,}"), r"\1 [redacted]"),
    (re.compile(r"(?i)\b(sk-[A-Za-z0-9]{8,})"), "[redacted]"),
    (
        re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key|apikey)\b(\s*[:=]\s*)\S+"),
        r"\1\2[redacted]",
    ),
)


def redact(text: str) -> str:
    """Mask credential-shaped values before they reach the console."""
    result = text
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


@dataclass(frozen=True, slots=True)
class ConsoleEntry:
    timestamp: datetime
    severity: Severity
    source: str
    message: str


class ConsoleViewModel:
    """Bounded, filterable, redacting activity buffer."""

    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._clock = clock or (lambda: datetime.now(UTC))
        self._entries: list[ConsoleEntry] = []
        self._listeners: list[Callable[[], None]] = []

    @property
    def capacity(self) -> int:
        return self._capacity

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a change callback and return a function that removes it."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    def append(self, severity: Severity, source: str, message: str) -> ConsoleEntry:
        entry = ConsoleEntry(
            timestamp=self._clock(),
            severity=severity,
            source=source,
            message=redact(message),
        )
        self._entries.append(entry)
        if len(self._entries) > self._capacity:
            del self._entries[: len(self._entries) - self._capacity]
        self._notify()
        return entry

    def extend(self, entries: Iterable[ConsoleEntry]) -> None:
        for entry in entries:
            self._entries.append(
                ConsoleEntry(
                    timestamp=entry.timestamp,
                    severity=entry.severity,
                    source=entry.source,
                    message=redact(entry.message),
                )
            )
        if len(self._entries) > self._capacity:
            del self._entries[: len(self._entries) - self._capacity]
        self._notify()

    def clear(self) -> None:
        if not self._entries:
            return
        self._entries.clear()
        self._notify()

    def entries(self, min_severity: Severity = Severity.DEBUG) -> list[ConsoleEntry]:
        threshold = min_severity.rank
        return [entry for entry in self._entries if entry.severity.rank >= threshold]

    def __len__(self) -> int:
        return len(self._entries)

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()
