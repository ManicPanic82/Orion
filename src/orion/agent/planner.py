"""Planner abstraction for Orion's resident agent."""

from __future__ import annotations

from typing import Protocol

from orion.agent.models import PlannedStep
from orion.tasks.models import Objective


class Planner(Protocol):
    def plan(
        self, objective: Objective, available_capabilities: list[str]
    ) -> list[PlannedStep]: ...


class MockPlanner:
    """Deterministic planner producing structured steps from objective text."""

    def plan(self, objective: Objective, available_capabilities: list[str]) -> list[PlannedStep]:
        text = objective.request.lower()
        steps: list[PlannedStep] = []

        if ("echo" in text or "repeat" in text) and "echo" in available_capabilities:
            steps.append(
                PlannedStep(
                    capability_id="echo",
                    input={"text": objective.request},
                    idempotency="read_only",
                )
            )

        if ("sum" in text or "add" in text) and "sum" in available_capabilities:
            steps.append(
                PlannedStep(
                    capability_id="sum", input={"values": [1, 2, 3]}, idempotency="read_only"
                )
            )

        if "fail" in text and "fail" in available_capabilities:
            steps.append(PlannedStep(capability_id="fail", input={}, idempotency="read_only"))

        if not steps and "echo" in available_capabilities:
            steps.append(
                PlannedStep(
                    capability_id="echo",
                    input={"text": objective.request},
                    idempotency="read_only",
                )
            )

        return steps
