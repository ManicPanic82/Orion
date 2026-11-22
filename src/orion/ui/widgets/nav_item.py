"""Navigation rail entry."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget

from orion.navigation import NavDestination

__all__ = ["NavItem"]


class NavItem(QPushButton):
    """Checkable button representing one destination."""

    def __init__(self, nav_destination: NavDestination, parent: QWidget | None = None) -> None:
        # Qt treats "&" in button text as a mnemonic marker, so it must be doubled.
        super().__init__(nav_destination.label.replace("&", "&&"), parent)
        self.nav_destination = nav_destination
        self.setObjectName("NavItem")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{nav_destination.subtitle} · {nav_destination.phase}")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
