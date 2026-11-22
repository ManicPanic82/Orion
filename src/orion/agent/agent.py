"""Resident agent orchestration for Orion."""

from __future__ import annotations

import datetime
import threading
from collections.abc import Callable
from typing import Any

from orion.agent.models import VerificationResult
from orion.agent.planner import MockPlanner, Planner
from orion.capabilities.executor import CapabilityExecutor
from orion.capabilities.registry import CapabilityRegistry
from orion.tasks.manager import TaskManager
from orion.tasks.models import IdempotencyClass, Objective, Task, TaskState, TaskStep, TaskStepState


class ResidentAgent:
    def __init__(
        self,
        *,
        task_manager: TaskManager | None = None,
        registry: CapabilityRegistry | None = None,
        planner: Planner | None = None,
        executor: CapabilityExecutor | None = None,
        verifier: Callable[[Task, list[Any]], VerificationResult] | None = None,
    ) -> None:
        self.task_manager = task_manager or TaskManager()
        self.registry = registry or CapabilityRegistry()
        self.planner = planner or MockPlanner()
        self.executor = executor or CapabilityExecutor(self.registry)
        self.verifier = verifier or self._default_verifier
        self._lock = threading.RLock()

    def submit_objective(
        self, request: str, *, request_id: str | None = None, metadata: dict[str, Any] | None = None
    ) -> Objective:
        objective = self.task_manager.create_objective(request, metadata=metadata)
        return objective

    def plan_objective(self, objective: Objective) -> list[Any]:
        available = self.registry.list_ids()
        return self.planner.plan(objective, available)

    def create_task_from_objective(
        self,
        objective: Objective,
        *,
        request_id: str | None = None,
        steps: list[Any] | None = None,
    ) -> Task:
        planned = steps if steps is not None else self.plan_objective(objective)
        task_steps: list[TaskStep] = []
        for i, ps in enumerate(planned):
            from orion.tasks.models import TaskStep

            try:
                idem = IdempotencyClass(ps.idempotency)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"planner returned invalid idempotency classification for "
                    f"{ps.capability_id!r}: {ps.idempotency!r}"
                ) from exc
            task_steps.append(
                TaskStep(
                    task_id="",
                    sequence=i + 1,
                    capability_id=ps.capability_id,
                    input=dict(ps.input),
                    idempotency=idem,
                    timeout_s=ps.timeout_s,
                )
            )
        task = self.task_manager.create_task(
            objective, title=objective.request[:80], steps=task_steps, request_id=request_id
        )
        return task

    def submit_and_create_task(
        self, request: str, *, request_id: str | None = None, metadata: dict[str, Any] | None = None
    ) -> Task:
        objective = self.submit_objective(request, request_id=request_id, metadata=metadata)
        return self.create_task_from_objective(objective, request_id=request_id)

    def run_task(self, task_id: str) -> Task:
        task = self.task_manager.get_task(task_id)
        if task.state is TaskState.CREATED:
            task = self.task_manager.transition_task_state(task_id, TaskState.PLANNED)
        if task.state is TaskState.PLANNED:
            task = self.task_manager.transition_task_state(task_id, TaskState.RUNNING)
        self.task_manager.update_task(
            task_id, started_at=task.started_at or datetime.datetime.now(datetime.UTC).isoformat()
        )

        observations: list[Any] = []
        cancel_event = self.task_manager.cancellation_event(task_id)

        for step in task.steps:
            if cancel_event.is_set():
                if step.state is TaskStepState.PENDING:
                    self.task_manager.transition_step_state(
                        task_id, step.step_id, TaskStepState.CANCELLED
                    )
                continue
            if step.state is not TaskStepState.PENDING:
                continue
            self.task_manager.transition_step_state(task_id, step.step_id, TaskStepState.RUNNING)
            step.started_at = datetime.datetime.now(datetime.UTC).isoformat()
            self.task_manager.update_step(task_id, step.step_id, started_at=step.started_at)

            result = self.executor.execute(step, cancel_event=cancel_event)
            observations.append(result)

            if cancel_event.is_set():
                self.task_manager.transition_step_state(
                    task_id, step.step_id, TaskStepState.CANCELLED
                )
                step.error = "cancelled"
                self.task_manager.update_step(task_id, step.step_id, error="cancelled")
                continue

            if result.get("success"):
                step.output = result.get("output")
                step.outcome = "success"
                self.task_manager.transition_step_state(
                    task_id, step.step_id, TaskStepState.COMPLETED
                )
                self.task_manager.update_step(
                    task_id, step.step_id, output=step.output, outcome=step.outcome
                )
            else:
                step.error = result.get("error")
                step.outcome = "failure"
                self.task_manager.transition_step_state(task_id, step.step_id, TaskStepState.FAILED)
                self.task_manager.update_step(
                    task_id, step.step_id, error=step.error, outcome=step.outcome
                )
                # Stop on failure.
                return self.task_manager.update_task(
                    task_id,
                    state=TaskState.FAILED,
                    failure_code=result.get("error_code", "step_failed"),
                    finished_at=datetime.datetime.now(datetime.UTC).isoformat(),
                )

        task = self.task_manager.get_task(task_id)
        # Verification.
        verification = self.verifier(task, observations)
        if verification.success:
            state = TaskState.COMPLETED
        elif any(s.state is TaskStepState.COMPLETED for s in task.steps) and any(
            s.state is TaskStepState.FAILED for s in task.steps
        ):
            state = TaskState.PARTIAL
        else:
            state = TaskState.FAILED
        task = self.task_manager.update_task(
            task_id,
            state=state,
            result_summary=verification.details,
            finished_at=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        self.task_manager.events.publish(
            "task.finished", {"task_id": task_id, "state": task.state.value}
        )
        return task

    def cancel_task(self, task_id: str) -> Task:
        return self.task_manager.cancel_task(task_id)

    def _default_verifier(self, task: Task, observations: list[Any]) -> VerificationResult:
        if not task.steps:
            return VerificationResult(success=True, outcome="success", details="no steps")
        if all(obs.get("success") for obs in observations) and len(observations) == len(task.steps):
            return VerificationResult(
                success=True, outcome="success", details="all steps succeeded"
            )
        if any(obs.get("success") for obs in observations):
            return VerificationResult(success=False, outcome="partial", details="some steps failed")
        return VerificationResult(success=False, outcome="failure", details="all steps failed")
