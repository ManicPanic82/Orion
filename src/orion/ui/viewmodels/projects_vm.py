"""Projects view model — project registry and briefing."""

from __future__ import annotations

from orion.config.settings import Severity
from orion.projects.manager import ProjectManager
from orion.projects.models import Project, ProjectBriefing
from orion.ui.viewmodels.console_vm import ConsoleViewModel

__all__ = ["ProjectsViewModel"]


class ProjectsViewModel:
    """Project registry operations and briefing view-model."""

    def __init__(
        self, project_manager: ProjectManager, console: ConsoleViewModel | None = None
    ) -> None:
        self._project_manager = project_manager
        self._console = console

    def projects(self) -> list[Project]:
        return self._project_manager.list_projects()

    def inspect(self, project_id: str) -> Project:
        return self._project_manager.inspect(project_id)

    def briefing(self, project_id: str) -> ProjectBriefing:
        return self._project_manager.briefing(project_id)

    def register_project(self, name: str, root: str) -> Project | None:
        try:
            return self._project_manager.register_project(name, root)
        except ValueError as exc:
            if self._console is not None:
                self._console.append(Severity.WARNING, "projects", str(exc))
            return None
