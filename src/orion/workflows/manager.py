"""Procedure and goal manager for Orion capability expansion."""

from __future__ import annotations

import threading
from typing import Any

from orion.workflows.models import DailyBriefing, Goal, Procedure, ReviewState


class WorkflowManager:
    def __init__(self) -> None:
        self._procedures: dict[str, Procedure] = {}
        self._goals: dict[str, Goal] = {}
        self._briefings: list[DailyBriefing] = []
        self._lock = threading.RLock()

    # Procedures
    def register_procedure(self, procedure: Procedure) -> Procedure:
        problems = procedure.validate()
        if problems:
            raise ValueError("; ".join(problems))
        with self._lock:
            self._procedures[procedure.procedure_id] = procedure
        return procedure

    def get_procedure(self, procedure_id: str) -> Procedure:
        with self._lock:
            if procedure_id not in self._procedures:
                raise KeyError(f"procedure not found: {procedure_id}")
            return self._procedures[procedure_id]

    def list_procedures(self) -> list[Procedure]:
        with self._lock:
            return list(self._procedures.values())

    def approve_procedure(self, procedure_id: str, approver: str = "user") -> Procedure:
        p = self.get_procedure(procedure_id)
        p.review_state = ReviewState.APPROVED
        p.enabled = True
        return p

    def reject_procedure(self, procedure_id: str) -> Procedure:
        p = self.get_procedure(procedure_id)
        p.review_state = ReviewState.REJECTED
        p.enabled = False
        return p

    def revoke_procedure(self, procedure_id: str) -> Procedure:
        p = self.get_procedure(procedure_id)
        p.review_state = ReviewState.REVOKED
        p.enabled = False
        return p

    def update_permissions(self, procedure_id: str, permissions: list[str]) -> Procedure:
        p = self.get_procedure(procedure_id)
        p.permissions = list(permissions)
        return p

    # Goals
    def create_goal(self, goal: Goal) -> Goal:
        if not goal.name:
            raise ValueError("goal name required")
        with self._lock:
            self._goals[goal.goal_id] = goal
        return goal

    def get_goal(self, goal_id: str) -> Goal:
        with self._lock:
            if goal_id not in self._goals:
                raise KeyError(f"goal not found: {goal_id}")
            return self._goals[goal_id]

    def list_goals(self) -> list[Goal]:
        with self._lock:
            return list(self._goals.values())

    def pause_goal(self, goal_id: str) -> Goal:
        g = self.get_goal(goal_id)
        g.enabled = False
        return g

    def resume_goal(self, goal_id: str) -> Goal:
        g = self.get_goal(goal_id)
        g.enabled = True
        return g

    def disable_goal(self, goal_id: str) -> Goal:
        g = self.get_goal(goal_id)
        g.enabled = False
        g.review_state = ReviewState.REVOKED
        return g

    # Briefings
    def generate_briefing(self, items: list[dict[str, Any]] | None = None) -> DailyBriefing:
        b = DailyBriefing(items=items or [])
        self._briefings.append(b)
        return b

    def last_briefing(self) -> DailyBriefing | None:
        return self._briefings[-1] if self._briefings else None
