"""Honest placeholder for a destination that is not implemented yet."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from orion.navigation import NavDestination
from orion.ui.widgets.card import Card
from orion.ui.widgets.status_pill import StatusPill

__all__ = ["PlannedPage"]


class PlannedPage(QWidget):
    """States what will live here and when, without pretending it works.

    No interactive control appears on this page, because none would do anything.
    """

    def __init__(self, nav_destination: NavDestination, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.nav_destination = nav_destination
        self.setObjectName("PlannedPage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel(nav_destination.label, self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        subtitle = QLabel(nav_destination.subtitle, self)
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        card = Card("Not implemented yet", None, self)
        badge = StatusPill("PLANNED", "unavailable", card)
        card.add_header_widget(badge)

        body = QLabel(
            f"{nav_destination.label} is planned for {nav_destination.phase} and is not "
            "part of the Phase 1 shell. No controls are shown because nothing on this "
            "page would be functional.",
            card,
        )
        body.setWordWrap(True)
        card.add_widget(body)

        outer.addWidget(card)
        outer.addStretch(1)
