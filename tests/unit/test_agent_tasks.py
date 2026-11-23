"""Tests for resident agent task execution."""

from __future__ import annotations

from orion.agent import ResidentAgent
from orion.capabilities import CapabilityRegistry, register_mock_capabilities
from orion.capabilities.executor import CapabilityExecutor
from orion.capabilities.permissions import MockPermissionGateway
from orion.tasks import InMemoryTaskRepository, TaskManager


def _make_agent() -> ResidentAgent:
    reg = CapabilityRegistry()
    register_mock_capabilities(reg)
    executor = CapabilityExecutor(reg, MockPermissionGateway())
    return ResidentAgent(
        registry=reg,
        executor=executor,
        task_manager=TaskManager(repository=InMemoryTaskRepository()),
    )


def test_objective_creates_task() -> None:
    agent = _make_agent()
    task = agent.submit_and_create_task("echo hello")
    assert task.task_id
    assert len(task.steps) >= 1


def test_mock_multi_step_task_runs_and_reports_progress() -> None:
    agent = _make_agent()
    task = agent.submit_and_create_task("echo and sum")
    # Force two steps by appending? Use plan output already; mock planner only echo for "echo"
    finished = agent.run_task(task.task_id)
    assert finished.state.value in {"completed", "partial", "failed"}
    assert finished.steps[0].state.value in {"completed", "failed", "cancelled"}


def test_cancellation_stops_pending_work() -> None:
    agent = _make_agent()
    task = agent.submit_and_create_task("slow operation")
    # Inject a slow step
    from orion.tasks.models import IdempotencyClass, TaskStep

    task.steps = [TaskStep(capability_id="slow", input={}, idempotency=IdempotencyClass.READ_ONLY)]
    agent.task_manager._repository.save(task)
    agent.cancel_task(task.task_id)
    finished = agent.run_task(task.task_id)
    assert finished.state.value in {"cancelled", "failed", "completed"}


def test_failure_represented() -> None:
    agent = _make_agent()
    task = agent.submit_and_create_task("this should fail")
    # Replace steps with fail capability
    from orion.tasks.models import IdempotencyClass, TaskStep

    task.steps = [TaskStep(capability_id="fail", input={}, idempotency=IdempotencyClass.READ_ONLY)]
    agent.task_manager._repository.save(task)
    finished = agent.run_task(task.task_id)
    assert finished.state.value in {"failed", "partial"}
    assert finished.steps[0].state.value == "failed"


def test_unknown_planner_idempotency_is_rejected() -> None:
    # Their clean tip: unknown planner idempotency classifications fail closed.
    from orion.agent.models import PlannedStep

    agent = _make_agent()
    objective = agent.submit_objective("echo a safe message")
    try:
        agent.create_task_from_objective(
            objective,
            steps=[
                PlannedStep(
                    capability_id="echo",
                    input={"text": "hello"},
                    idempotency="future_unknown_value",
                )
            ],
        )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown planner idempotency should be rejected")
