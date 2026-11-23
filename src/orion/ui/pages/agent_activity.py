"""Agent Activity: the real task list from Orion Core."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from orion.ui.viewmodels.agent_activity_vm import AgentActivityViewModel
from orion.ui.widgets.card import Card

__all__ = ["AgentActivityPage"]


class AgentActivityPage(QWidget):
    """Renders the authoritative task list from the provider snapshot."""

    def __init__(self, view_model: AgentActivityViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AgentActivityPage")
        self._vm = view_model

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Agent Activity", self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        card = Card(
            "Tasks",
            "Real task state from the Orion Core task engine, live from Core.",
            self,
        )
        outer.addWidget(card)

        self._list = QListWidget(card)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        card.add_widget(self._list)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        self._refresh_button = QPushButton("Refresh", self)
        self._refresh_button.setObjectName("Secondary")
        self._refresh_button.clicked.connect(self.refresh)
        row.addWidget(self._refresh_button, 0)
        outer.addLayout(row)

        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        tasks = self._vm.tasks()
        if not tasks:
            empty = QListWidgetItem("No tasks yet.")
            empty.setText("No tasks yet — submit an objective from the Command Centre.")
            self._list.addItem(empty)
            return
        for task in tasks:
            self._list.addItem(self._format_row(task))

    def _format_row(self, task: object) -> QListWidgetItem:
        summary = task
        text = f"{summary.state.value.upper():<9} {summary.title or summary.task_id[:8]}"
        if summary.note:
            text += f"\n{summary.note}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, summary.task_id)
        return item

    def selected_task_id(self) -> str | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole))
