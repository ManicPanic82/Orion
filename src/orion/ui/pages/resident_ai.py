"""Resident AI: conversation with the resident agent (Phase 4)."""

from __future__ import annotations

import uuid

from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from orion.ui.viewmodels.resident_ai_vm import ResidentAIViewModel
from orion.ui.widgets.card import Card
from orion.ui.widgets.status_pill import StatusPill

__all__ = ["ResidentAIChatPage"]


class ResidentAIChatPage(QWidget):
    """Chat surface: composer + message log driven by the Core objective pipeline."""

    def __init__(self, view_model: ResidentAIViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResidentAIChatPage")
        self._vm = view_model

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Resident AI", self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        status_card = Card("Agent", "Live state of the resident agent.", self)
        row = QHBoxLayout()
        row.setSpacing(8)
        self._status_pill = StatusPill("OPERATIONAL", "operational", status_card)
        row.addWidget(self._status_pill)
        row.addStretch(1)
        self._agent_detail = QLabel("", status_card)
        self._agent_detail.setProperty("role", "muted")
        row.addWidget(self._agent_detail, 1)
        status_card.add_layout(row)
        outer.addWidget(status_card)

        chat_card = Card("Conversation", "Objectives are planned and executed by Orion Core.", self)
        self._log = QTextEdit(chat_card)
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Say an objective; the resident agent plans and executes it.")
        self._log.setObjectName("ChatLog")
        chat_card.add_widget(self._log)
        outer.addWidget(chat_card, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self._input = QLineEdit(self)
        self._input.setObjectName("ChatInput")
        self._input.setPlaceholderText("Describe the outcome you want.")
        self._input.returnPressed.connect(self._on_send)
        input_row.addWidget(self._input, 1)
        self._send = QPushButton("Send", self)
        self._send.setObjectName("Primary")
        self._send.setEnabled(False)
        self._send.clicked.connect(self._on_send)
        input_row.addWidget(self._send, 0)
        outer.addLayout(input_row)

        shortcut = QShortcut("Ctrl+Return", self._input)
        shortcut.activated.connect(self._on_send)

        self._input.textChanged.connect(self._sync_send_state)
        self._sync_send_state()
        self.refresh()

    def refresh(self) -> None:
        status = self._vm.agent_status()
        self._status_pill.set_status_kind(status.kind)
        self._status_pill.setText(status.label)
        self._agent_detail.setText(status.detail)
        messages = self._vm.messages()
        self._log.clear()
        for role, text in messages:
            self._append_message(role, text)
        self._sync_send_state()

    def _append_message(self, role: str, text: str) -> None:
        prefix = "You: " if role == "user" else "Orion: " if role == "agent" else "System: "
        self._log.append(f"{prefix}{text}\n")

    def _sync_send_state(self) -> None:
        self._send.setEnabled(self._vm.can_send(self._input.text()))

    def _on_send(self) -> None:
        text = self._input.text()
        if not self._vm.can_send(text):
            self._append_message("system", "Objective exceeds the character limit; shorten it.")
            self._input.clear()
            return
        result = self._vm.send(text, str(uuid.uuid4()))
        self._append_message("user", text)
        self._append_message("agent" if result.accepted else "system", result.message)
        if result.accepted:
            self._input.clear()
        self.refresh()
