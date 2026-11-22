"""The visible MOCK marker required by CONTRACTS.md invariant 10."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from orion.ui.widgets.status_pill import StatusPill

__all__ = ["MockBadge"]


class MockBadge(StatusPill):
    """An unmistakable marker for simulated state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("MOCK", "mock", parent)
        self.setToolTip("Simulated state. No real component is connected in this phase.")
