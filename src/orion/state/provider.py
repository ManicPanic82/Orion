"""The state seam between the presentation layer and whatever owns the truth.

In Phase 1 the only implementation is :class:`orion.mock.state_provider.MockStateProvider`.
Phase 2 replaces it with a client of Orion Core. The window depends on this
protocol, not on the mock, so that replacement is a composition change rather than
a UI rewrite.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from orion.state.models import AppSnapshot, CommandResult

__all__ = ["StateProvider"]


@runtime_checkable
class StateProvider(Protocol):
    """Authoritative state and command intake for the Operations Centre."""

    @property
    def is_mock(self) -> bool:
        """True when this provider produces simulated state."""
        ...

    def snapshot(self) -> AppSnapshot:
        """Return the current authoritative snapshot."""
        ...

    def submit_command(self, text: str, request_id: str) -> CommandResult:
        """Submit a user command.

        Implementations must validate ``text`` and must never claim work was
        performed that they did not perform.
        """
        ...
