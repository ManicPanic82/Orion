"""Project intelligence models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ProjectState(StrEnum):
    REGISTERED = "registered"
    INSPECTED = "inspected"
    STALE = "stale"
    ERROR = "error"


@dataclass(slots=True)
class Project:
    project_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    root: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    test_command: str = ""
    excluded_paths: list[str] = field(default_factory=list)
    state: ProjectState = ProjectState.REGISTERED
    last_inspected_at: str | None = None
    branch: str | None = None
    status_summary: str = ""
    recent_commits: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "root": self.root,
            "description": self.description,
            "tags": list(self.tags),
            "test_command": self.test_command,
            "excluded_paths": list(self.excluded_paths),
            "state": self.state.value,
            "last_inspected_at": self.last_inspected_at,
            "branch": self.branch,
            "status_summary": self.status_summary,
            "recent_commits": list(self.recent_commits),
            "evidence": list(self.evidence),
        }


@dataclass(slots=True)
class ProjectBriefing:
    project_id: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    summary: str = ""
    branch: str | None = None
    status: str = ""
    commits: list[str] = field(default_factory=list)
    cached: bool = False
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "branch": self.branch,
            "status": self.status,
            "commits": list(self.commits),
            "cached": self.cached,
            "evidence": list(self.evidence),
        }
