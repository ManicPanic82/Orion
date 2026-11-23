"""Qt-free unit tests for the new Workstation view models."""

from __future__ import annotations

import uuid
from pathlib import Path

from orion.core.service import OrionCore
from orion.core.services import build_default_services
from orion.hardware.manager import HardwareManager
from orion.ui.core_state_provider import CoreStateProvider
from orion.ui.viewmodels.agent_activity_vm import AgentActivityViewModel
from orion.ui.viewmodels.console_vm import ConsoleViewModel
from orion.ui.viewmodels.experience_learning_vm import ExperienceLearningViewModel
from orion.ui.viewmodels.model_manager_vm import ModelManagerViewModel
from orion.ui.viewmodels.projects_vm import ProjectsViewModel
from orion.ui.viewmodels.resident_ai_vm import ResidentAIViewModel
from orion.ui.viewmodels.system_monitor_vm import SystemMonitorViewModel


def _provider(db: Path | None = None) -> CoreStateProvider:
    services = build_default_services(db_path=db)
    return CoreStateProvider(core=OrionCore(services=services))


def test_agent_activity_vm_returns_real_tasks(tmp_path: Path) -> None:
    provider = _provider(tmp_path / "orion.db")
    vm = AgentActivityViewModel(provider)
    assert vm.tasks() == ()
    snapshot = vm.snapshot()
    assert snapshot.is_mock is False


def test_resident_ai_vm_submits_and_logs() -> None:
    provider = _provider()
    console = ConsoleViewModel()
    vm = ResidentAIViewModel(provider, console)

    assert vm.can_send("echo hello") is True
    assert vm.can_send("   ") is False
    result = vm.send("echo hello", str(uuid.uuid4()))
    assert result.accepted is True
    assert result.simulated is False
    messages = vm.messages()
    assert [role for role, _ in messages] == ["user", "agent"]
    assert messages[0][1] == "echo hello"
    assert len(messages[1][1]) > 0

    rejected = vm.send("", str(uuid.uuid4()))
    assert rejected.accepted is False


def test_system_monitor_vm_collects_real_inventory() -> None:
    vm = SystemMonitorViewModel(HardwareManager())
    inventory = vm.inventory()
    assert inventory.gpus  # real collection returns at least the unknown fallback

    refreshed = vm.refresh()
    assert refreshed is not None
    telemetry = vm.telemetry()
    assert telemetry  # telemetry is recorded after refresh


def test_model_manager_vm_reports_status_and_profiles(tmp_path: Path) -> None:
    services = build_default_services(db_path=tmp_path / "orion.db")
    vm = ModelManagerViewModel(services.model_manager)
    # Mock profile is registered + loaded by CoreServices composition in a live core;
    # here the manager starts unloaded, which is a valid status too.
    status = vm.status()
    assert status is not None
    assert vm.profiles() == []


def test_projects_vm_lists_and_registers(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    services = build_default_services()
    vm = ProjectsViewModel(services.project_manager)

    project = vm.register_project("demo", str(root))
    assert project is not None
    assert project.name == "demo"
    assert [p.project_id for p in vm.projects()] == [project.project_id]

    # A rejected registration (outside allowed roots — none configured, so try
    # a non-existent root instead) returns None and logs a warning.
    services2 = build_default_services()
    vm2 = ProjectsViewModel(services2.project_manager)
    assert vm2.register_project("missing", str(tmp_path / "does-not-exist")) is None


def test_experience_learning_vm_lists_empty_pipelines(tmp_path: Path) -> None:
    services = build_default_services(db_path=tmp_path / "orion.db")
    vm = ExperienceLearningViewModel(services.experience_recorder, services.learning_manager)
    assert vm.experiences() == []
    assert vm.datasets() == []
    assert vm.runs() == []
    assert vm.promotions() == []
