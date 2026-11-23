"""Command Centre: status, tasks, activity, and the command composer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from orion.state.models import ComponentStatus, EventRecord, StatusKind, TaskSummary
from orion.ui.viewmodels.command_centre_vm import COMMAND_MAX_LENGTH, CommandCentreViewModel
from orion.ui.widgets.card import Card
from orion.ui.widgets.mock_badge import MockBadge
from orion.ui.widgets.status_pill import StatusPill

__all__ = ["CommandCentrePage"]

_PILL_TEXT: dict[StatusKind, str] = {
    StatusKind.MOCK: "MOCK",
    StatusKind.OPERATIONAL: "OPERATIONAL",
    StatusKind.DEGRADED: "DEGRADED",
    StatusKind.UNAVAILABLE: "UNAVAILABLE",
}


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
            continue
        child = item.layout()
        if child is not None:
            _clear_layout(child)
            child.deleteLater()


class CommandCentrePage(QWidget):
    """Renders authoritative state from the command-centre view model."""

    def __init__(self, view_model: CommandCentreViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CommandCentrePage")
        self._vm = view_model

        self._agent_pill: StatusPill
        self._agent_detail: QLabel
        self._model_pill: StatusPill
        self._model_detail: QLabel
        self._tasks_box: QVBoxLayout
        self._events_box: QVBoxLayout
        self._composer: QPlainTextEdit
        self._submit: QPushButton
        self._result_label: QLabel

        self._build()
        self.refresh()

    # -- construction -----------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        heading = QHBoxLayout()
        heading.setSpacing(10)
        title = QLabel("Command Centre", self)
        title.setProperty("role", "display")
        heading.addWidget(title)
        heading.addWidget(MockBadge(self))
        heading.addStretch(1)
        outer.addLayout(heading)

        subtitle = QLabel(
            "Orion Workstation with the resident agent connected: objectives "
            "run through the permission gateway and the durable task engine.",
            self,
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        status_row = QHBoxLayout()
        status_row.setSpacing(16)
        agent_card, self._agent_pill, self._agent_detail = self._status_card("Resident Agent")
        model_card, self._model_pill, self._model_detail = self._status_card("Model Runtime")
        status_row.addWidget(agent_card, 1)
        status_row.addWidget(model_card, 1)
        outer.addLayout(status_row)

        middle = QHBoxLayout()
        middle.setSpacing(16)

        tasks_card = Card(
            "Active tasks",
            "Rows created by simulated submissions. Nothing here has executed.",
            self,
        )
        self._tasks_box = tasks_card.body_layout()
        middle.addWidget(tasks_card, 3)

        events_card = Card("Recent events", "Newest first. Authoritative state is mock.", self)
        self._events_box = events_card.body_layout()
        middle.addWidget(events_card, 2)

        outer.addLayout(middle, 1)

        composer_card = Card("Objective", "Phase 1 accepts text only, and executes nothing.", self)
        self._composer = QPlainTextEdit(self)
        self._composer.setObjectName("Composer")
        self._composer.setPlaceholderText(
            "Describe the outcome you want. Submissions are recorded locally as simulated."
        )
        self._composer.setFixedHeight(84)
        self._composer.setTabChangesFocus(True)
        self._composer.textChanged.connect(self._sync_submit_state)
        composer_card.add_widget(self._composer)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._result_label = QLabel("", self)
        self._result_label.setProperty("role", "muted")
        self._result_label.setWordWrap(True)
        actions.addWidget(self._result_label, 1)

        self._submit = QPushButton("Submit objective", self)
        self._submit.setObjectName("Primary")
        self._submit.setEnabled(False)
        self._submit.clicked.connect(self._on_submit)
        actions.addWidget(self._submit, 0)
        composer_card.add_layout(actions)

        outer.addWidget(composer_card)

        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self._composer)
        shortcut.activated.connect(self._on_submit)

        self._sync_submit_state()

    def _status_card(self, label: str) -> tuple[Card, StatusPill, QLabel]:
        card = Card(label, None, self)
        row = QHBoxLayout()
        row.setSpacing(8)
        pill = StatusPill("MOCK", "mock", card)
        row.addWidget(pill)
        row.addStretch(1)
        card.add_layout(row)

        detail = QLabel("", card)
        detail.setProperty("role", "muted")
        detail.setWordWrap(True)
        card.add_widget(detail)
        return card, pill, detail

    # -- behaviour --------------------------------------------------------

    def _sync_submit_state(self) -> None:
        text = self._composer.toPlainText()
        self._submit.setEnabled(self._vm.can_submit(text))
        if len(text.strip()) > COMMAND_MAX_LENGTH:
            self._result_label.setText(
                f"Objective exceeds {COMMAND_MAX_LENGTH} characters; shorten it to submit."
            )

    def _on_submit(self) -> None:
        if not self._vm.can_submit(self._composer.toPlainText()):
            return
        result = self._vm.submit(self._composer.toPlainText())
        self._result_label.setText(result.message)
        if result.accepted:
            self._composer.clear()
        self.refresh()

    def refresh(self) -> None:
        snapshot = self._vm.snapshot()
        self._apply_status(snapshot.agent, self._agent_pill, self._agent_detail)
        self._apply_status(snapshot.model, self._model_pill, self._model_detail)
        self._render_tasks(snapshot.tasks)
        self._render_events(snapshot.events)

    # -- rendering --------------------------------------------------------

    @staticmethod
    def _apply_status(status: ComponentStatus, pill: StatusPill, detail: QLabel) -> None:
        pill.setText(_PILL_TEXT[status.kind])
        pill.set_status_kind(status.kind)
        detail.setText(status.detail)

    def _render_tasks(self, tasks: tuple[TaskSummary, ...]) -> None:
        _clear_layout(self._tasks_box)
        if not tasks:
            empty = QLabel("No tasks. The task engine arrives in Phase 4.", self)
            empty.setProperty("role", "muted")
            empty.setWordWrap(True)
            self._tasks_box.addWidget(empty)
            self._tasks_box.addStretch(1)
            return

        for task in reversed(tasks):
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(10)

            identifier = QLabel(task.task_id, row)
            identifier.setProperty("role", "mono")
            row_layout.addWidget(identifier)

            title = QLabel(task.title, row)
            title.setWordWrap(True)
            row_layout.addWidget(title, 1)

            pill = StatusPill("SIMULATED", "mock", row)
            row_layout.addWidget(pill)

            self._tasks_box.addWidget(row)

            note = QLabel(task.note, self)
            note.setProperty("role", "muted")
            note.setWordWrap(True)
            self._tasks_box.addWidget(note)

        self._tasks_box.addStretch(1)

    def _render_events(self, events: tuple[EventRecord, ...]) -> None:
        _clear_layout(self._events_box)
        if not events:
            empty = QLabel("No events recorded.", self)
            empty.setProperty("role", "muted")
            self._events_box.addWidget(empty)
            self._events_box.addStretch(1)
            return

        for event in reversed(events[-6:]):
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)

            stamp = QLabel(event.timestamp.astimezone().strftime("%H:%M:%S"), row)
            stamp.setProperty("role", "mono")
            row_layout.addWidget(stamp)

            source = QLabel(event.source, row)
            source.setProperty("role", "muted")
            source.setMinimumWidth(70)
            row_layout.addWidget(source)

            message = QLabel(event.message, row)
            message.setWordWrap(True)
            message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row_layout.addWidget(message, 1)

            self._events_box.addWidget(row)

        self._events_box.addStretch(1)

    # -- test helpers -----------------------------------------------------

    def composer(self) -> QPlainTextEdit:
        return self._composer

    def submit_button(self) -> QPushButton:
        return self._submit

    def result_text(self) -> str:
        return self._result_label.text()
