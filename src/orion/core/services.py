"""Core application services: agent, tasks, permissions, model, memory, learning.

``CoreServices`` is the in-process composition root for Orion Core. It wires the
subsystems the roadmap phases introduce into the resident agent pipeline:

- :class:`~orion.permissions.gateway.PermissionGateway` — deterministic policy
  enforcement point for every side-effecting capability (Phase 5).
- :class:`~orion.tasks.manager.TaskManager` — durable task engine (Phase 4).
- :class:`~orion.experience.manager.ExperienceRecorder` — durable experience
  capture (Phase 7).
- :class:`~orion.agent.agent.ResidentAgent` — objective/task orchestration
  (Phase 4) that plans via the registry and executes through the executor,
  which gates through the permission gateway (Phase 5).
- :class:`~orion.models.manager.ModelManager` — model profile lifecycle (Phase 3)
  backed by the mock host until a real backend lands.

This module deliberately holds no UI or Qt code: it is pure domain composition,
so the Workstation embeds it and the standalone ``orion-core`` process can own
it the same way.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from orion.agent.agent import ResidentAgent
from orion.capabilities.executor import CapabilityExecutor
from orion.capabilities.mock import register_mock_capabilities
from orion.capabilities.registry import CapabilityRegistry
from orion.experience.manager import ExperienceRecorder
from orion.experience.store import SQLiteExperienceStore
from orion.hardware.manager import HardwareManager
from orion.learning.manager import LearningManager
from orion.memory.manager import MemoryManager
from orion.memory.store import MemoryStore
from orion.models.manager import ModelManager
from orion.models.profile import ModelProfile
from orion.permissions.gateway import PermissionGateway
from orion.permissions.models import AutonomyMode
from orion.projects.manager import ProjectManager
from orion.tasks.manager import TaskManager
from orion.tasks.repository import SQLiteTaskRepository


def _utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


@dataclass(slots=True)
class CoreServices:
    """Composed Core services.

    Attributes mirror the subsystem packages one-to-one; the resident agent
    is the user-facing orchestrator.
    """

    permission_gateway: PermissionGateway
    task_manager: TaskManager
    experience_recorder: ExperienceRecorder
    model_manager: ModelManager
    capability_registry: CapabilityRegistry
    agent: ResidentAgent
    learning_manager: LearningManager
    memory_manager: MemoryManager
    hardware_manager: HardwareManager
    project_manager: ProjectManager
    events: Any = field(default=None)
    startup_timestamp: str = field(default_factory=_utc_now)


def build_default_services(
    *, db_path: Any = None, autonomy: AutonomyMode = AutonomyMode.SUPERVISED
) -> CoreServices:
    """Compose the default Orion Core services (all subsystems wired).

    Tasks, experiences, and memories are durable (SQLite); the model host is
    the labelled mock (real backends land in later phases).
    """
    from orion.config.paths import app_data_dir

    if db_path is None:
        db_path = app_data_dir() / "orion.db"

    gateway = PermissionGateway(mode=autonomy)
    task_manager = TaskManager(repository=SQLiteTaskRepository(db_path))
    experience_recorder = ExperienceRecorder(store=SQLiteExperienceStore(db_path))
    registry = CapabilityRegistry()
    register_mock_capabilities(registry)
    executor = CapabilityExecutor(registry, gateway)
    agent = ResidentAgent(
        task_manager=task_manager,
        registry=registry,
        executor=executor,
        experience_recorder=experience_recorder,
    )
    model_manager = ModelManager()
    hardware_manager = HardwareManager()
    return CoreServices(
        permission_gateway=gateway,
        task_manager=task_manager,
        experience_recorder=experience_recorder,
        model_manager=model_manager,
        capability_registry=registry,
        agent=agent,
        learning_manager=LearningManager(),
        memory_manager=MemoryManager(MemoryStore(db_path)),
        hardware_manager=hardware_manager,
        project_manager=ProjectManager(),
    )


def register_mock_model_profile(model_manager: ModelManager) -> ModelProfile:
    """Register and load the mock model profile (Phase 3 placeholder)."""
    profile = ModelProfile(profile_id="mock-base", base_model="mock")
    registered = model_manager.register(profile)
    model_manager.load(registered)
    return registered
