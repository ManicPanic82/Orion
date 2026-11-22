"""A pill-shaped status label driven by stylesheet tone selectors."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from orion.state.models import StatusKind
from orion.ui.widgets._qt import repolish

__all__ = ["StatusPill"]

_TONE_BY_KIND: dict[StatusKind, str] = {
    StatusKind.OPERATIONAL: "operational",
    StatusKind.DEGRADED: "degraded",
    StatusKind.UNAVAILABLE: "unavailable",
    StatusKind.MOCK: "mock",
}

_TONES = frozenset({"mock", "operational", "degraded", "unavailable", "danger"})


class StatusPill(QLabel):
    """Compact state indicator.

    Tone is a dynamic Qt property so the colour lives in the stylesheet rather
    than in widget code.
    """

    def __init__(self, text: str = "", tone: str = "mock", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("StatusPill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        normalised = tone if tone in _TONES else "unavailable"
        if self.property("tone") == normalised:
            return
        self.setProperty("tone", normalised)
        repolish(self)

    def tone(self) -> str:
        return str(self.property("tone"))

    def set_status_kind(self, kind: StatusKind) -> None:
        self.set_tone(_TONE_BY_KIND[kind])
