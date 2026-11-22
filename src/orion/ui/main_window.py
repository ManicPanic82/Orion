"""The Orion Workstation main window.

The window is a client of a :class:`orion.state.provider.StateProvider`. It owns
presentation, navigation, and preference persistence only. It holds no task,
model, or permission logic; every piece of assistant state it renders arrives from
the provider, which is explicitly mock in Phase 1.

Lifecycle (ADR-009): closing the window hides it to the notification area. Only
the tray's Quit action or Ctrl+Q ends the process. When no system tray exists the
window closes normally, because trapping the user with no visible interface and no
way to quit would be worse than losing residency.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from orion import APP_NAME, PHASE_LABEL, __version__
from orion.config.settings import Settings, SettingsError, Severity
from orion.config.store import SettingsStore
from orion.mock.state_provider import MockStateProvider
from orion.navigation import DEFAULT_PAGE_ID, DESTINATIONS
from orion.startup import StartupController
from orion.state.provider import StateProvider
from orion.ui.console_panel import ConsolePanel
from orion.ui.pages.command_centre import CommandCentrePage
from orion.ui.pages.planned_page import PlannedPage
from orion.ui.pages.settings_page import SettingsPage
from orion.ui.tray import TrayController
from orion.ui.viewmodels.command_centre_vm import CommandCentreViewModel
from orion.ui.viewmodels.console_vm import ConsoleEntry, ConsoleViewModel
from orion.ui.widgets.mock_badge import MockBadge
from orion.ui.widgets.nav_item import NavItem

__all__ = ["MainWindow"]

log = logging.getLogger(__name__)

_NAV_WIDTH = 236
_MIN_WIDTH = 1100
_MIN_HEIGHT = 720


class MainWindow(QMainWindow):
    """Top-level Operations Centre window."""

    def __init__(
        self,
        store: SettingsStore,
        settings: Settings,
        provider: StateProvider | None = None,
        startup: StartupController | None = None,
        startup_prompt: Callable[[], bool] | None = None,
        tray_available: Callable[[], bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._settings = settings
        self._provider: StateProvider = provider or MockStateProvider()
        self._startup = startup
        self._startup_prompt = startup_prompt
        self._console = ConsoleViewModel()
        self._command_vm = CommandCentreViewModel(self._provider, self._console)
        self._shutdown_requested = False

        self._nav_buttons: dict[str, NavItem] = {}
        self._pages: dict[str, QWidget] = {}

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        self._restore_geometry()

        self._build_ui()
        self._seed_console()
        self._show_page(self._settings.navigation.active_page, persist=False)

        self._tray = TrayController(
            self,
            is_available=tray_available,
            notice_already_shown=settings.ui.tray_notice_shown,
            parent=self,
        )
        self._tray.quit_requested.connect(self.request_quit)
        self._tray.notice_shown.connect(self._on_tray_notice_shown)
        self._tray.installed.connect(self._on_tray_installed)
        self._tray.install()

        shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(self.request_quit)

    # -- construction -----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("PageRoot")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_nav_rail(central))

        content = QWidget(central)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._stack = QStackedWidget(content)
        self._build_pages()

        self._console_panel = ConsolePanel(self._console, self._settings.console, content)
        self._console_panel.expanded_changed.connect(self._on_console_expanded)
        self._console_panel.min_severity_changed.connect(self._on_console_severity)

        splitter = QSplitter(Qt.Orientation.Vertical, content)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._stack)
        splitter.addWidget(self._console_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        self._splitter = splitter

        content_layout.addWidget(splitter)
        layout.addWidget(content, 1)

        self.setCentralWidget(central)

        status = self.statusBar()
        status.addPermanentWidget(MockBadge(status))
        version = QLabel(f"v{__version__} · {PHASE_LABEL}", status)
        version.setProperty("role", "muted")
        status.addPermanentWidget(version)

    def _build_nav_rail(self, parent: QWidget) -> QWidget:
        rail = QWidget(parent)
        rail.setObjectName("NavRail")
        rail.setFixedWidth(_NAV_WIDTH)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(4)

        brand = QLabel("ORION", rail)
        brand.setObjectName("NavBrand")
        layout.addWidget(brand)

        brand_sub = QLabel("WORKSTATION", rail)
        brand_sub.setObjectName("NavBrandSub")
        layout.addWidget(brand_sub)

        divider = QFrame(rail)
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(divider)
        layout.addSpacing(8)

        group = QButtonGroup(rail)
        group.setExclusive(True)

        for nav_destination in DESTINATIONS:
            item = NavItem(nav_destination, rail)
            item.clicked.connect(
                lambda _checked=False, page_id=nav_destination.id: self._show_page(page_id)
            )
            group.addButton(item)
            layout.addWidget(item)
            self._nav_buttons[nav_destination.id] = item

        layout.addStretch(1)

        layout.addWidget(MockBadge(rail))

        phase = QLabel(PHASE_LABEL, rail)
        phase.setProperty("role", "muted")
        phase.setWordWrap(True)
        layout.addWidget(phase)

        self._nav_group = group
        return rail

    def _build_pages(self) -> None:
        for nav_destination in DESTINATIONS:
            page: QWidget
            if nav_destination.id == "command_centre":
                page = CommandCentrePage(self._command_vm, self._stack)
            elif nav_destination.id == "settings":
                page = SettingsPage(self._store, self._settings, self._startup, self._stack)
            else:
                page = PlannedPage(nav_destination, self._stack)
            self._stack.addWidget(page)
            self._pages[nav_destination.id] = page

    def _seed_console(self) -> None:
        snapshot = self._provider.snapshot()
        self._console.extend(
            ConsoleEntry(
                timestamp=event.timestamp,
                severity=event.severity,
                source=event.source,
                message=event.message,
            )
            for event in snapshot.events
        )

    # -- navigation -------------------------------------------------------

    def _show_page(self, page_id: str, *, persist: bool = True) -> None:
        if page_id not in self._pages:
            page_id = DEFAULT_PAGE_ID

        self._stack.setCurrentWidget(self._pages[page_id])

        button = self._nav_buttons.get(page_id)
        if button is not None and not button.isChecked():
            button.setChecked(True)

        if self._settings.navigation.active_page != page_id:
            self._settings.navigation.active_page = page_id
            if persist:
                self._persist()

    def show_page(self, page_id: str) -> None:
        """Navigate to a destination by id. Unknown ids fall back to Command Centre."""
        self._show_page(page_id)

    def current_page_id(self) -> str:
        current = self._stack.currentWidget()
        for page_id, page in self._pages.items():
            if page is current:
                return page_id
        return DEFAULT_PAGE_ID

    def nav_button(self, page_id: str) -> NavItem:
        return self._nav_buttons[page_id]

    def page(self, page_id: str) -> QWidget:
        return self._pages[page_id]

    # -- console preference ----------------------------------------------

    def _on_console_expanded(self, expanded: bool) -> None:
        self._settings.console.expanded = expanded
        if expanded:
            height = max(self._settings.console.height, 120)
            total = max(self._splitter.height(), height + 200)
            self._splitter.setSizes([total - height, height])
        self._persist()

    def _on_console_severity(self, severity: object) -> None:
        if isinstance(severity, Severity):
            self._settings.console.min_severity = severity
            self._persist()

    # -- tray and lifecycle ----------------------------------------------

    @property
    def tray_installed(self) -> bool:
        return self._tray.available()

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    @property
    def tray(self) -> TrayController:
        return self._tray

    def restore_from_tray(self) -> None:
        self._tray.restore_window()

    def request_quit(self) -> None:
        """End the process: persist, remove the icon, then quit."""
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        self._capture_geometry()
        self._persist()
        self._tray.shutdown()

        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _on_tray_notice_shown(self) -> None:
        if self._settings.ui.tray_notice_shown:
            return
        self._settings.ui.tray_notice_shown = True
        self._persist()

    def _on_tray_installed(self) -> None:
        """Keep the process alive once a tray exists to restore it from."""
        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(False)

    def prompt_startup_if_needed(self) -> None:
        """Ask once, at first interactive launch, whether Orion should autostart.

        Deliberately *not* called from :meth:`closeEvent`: a modal dialog in the
        close path blocks application shutdown, because quitting closes the window
        and nothing can answer the dialog.
        """
        if self._startup is None or self._settings.startup.prompted:
            return

        prompt = self._startup_prompt or self._default_startup_prompt
        accepted = bool(prompt())

        self._settings.startup.prompted = True
        if accepted:
            self._startup.set_enabled(True)
        else:
            self._persist()

        settings_page = self._pages.get("settings")
        if isinstance(settings_page, SettingsPage):
            settings_page.refresh_startup()

    def _default_startup_prompt(self) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle("Start Orion at sign-in")
        box.setText("Start Orion when you sign in?")
        box.setInformativeText(
            "Orion will open in the notification area, so it is ready when you need it. "
            "You can change this later in Settings."
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        return box.exec() == QMessageBox.StandardButton.Yes

    # -- geometry and persistence ----------------------------------------

    def _restore_geometry(self) -> None:
        window = self._settings.window
        width = max(int(window.width), _MIN_WIDTH)
        height = max(int(window.height), _MIN_HEIGHT)
        self.resize(width, height)

        if window.x is not None and window.y is not None:
            x, y = self._clamp_position(int(window.x), int(window.y), width, height)
            self.move(x, y)

        if window.maximized:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    @staticmethod
    def _clamp_position(x: int, y: int, width: int, height: int) -> tuple[int, int]:
        """Keep a restored window on a real screen."""
        candidate = QRect(x, y, width, height)
        for screen in QGuiApplication.screens():
            if screen.availableGeometry().intersects(candidate):
                return x, y

        primary = QGuiApplication.primaryScreen()
        if primary is None:  # pragma: no cover - headless fallback
            return x, y
        area = primary.availableGeometry()
        return (
            area.x() + max((area.width() - width) // 2, 0),
            area.y() + max((area.height() - height) // 2, 0),
        )

    def _capture_geometry(self) -> None:
        window = self._settings.window
        window.maximized = self.isMaximized()
        if not self.isMaximized():
            geometry = self.normalGeometry()
            window.width = geometry.width()
            window.height = geometry.height()
            window.x = geometry.x()
            window.y = geometry.y()

    def _persist(self) -> None:
        try:
            self._store.save(self._settings)
        except SettingsError as exc:
            log.warning("settings not saved: %s", exc)

    # -- Qt overrides -----------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        app = QApplication.instance()
        closing_down = bool(app is not None and app.closingDown())

        if self._shutdown_requested or closing_down or not self._tray.available():
            self._capture_geometry()
            self._persist()
            super().closeEvent(event)
            return

        self._capture_geometry()
        self._persist()
        event.ignore()
        self._tray.hide_window()

    # -- test helpers -----------------------------------------------------

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def settings_store(self) -> SettingsStore:
        return self._store

    @property
    def console_panel(self) -> ConsolePanel:
        return self._console_panel

    @property
    def provider(self) -> StateProvider:
        return self._provider
