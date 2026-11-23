"""Projects (Phase 11): registry and evidence-based briefings."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from orion.projects.manager import ProjectManager
from orion.ui.viewmodels.projects_vm import ProjectsViewModel
from orion.ui.widgets.card import Card

__all__ = ["ProjectsPage"]


class ProjectsPage(QWidget):
    """Project registry + briefing, all read through the manager."""

    def __init__(
        self,
        project_manager: ProjectManager | None,
        view_model: ProjectsViewModel | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ProjectsPage")
        self._vm = view_model or ProjectsViewModel(project_manager or ProjectManager())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Projects", self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        register_card = Card(
            "Register project", "Registers a project root inside allowed roots.", self
        )
        name_input = QLineEdit(register_card)
        name_input.setObjectName("ProjectNameInput")
        name_input.setPlaceholderText("Name")
        root_input = QLineEdit(register_card)
        root_input.setObjectName("ProjectRootInput")
        root_input.setPlaceholderText("Project root path")
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(name_input, 1)
        row.addWidget(root_input, 3)
        self._register_button = QPushButton("Register", self)
        self._register_button.setObjectName("Primary")
        row.addWidget(self._register_button, 0)
        register_card.add_layout(row)
        outer.addWidget(register_card)

        projects_card = Card(
            "Projects", "Registered projects (evidence refreshed via Inspector).", self
        )
        self._projects_list = QListWidget(projects_card)
        self._projects_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._projects_list.currentItemChanged.connect(self._on_project_selected)
        projects_card.add_widget(self._projects_list)
        outer.addWidget(projects_card)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(8)
        self._inspect_button = QPushButton("Inspect", self)
        self._inspect_button.setObjectName("Secondary")
        detail_row.addWidget(self._inspect_button, 0)
        self._detail = QLabel("", self)
        self._detail.setProperty("role", "muted")
        self._detail.setWordWrap(True)
        detail_row.addWidget(self._detail, 1)
        outer.addLayout(detail_row)

        self._selected_id = ""
        self._register_button.clicked.connect(lambda: self._on_register(name_input, root_input))
        self._inspect_button.clicked.connect(self._on_inspect)
        self.refresh()

    def _on_register(self, name_input: QLineEdit, root_input: QLineEdit) -> None:
        project = self._vm.register_project(name_input.text(), root_input.text())
        if project is not None:
            name_input.clear()
            root_input.clear()
            self.refresh()

    def _on_inspect(self) -> None:
        if not self._selected_id:
            return
        self.refresh()

    def _on_project_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        self._selected_id = (
            str(current.data(Qt.ItemDataRole.UserRole)) if current is not None else ""
        )
        self._detail.setText("")

    def refresh(self) -> None:
        projects = self._vm.projects()
        self._projects_list.clear()
        for project in projects:
            item = QListWidgetItem(
                f"{project.name}\n{project.root}\n"
                f"  State: {project.state.value} · Branch: {project.branch or 'unknown'} · "
                f"Status: {project.status_summary or 'unknown'}"
            )
            item.setData(Qt.ItemDataRole.UserRole, project.project_id)
            self._projects_list.addItem(item)
