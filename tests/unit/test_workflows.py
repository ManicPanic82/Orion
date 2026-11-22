"""Tests for capability expansion workflows."""

from __future__ import annotations

from orion.workflows import Goal, Procedure, WorkflowManager


def test_procedure_validation_and_versioning() -> None:
    mgr = WorkflowManager()
    p = Procedure(name="Test", steps=[{"action": "x"}])
    assert p.validate() == []
    mgr.register_procedure(p)
    assert mgr.get_procedure(p.procedure_id).version == "1"


def test_procedure_review_gates() -> None:
    mgr = WorkflowManager()
    p = Procedure(name="Test", steps=[{"action": "x"}])
    mgr.register_procedure(p)
    assert p.enabled is False
    mgr.approve_procedure(p.procedure_id)
    assert mgr.get_procedure(p.procedure_id).enabled is True


def test_goal_budget_and_pause() -> None:
    mgr = WorkflowManager()
    g = Goal(name="Goal", budget_calls=10)
    mgr.create_goal(g)
    mgr.pause_goal(g.goal_id)
    assert mgr.get_goal(g.goal_id).enabled is False


def test_daily_briefing() -> None:
    mgr = WorkflowManager()
    mgr.generate_briefing([{"item": "test"}])
    assert mgr.last_briefing() is not None
