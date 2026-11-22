"""Settings destination: storage facts, lifecycle behaviour, and login startup.

Only controls with real effects appear here. In Phase 1 that is the login
autostart toggle, which reflects the registry rather than assuming it worked;
everything else reports facts the application actually knows.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from orion import PHASE_LABEL, __version__
from orion.config.paths import app_data_dir
from orion.config.settings import Settings
from orion.config.store import SettingsStore
from orion.startup import StartupController, StartupStatus
from orion.ui.widgets.card import Card
from orion.ui.widgets.mock_badge import MockBadge

__all__ = ["SettingsPage"]


class SettingsPage(QWidget):
    """Read-only diagnostics plus the startup control."""

    def __init__(
        self,
        store: SettingsStore,
        settings: Settings,
        startup: StartupController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        self._store = store
        self._settings = settings
        self._startup = startup
        self._startup_checkbox: QCheckBox | None = None
        self._startup_note: QLabel | None = None
        self._startup_error: QLabel | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Settings", self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        subtitle = QLabel(
            "Phase 1 persists presentation preferences only. Domain settings arrive "
            "with the subsystems that own them.",
            self,
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        storage = Card("Storage", None, self)
        storage.add_widget(self._value_row("Settings file", str(store.path), storage))
        storage.add_widget(self._value_row("Data directory", str(app_data_dir()), storage))
        outer.addWidget(storage)

        lifecycle = Card("Window and lifecycle", None, self)
        lifecycle_body = QLabel(
            "Closing the window minimises Orion to the notification area, and the "
            "process keeps running. If Windows reports no notification area, closing "
            "exits instead, so Orion can never become unreachable. Quit from the tray "
            "menu, or press Ctrl+Q while the window is open. Launching Orion again "
            "always brings the window back.",
            lifecycle,
        )
        lifecycle_body.setWordWrap(True)
        lifecycle.add_widget(lifecycle_body)
        outer.addWidget(lifecycle)

        if startup is not None:
            outer.addWidget(self._build_startup_card(startup))

        about = Card("About", None, self)
        about.add_header_widget(MockBadge(about))
        about.add_widget(self._value_row("Version", __version__, about))
        about.add_widget(self._value_row("Stage", PHASE_LABEL, about))
        about.add_widget(self._value_row("Persistence", "Versioned JSON, schema 1", about))
        note = QLabel(
            "No model runtime, agent, automation, or network access exists in this phase.",
            about,
        )
        note.setProperty("role", "muted")
        note.setWordWrap(True)
        about.add_widget(note)
        outer.addWidget(about)

        outer.addStretch(1)

    # -- startup ----------------------------------------------------------

    def _build_startup_card(self, startup: StartupController) -> Card:
        card = Card("Startup", None, self)

        checkbox = QCheckBox("Start Orion when I sign in", card)
        checkbox.setChecked(startup.status().desired)
        checkbox.toggled.connect(self._on_startup_toggled)
        card.add_widget(checkbox)
        self._startup_checkbox = checkbox

        command = QLabel(startup.registration.command, card)
        command.setProperty("role", "mono")
        command.setWordWrap(True)
        command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card.add_widget(command)

        note = QLabel("", card)
        note.setProperty("role", "muted")
        note.setWordWrap(True)
        card.add_widget(note)
        self._startup_note = note

        error = QLabel("", card)
        error.setProperty("role", "muted")
        error.setProperty("tone", "danger")
        error.setWordWrap(True)
        error.setVisible(False)
        card.add_widget(error)
        self._startup_error = error

        self.refresh_startup()
        return card

    def _on_startup_toggled(self, checked: bool) -> None:
        if self._startup is None:
            return
        status = self._startup.set_enabled(checked)
        if status.desired != checked and self._startup_checkbox is not None:
            checkbox = self._startup_checkbox
            checkbox.blockSignals(True)
            checkbox.setChecked(status.desired)
            checkbox.blockSignals(False)
        self._render_startup(status)

    def refresh_startup(self) -> None:
        if self._startup is None:
            return
        self._render_startup(self._startup.status())

    def _render_startup(self, status: StartupStatus) -> None:
        if (
            self._startup_checkbox is not None
            and self._startup_checkbox.isChecked() != status.desired
        ):
            self._startup_checkbox.blockSignals(True)
            self._startup_checkbox.setChecked(status.desired)
            self._startup_checkbox.blockSignals(False)

        if self._startup_note is not None:
            self._startup_note.setText(status.note)

        if self._startup_error is not None:
            self._startup_error.setText(status.error or "")
            self._startup_error.setVisible(bool(status.error))

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _value_row(label: str, value: str, parent: QWidget) -> QWidget:
        row = QWidget(parent)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        name = QLabel(label, row)
        name.setProperty("role", "muted")
        layout.addWidget(name)

        text = QLabel(value, row)
        text.setProperty("role", "mono")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text)
        return row

    # -- test helpers -----------------------------------------------------

    def startup_checkbox(self) -> QCheckBox | None:
        return self._startup_checkbox

    def startup_note(self) -> str:
        return self._startup_note.text() if self._startup_note is not None else ""
