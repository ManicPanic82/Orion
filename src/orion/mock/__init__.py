"""Explicit mock implementations for Phase 1.

Nothing in this package performs real work. Every status it reports uses
:class:`orion.state.models.StatusKind.MOCK`, and every command it accepts is
described to the user as simulated.
"""

from __future__ import annotations

from orion.mock.state_provider import MockStateProvider

__all__ = ["MockStateProvider"]
