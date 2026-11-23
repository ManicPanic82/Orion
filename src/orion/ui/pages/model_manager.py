"""Model Manager (Phase 3): model profiles and runtime state."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from orion.models.manager import ModelManager
from orion.state.models import StatusKind
from orion.ui.viewmodels.model_manager_vm import ModelManagerViewModel
from orion.ui.widgets.card import Card
from orion.ui.widgets.status_pill import StatusPill

__all__ = ["ModelManagerPage"]


class ModelManagerPage(QWidget):
    """Shows the Model Manager's runtime status and registered profiles."""

    def __init__(self, model_manager: ModelManager | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ModelManagerPage")
        self._vm = ModelManagerViewModel(model_manager or ModelManager())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Model Manager", self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        status_card = Card("Runtime status", "Model Manager state and active profile.", self)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self._status_pill = StatusPill("DEGRADED", "degraded", status_card)
        status_row.addWidget(self._status_pill)
        status_row.addStretch(1)
        self._active_profile_label = QLabel("No profile active.", status_card)
        self._active_profile_label.setProperty("role", "muted")
        status_row.addWidget(self._active_profile_label, 1)
        status_card.add_layout(status_row)
        outer.addWidget(status_card)

        profiles_card = Card(
            "Registered profiles", "Model profiles and their base/adapter configuration.", self
        )
        self._list = QListWidget(profiles_card)
        profiles_card.add_widget(self._list)
        outer.addWidget(profiles_card)

        self._last_error_label = QLabel("", self)
        self._last_error_label.setProperty("role", "muted")
        self._last_error_label.setWordWrap(True)
        outer.addWidget(self._last_error_label)

        self.refresh()

    def refresh(self) -> None:
        status = self._vm.status()
        kind = StatusKind.OPERATIONAL if self._vm.is_ready else StatusKind.DEGRADED
        text = status.state.value.upper()
        if status.is_mock:
            kind = StatusKind.MOCK
            text = f"{text} (mock)"
        self._status_pill.set_status_kind(kind)
        self._status_pill.setText(text)
        self._active_profile_label.setText(
            f"Active profile: {status.active_profile_id}"
            if status.active_profile_id
            else "No active profile"
        )
        self._last_error_label.setText(status.last_error or "")
        self._list.clear()
        for profile in self._vm.profiles():
            base = profile.base_model.identity or "<unnamed base model>"
            item = QListWidgetItem(
                f"{profile.profile_id or profile.name}\n"
                f"  Base: {base} · Adapter: {profile.adapter.requirement.value}"
                + (
                    f" · quantisation: {profile.quantisation}"
                    if profile.quantisation != "none"
                    else ""
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, profile.profile_id or profile.name)
            self._list.addItem(item)
