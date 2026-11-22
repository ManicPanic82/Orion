"""Project intelligence manager for Orion."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Any

from orion.projects.models import Project, ProjectBriefing, ProjectState


class ProjectManager:
    def __init__(self, *, allowed_roots: list[str] | None = None) -> None:
        self.allowed_roots = list(allowed_roots or [])
        self._projects: dict[str, Project] = {}
        self._lock = threading.RLock()

    def register_project(self, name: str, root: str, **kwargs: Any) -> Project:
        root_path = Path(root).resolve(strict=False)
        if self.allowed_roots and not any(
            str(root_path).startswith(str(Path(r).resolve())) for r in self.allowed_roots
        ):
            raise ValueError(f"project root {root} is outside allowed roots")
        if not root_path.exists():
            raise ValueError(f"project root does not exist: {root}")
        project = Project(name=name, root=str(root_path), **kwargs)
        with self._lock:
            self._projects[project.project_id] = project
        return project

    def get(self, project_id: str) -> Project:
        with self._lock:
            if project_id not in self._projects:
                raise KeyError(f"project not found: {project_id}")
            return self._projects[project_id]

    def list_projects(self) -> list[Project]:
        with self._lock:
            return list(self._projects.values())

    def inspect(self, project_id: str) -> Project:
        project = self.get(project_id)
        root = Path(project.root)
        evidence = []
        try:
            branch = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            project.branch = branch
            evidence.append(f"branch:{branch}")
        except Exception:
            project.branch = None
            project.state = ProjectState.ERROR
        try:
            status = subprocess.check_output(
                ["git", "-C", str(root), "status", "--short"], stderr=subprocess.DEVNULL, text=True
            ).strip()
            project.status_summary = status or "clean"
            evidence.append("status")
        except Exception:
            project.status_summary = "unknown"
        try:
            log = subprocess.check_output(
                ["git", "-C", str(root), "log", "--oneline", "-5"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            project.recent_commits = [line for line in log.splitlines() if line.strip()]
            evidence.append("commits")
        except Exception:
            project.recent_commits = []
        import datetime as _dt

        project.last_inspected_at = _dt.datetime.now(_dt.UTC).isoformat()
        project.evidence = evidence
        project.state = ProjectState.INSPECTED if evidence else ProjectState.STALE
        return project

    def briefing(self, project_id: str, *, cached: bool = False) -> ProjectBriefing:
        project = self.get(project_id)
        if project.last_inspected_at is None:
            cached = True
        return ProjectBriefing(
            project_id=project.project_id,
            summary=f"{project.name}: {project.status_summary or 'not inspected'}",
            branch=project.branch,
            status=project.status_summary,
            commits=list(project.recent_commits),
            cached=cached,
            evidence=list(project.evidence),
        )

    def run_test_command(self, project_id: str, executor: Any) -> Any:
        project = self.get(project_id)
        if not project.test_command:
            raise ValueError("no test command configured")
        # Use shell=False; split command.
        import shlex

        parts = shlex.split(project.test_command)
        from orion.automation.models import ExecutionRequest, IdempotencyClass

        req = ExecutionRequest(
            executable=parts[0],
            args=parts[1:],
            working_dir=project.root,
            idempotency=IdempotencyClass.IDEMPOTENT,
        )
        return executor.execute(req)
