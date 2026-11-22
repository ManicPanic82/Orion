"""Tray residency: the window closes to the notification area, not to nothing.

Design notes that matter on Windows:

* The ``QSystemTrayIcon`` is held for the process lifetime. If it is garbage
  collected the icon disappears from the notification area with no error.
* ``hide()`` is called before quitting, otherwise Windows can leave a ghost icon
  that only clears on hover.
* Availability is injected so the policy can be tested on the offscreen platform,
  where no system tray exists.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

__all__ = ["TrayController", "build_app_icon"]

log = logging.getLogger(__name__)

_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
_BACKGROUND = "#0B0F14"
_RING = "#14B8A6"
_STARS = "#3B82F6"


def _render_icon(size: int) -> QPixmap:
    """Draw the Orion mark: a teal ring with the three belt stars."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(_BACKGROUND))
    radius = size * 0.22
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    pen = QPen(QColor(_RING))
    pen.setWidthF(max(size * 0.075, 1.0))
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    inset = size * 0.2
    painter.drawEllipse(QRectF(inset, inset, size - 2 * inset, size - 2 * inset))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(_STARS))
    centre = size / 2
    for dx, dy, scale in ((-0.15, 0.02, 0.045), (0.0, -0.09, 0.055), (0.15, 0.02, 0.045)):
        star_radius = max(size * scale, 1.0)
        painter.drawEllipse(
            QRectF(
                centre + dx * size - star_radius,
                centre + dy * size - star_radius,
                star_radius * 2,
                star_radius * 2,
            )
        )

    painter.end()
    return pixmap


def build_app_icon() -> QIcon:
    """Multi-resolution icon drawn in code, so no binary asset is committed."""
    icon = QIcon()
    for size in _ICON_SIZES:
        icon.addPixmap(_render_icon(size))
    return icon


class TrayController(QObject):
    """Owns the tray icon, its menu, and the hide/restore policy."""

    quit_requested = Signal()
    notice_shown = Signal()
    installed = Signal()

    def __init__(
        self,
        window: QWidget,
        *,
        is_available: Callable[[], bool] | None = None,
        notice_already_shown: bool = False,
        retries: int = 5,
        retry_interval_ms: int = 1_000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._is_available = is_available or QSystemTrayIcon.isSystemTrayAvailable
        self._notice_shown = notice_already_shown
        self._icon: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        self._retries_left = max(int(retries), 0)
        self._retry_interval_ms = max(int(retry_interval_ms), 1)
        self._retry_timer: QTimer | None = None

    # -- lifecycle --------------------------------------------------------

    def install(self) -> bool:
        """Create and show the tray icon, retrying briefly if the shell is not ready.

        At sign-in the shell can still be starting, so a single availability check
        would wrongly conclude that no tray exists and the autostarted instance would
        exit on its first close. Returns whether the icon exists *now*; a later
        success is reported through :attr:`installed`.
        """
        if self._try_install():
            return True
        if self._retries_left > 0:
            timer = QTimer(self)
            timer.setInterval(self._retry_interval_ms)
            timer.timeout.connect(self._retry)
            timer.start()
            self._retry_timer = timer
        else:
            log.info("system tray unavailable; window close will exit the application")
        return False

    def _try_install(self) -> bool:
        if self._icon is not None:
            return True
        if not self._is_available():
            return False

        menu = QMenu()
        open_action = QAction("Open Orion Workstation", menu)
        open_action.triggered.connect(self.restore_window)
        menu.addAction(open_action)
        menu.addSeparator()
        quit_action = QAction("Quit Orion", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        icon = QSystemTrayIcon(build_app_icon(), self)
        icon.setToolTip("Orion Workstation — running in the notification area")
        icon.setContextMenu(menu)
        icon.activated.connect(self._on_activated)
        icon.show()

        self._icon = icon
        self._menu = menu
        self.installed.emit()
        return True

    def _retry(self) -> None:
        self._retries_left -= 1
        if self._try_install():
            self._stop_retries()
            return
        if self._retries_left <= 0:
            self._stop_retries()
            log.info("system tray did not become available; window close will exit")

    def _stop_retries(self) -> None:
        if self._retry_timer is not None:
            self._retry_timer.stop()
            self._retry_timer.deleteLater()
            self._retry_timer = None

    def available(self) -> bool:
        return self._icon is not None

    def shutdown(self) -> None:
        self._stop_retries()
        if self._icon is None:
            return
        self._icon.hide()
        self._icon.setContextMenu(None)
        self._icon.deleteLater()
        self._icon = None
        if self._menu is not None:
            self._menu.deleteLater()
            self._menu = None

    # -- policy -----------------------------------------------------------

    def hide_window(self) -> None:
        """Hide the window and explain, once, where it went."""
        if self._icon is None:
            return
        self._window.hide()
        if not self._notice_shown:
            self._icon.showMessage(
                "Orion is still running",
                "Right-click the tray icon to quit. Launching Orion again brings this window back.",
                QSystemTrayIcon.MessageIcon.Information,
                6_000,
            )
            self._notice_shown = True
            self.notice_shown.emit()

    def restore_window(self) -> None:
        window = self._window
        if window.isMinimized():
            window.showNormal()
        else:
            window.show()
        window.raise_()
        window.activateWindow()

    # -- internals --------------------------------------------------------

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_window()
