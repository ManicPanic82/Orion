"""Regression coverage for the security follow-up hardening pass."""

from __future__ import annotations

import json
import threading

import pytest

from orion.agent import ResidentAgent
from orion.agent.models import PlannedStep
from orion.capabilities.executor import CapabilityExecutor
from orion.capabilities.models import Capability, IdempotencyClass
from orion.capabilities.registry import CapabilityRegistry
from orion.core.supervisor import CoreSupervisor, RestartPolicy
from orion.experience import (
    Experience,
    ExperienceAction,
    ExperienceFeedback,
    ExperienceRecorder,
    OutcomeClass,
    PrivacyState,
)
from orion.hardware import HardwareManager
from orion.permissions.gateway import PermissionGateway
from orion.permissions.models import (
    AutonomyMode,
    PermissionDecision,
    PermissionGrant,
)
from orion.tasks.manager import TaskManager
from orion.tasks.models import (
    IdempotencyClass as TaskIdempotency,
    TaskState,
    TaskStep,
    TaskStepState,
)
from orion.tasks.repository import InMemoryTaskRepository, SQLiteTaskRepository


def test_capability_defaults_to_non_idempotent_and_fails_closed() -> None:
    invoked = []
    capability = Capability(
        capability_id="dangerous",
        handler=lambda payload, cancel_event=None: invoked.append(payload),
    )
    assert capability.idempotency is IdempotencyClass.NON_IDEMPOTENT

    registry = CapabilityRegistry()
    registry.register(capability)
    result = CapabilityExecutor(registry).execute(
        TaskStep(capability_id="dangerous", input={"operation": "delete"})
    )
    assert result["success"] is False
    assert result["error_code"] == "permission_unavailable"
    assert invoked == []


def test_scoped_read_only_capability_requires_matching_grant() -> None:
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            capability_id="read_secret",
            idempotency=IdempotencyClass.READ_ONLY,
            required_scopes=["secrets.read"],
            handler=lambda payload, cancel_event=None: {"read": True},
        )
    )
    gateway = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    executor = CapabilityExecutor(registry, gateway)
    step = TaskStep(capability_id="read_secret", input={"path": "vault/item"})

    gateway.add_grant(
        PermissionGrant(
            capability_id="read_secret",
            action="read_secret",
            resource="vault/item",
            scope="",
        )
    )
    denied = executor.execute(step)
    assert denied["success"] is False
    assert denied["error_code"] == "permission_denied"

    gateway.add_grant(
        PermissionGrant(
            capability_id="read_secret",
            action="read_secret",
            resource="vault/item",
            scope="secrets.read",
        )
    )
    allowed = executor.execute(step)
    assert allowed["success"] is True


def test_grant_constraints_and_path_wildcards_are_segment_aware() -> None:
    grant = PermissionGrant(
        capability_id="write_file",
        action="write",
        scope="project",
        resource="C:/Projects/Trusted/*",
        constraints={"path": "C:/Projects/Trusted/file.txt"},
    )
    assert grant.matches(
        "write_file",
        "C:\\Projects\\Trusted\\file.txt",
        action="write",
        scope="project",
        args={"path": "C:/Projects/Trusted/file.txt"},
    )
    assert not grant.matches(
        "write_file",
        "C:\\Projects\\TrustedEvil\\file.txt",
        action="write",
        scope="project",
        args={"path": "C:/Projects/TrustedEvil/file.txt"},
    )
    assert not grant.matches(
        "write_file",
        "C:/Projects/Trusted/../TrustedEvil/file.txt",
        action="write",
        scope="project",
        args={"path": "C:/Projects/Trusted/../TrustedEvil/file.txt"},
    )
    assert not grant.matches(
        "write_file",
        "C:/Projects/Trusted/file.txt",
        action="write",
        scope="project",
        args={"path": "C:/Projects/Trusted/other.txt"},
    )


def test_explicit_approval_is_bound_to_task_and_step() -> None:
    gateway = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    approval = gateway.request_approval(
        capability_id="write_file",
        resource="/tmp/x",
        task_id="task-1",
        step_id="step-1",
        args={"path": "/tmp/x"},
    )
    gateway.approve(approval.approval_id)

    decision = gateway.decide(
        "write_file",
        "/tmp/x",
        task_id="task-2",
        step_id="step-1",
        args={"path": "/tmp/x"},
        approval_id=approval.approval_id,
        idempotency="non_idempotent",
    )
    assert decision.decision is PermissionDecision.DENY


def test_explicit_approval_empty_resource_is_not_a_wildcard() -> None:
    gateway = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    approval = gateway.request_approval(capability_id="write_file", resource="")
    gateway.approve(approval.approval_id)

    decision = gateway.decide(
        "write_file",
        "/outside/target",
        approval_id=approval.approval_id,
        idempotency="non_idempotent",
    )
    assert decision.decision is PermissionDecision.DENY


def test_unknown_explicit_approval_id_is_denied() -> None:
    gateway = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    decision = gateway.decide(
        "write_file",
        "/tmp/x",
        approval_id="not-a-real-approval",
        idempotency="non_idempotent",
    )
    assert decision.decision is PermissionDecision.DENY


def test_invalid_planner_idempotency_is_rejected() -> None:
    class InvalidPlanner:
        def plan(self, objective, available_capabilities):
            return [PlannedStep(capability_id="write_file", idempotency="pretend_read_only")]

    agent = ResidentAgent(
        task_manager=TaskManager(repository=InMemoryTaskRepository()),
        planner=InvalidPlanner(),
    )
    objective = agent.submit_objective("perform a file operation")
    with pytest.raises(ValueError, match="invalid idempotency"):
        agent.create_task_from_objective(objective)


def test_task_step_default_is_non_idempotent() -> None:
    assert TaskStep().idempotency is TaskIdempotency.NON_IDEMPOTENT


def test_durable_request_deduplication_survives_restart(tmp_path) -> None:
    database = tmp_path / "orion.db"
    first = TaskManager(repository=SQLiteTaskRepository(database))
    task = first.create_task(first.create_objective("first request"), request_id="request-1")

    restarted = TaskManager(repository=SQLiteTaskRepository(database))
    duplicate = restarted.create_task(
        restarted.create_objective("duplicate request"), request_id="request-1"
    )
    assert duplicate.task_id == task.task_id
    assert len(restarted.list_tasks()) == 1


def test_unsafe_running_task_is_quarantined_and_not_resumed() -> None:
    manager = TaskManager(repository=InMemoryTaskRepository())
    step = TaskStep(
        capability_id="charge_card",
        idempotency=TaskIdempotency.NON_IDEMPOTENT,
    )
    task = manager.create_task(manager.create_objective("charge"), steps=[step])
    manager.update_task(task.task_id, state=TaskState.RUNNING)
    manager.update_step(task.task_id, step.step_id, state=TaskStepState.RUNNING)

    recovered = manager.recover_task(task.task_id)
    assert recovered.recovery_safe is False
    assert recovered.state is TaskState.PAUSED
    assert recovered.failure_code == "unsafe_recovery_requires_review"

    class MustNotExecute:
        def execute(self, *args, **kwargs):
            raise AssertionError("quarantined task must not execute")

    registry = CapabilityRegistry()
    registry.register(
        Capability(
            capability_id="charge_card",
            idempotency=IdempotencyClass.NON_IDEMPOTENT,
        )
    )
    agent = ResidentAgent(
        task_manager=manager, registry=registry, executor=MustNotExecute()
    )
    assert agent.run_task(task.task_id).state is TaskState.PAUSED


def test_supervisor_terminates_running_child_on_shutdown() -> None:
    started = threading.Event()
    stop = threading.Event()
    result = []

    class Child:
        terminated = False

        def poll(self):
            return -15 if self.terminated else None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return self.poll()

    child = Child()

    def spawn():
        started.set()
        return child

    supervisor = CoreSupervisor(
        RestartPolicy(max_restarts=2, initial_delay_s=0, max_delay_s=0)
    )
    thread = threading.Thread(
        target=lambda: result.append(supervisor.supervise(spawn, stop_event=stop))
    )
    thread.start()
    assert started.wait(1)
    stop.set()
    thread.join(2)

    assert not thread.is_alive()
    assert child.terminated is True
    assert result == [0]


def test_feedback_and_nested_action_data_are_redacted() -> None:
    recorder = ExperienceRecorder()
    experience = recorder.capture_experience(
        objective_id="objective",
        task_id="task",
        outcome=OutcomeClass.SUCCESS,
        actions=[
            ExperienceAction(
                capability_id="read_secret",
                input={"nested": {"token": "action-secret"}},
            )
        ],
        metadata={"nested": {"token": "metadata-secret"}},
    )
    recorder.add_feedback(experience.experience_id, "feedback-secret")
    recorder.redact(
        experience.experience_id,
        ["metadata.token", "actions.input.token", "feedback.content"],
    )

    stored = recorder.get(experience.experience_id)
    assert stored is not None
    assert stored.metadata["nested"]["token"] == "[REDACTED]"
    assert stored.actions[0].input["nested"]["token"] == "[REDACTED]"
    assert stored.feedback[0].content == "[REDACTED]"
    recorder.add_feedback(experience.experience_id, "later-feedback-secret")
    assert recorder.get(experience.experience_id).feedback[-1].content == "[REDACTED]"
    exported = json.dumps(recorder.export(), sort_keys=True)
    for secret in ("action-secret", "metadata-secret", "feedback-secret", "later-feedback-secret"):
        assert secret not in exported


def test_hardware_inventory_reports_multiple_gpus_and_windows_os(monkeypatch) -> None:
    def query(self, script, timeout=15.0):
        if "Win32_Processor" in script:
            return "Test CPU"
        if "TotalPhysicalMemory" in script:
            return str(32 * 1024**3)
        if "Win32_OperatingSystem" in script:
            return json.dumps(
                {"Caption": "Microsoft Windows 11 Pro", "Version": "10.0", "BuildNumber": "22631"}
            )
        if "Win32_VideoController" in script:
            return json.dumps(
                [
                    {
                        "Name": "NVIDIA GeForce RTX 4090",
                        "DriverVersion": "555.1",
                        "PNPDeviceID": "GPU-0",
                        "AdapterRAM": 4 * 1024**3,
                    },
                    {
                        "Name": "Intel UHD Graphics",
                        "DriverVersion": "31.0",
                        "PNPDeviceID": "GPU-1",
                        "AdapterRAM": 512 * 1024**2,
                    },
                ]
            )
        if "nvidia-smi" in script:
            return "NVIDIA GeForce RTX 4090, 24564, 555.1, GPU-0"
        return ""

    monkeypatch.setattr(HardwareManager, "_run_query", query)
    inventory = HardwareManager().collect_inventory()
    assert inventory.os_version == "Microsoft Windows 11 Pro 10.0 22631"
    assert inventory.ram_mb == 32768
    assert len(inventory.gpus) == 2
    assert inventory.gpus[0].memory_mb == 24564
    assert inventory.gpus[0].driver_version == "555.1"
    assert inventory.gpus[1].name == "Intel UHD Graphics"


def test_evaluation_cannot_accept_caller_supplied_pass_result() -> None:
    from orion.learning import LearningManager

    metrics = {
        "accuracy": 0.99,
        "held_out": True,
        "eval_dataset_checksum": "test-checksum",
        "eval_examples": 10,
    }
    with pytest.raises(ValueError, match="evaluator output"):
        LearningManager().evaluate_candidate("candidate", metrics=metrics, passed=True)



def test_empty_grant_selectors_do_not_mean_global_access() -> None:
    grant = PermissionGrant()
    assert not grant.matches(
        "write_file",
        "/etc/passwd",
        action="delete",
        scope="global",
        args={"path": "/etc/passwd"},
    )



def test_redacted_experience_export_masks_legacy_nested_feedback() -> None:
    experience = Experience(
        privacy_state=PrivacyState.REDACTED,
        redacted_fields=["feedback.content", "actions.input.token", "metadata.token"],
        actions=[
            ExperienceAction(
                capability_id="read_secret",
                input={"nested": {"token": "legacy-action-secret"}},
            )
        ],
        feedback=[ExperienceFeedback(content="legacy-feedback-secret")],
        metadata={"nested": {"token": "legacy-metadata-secret"}},
    )
    exported = json.dumps(experience.as_dict(redact=True), sort_keys=True)
    assert "legacy-action-secret" not in exported
    assert "legacy-feedback-secret" not in exported
    assert "legacy-metadata-secret" not in exported
    assert experience.feedback[0].content == "legacy-feedback-secret"
    assert experience.metadata["nested"]["token"] == "legacy-metadata-secret"



def test_returned_permission_objects_cannot_mutate_gateway_policy() -> None:
    gateway = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    grant = gateway.add_grant(
        PermissionGrant(
            capability_id="write_file",
            action="write_file",
            resource="/safe",
            scope="project",
        )
    )
    grant.resource = "*"
    grant.capability_id = "*"
    decision = gateway.decide(
        "write_file",
        "/outside",
        scope="project",
        idempotency="non_idempotent",
    )
    assert decision.decision is PermissionDecision.DENY

    approval = gateway.request_approval(
        capability_id="delete_file",
        resource="/safe",
        task_id="task-1",
        step_id="step-1",
    )
    approval.resource = "/outside"
    approved = gateway.approve(approval.approval_id)
    approved.resource = "/outside"
    decision = gateway.decide(
        "delete_file",
        "/outside",
        task_id="task-1",
        step_id="step-1",
        approval_id=approval.approval_id,
        idempotency="non_idempotent",
    )
    assert decision.decision is PermissionDecision.DENY



def test_capability_registry_does_not_expose_mutable_security_metadata() -> None:
    capability = Capability(capability_id="write_file")
    registry = CapabilityRegistry()
    registry.register(capability)

    capability.idempotency = IdempotencyClass.READ_ONLY
    returned = registry.get("write_file")
    returned.idempotency = IdempotencyClass.READ_ONLY
    assert registry.get("write_file").idempotency is IdempotencyClass.NON_IDEMPOTENT



def test_in_memory_task_repository_does_not_expose_mutable_records() -> None:
    manager = TaskManager(repository=InMemoryTaskRepository())
    step = TaskStep(
        capability_id="write_file",
        idempotency=TaskIdempotency.NON_IDEMPOTENT,
    )
    task = manager.create_task(manager.create_objective("write"), steps=[step])
    task.steps[0].idempotency = TaskIdempotency.READ_ONLY
    loaded = manager.get_task(task.task_id)
    assert loaded.steps[0].idempotency is TaskIdempotency.NON_IDEMPOTENT
    loaded.steps[0].idempotency = TaskIdempotency.READ_ONLY
    assert manager.get_task(task.task_id).steps[0].idempotency is TaskIdempotency.NON_IDEMPOTENT



def test_returned_experience_snapshot_cannot_remove_privacy_controls() -> None:
    recorder = ExperienceRecorder()
    returned = recorder.capture_experience(
        objective_id="objective",
        task_id="task",
        outcome=OutcomeClass.SUCCESS,
        metadata={"request": "private-request"},
    )
    recorder.redact(returned.experience_id, ["request"])
    returned.redacted_fields.clear()
    returned.privacy_state = PrivacyState.APPROVED
    returned.metadata["request"] = "mutated-secret"

    stored = recorder.get(returned.experience_id)
    assert stored.privacy_state is PrivacyState.REDACTED
    assert stored.redacted_fields == ["request"]
    assert stored.metadata["request"] == "[REDACTED]"
