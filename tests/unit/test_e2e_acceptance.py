"""E2E acceptance: their complete-user-workflow criteria on Windows.

Covers shutdown/recovery durability, the permissions UX flow, real hardware
operation, and the learning promotion pipeline.
"""

from __future__ import annotations

from pathlib import Path

from orion.capabilities.executor import CapabilityExecutor
from orion.core.service import OrionCore
from orion.core.services import build_default_services
from orion.experience import ExperienceRecorder, OutcomeClass, PrivacyState, QualityState
from orion.hardware import HardwareManager
from orion.learning import LearningManager
from orion.models import ModelProfile
from orion.permissions import PermissionDecision, PermissionGrant
from orion.tasks.models import TaskStep


def test_shutdown_and_recovery_preserves_state(tmp_path: Path) -> None:
    db = tmp_path / "orion.db"
    core = OrionCore(services=build_default_services(db_path=db))
    core.start()
    task = core.submit_objective("echo hello")
    core.run_task(task.task_id)
    core.stop()

    restarted = OrionCore(services=build_default_services(db_path=db))
    restarted.start()
    try:
        ids = {t.task_id for t in restarted.services.task_manager.list_tasks()}
        assert task.task_id in ids
        assert len(restarted.services.experience_recorder.list_experiences()) >= 1

        # Durable request deduplication: repeat the request, same task.
        first = restarted.submit_objective("echo hello", request_id="req-1")
        second = restarted.submit_objective("echo hello", request_id="req-1")
        assert first.task_id == second.task_id
    finally:
        restarted.stop()


def test_permissions_ux_flow_via_gateway() -> None:
    services = build_default_services()
    gateway = services.permission_gateway

    # An approval issued through the gateway allows a bound, matching request.
    approval = gateway.request_approval(
        capability_id="write_file", resource="/vault/item.txt", ttl_seconds=300
    )
    gateway.approve(approval.approval_id)
    decision = gateway.decide("write_file", "/vault/item.txt", idempotency="non_idempotent")
    assert decision.decision is PermissionDecision.ALLOW


def test_permissions_executor_flow_e2e() -> None:
    services = build_default_services()
    executor = CapabilityExecutor(services.capability_registry, services.permission_gateway)
    step = TaskStep(capability_id="write_file", input={"path": "C:/vault/item.txt"})

    # write_file is risk=HIGH and requires the files.write scope: denied by
    # default with no grants.
    denied = executor.execute(step)
    assert denied["success"] is False

    # Granting scope=files.write (with a matching resource) allows the call.
    services.permission_gateway.add_grant(
        PermissionGrant(
            capability_id="write_file",
            action="write_file",
            resource="*",
            scope="files.write",
        )
    )
    allowed = executor.execute(step)
    assert allowed["success"] is True


def test_hardware_operation() -> None:
    inventory = HardwareManager().collect_inventory()
    assert inventory.gpus
    assert inventory.os_version or inventory.cpu
    assert inventory.inventory_id


def test_learning_promotion_e2e() -> None:
    recorder = ExperienceRecorder()
    for i in range(2):
        exp = recorder.capture_experience(
            objective_id=f"o{i}", task_id=f"t{i}", outcome=OutcomeClass.SUCCESS
        )
        recorder.review_privacy(exp.experience_id, PrivacyState.APPROVED)
        recorder.review_quality(exp.experience_id, QualityState.APPROVED)

    lm = LearningManager()
    dataset = lm.build_dataset(recorder.list_experiences())
    run = lm.submit_training(dataset, base_model_revision="rev1")
    assert run.status.value == "completed"

    ev = lm.evaluate_candidate(
        "mock-base",
        metrics={
            "accuracy": 0.9,
            "held_out": True,
            "dataset_id": dataset.dataset_id,
            "eval_dataset_checksum": dataset.checksum,
            "eval_examples": len(dataset.eval_ids),
        },
    )
    assert ev.passed is True

    record = lm.promote_candidate(
        ModelProfile(profile_id="mock-base"), evaluation=ev, approved=True
    )
    assert record.status.value == "approved"


def test_objective_flow_end_to_end(tmp_path: Path) -> None:
    services = build_default_services(db_path=tmp_path / "orion.db")
    assert services.model_manager.is_ready is False  # before explicit load

    from orion.core.services import register_mock_model_profile

    register_mock_model_profile(services.model_manager)
    assert services.model_manager.is_ready is True

    core = OrionCore(services=services)
    core.start()
    try:
        task = core.submit_objective("echo hello")
        finished = core.run_task(task.task_id)
        assert finished.state.value == "completed"
        assert len(services.experience_recorder.list_experiences()) >= 1
    finally:
        core.stop()
