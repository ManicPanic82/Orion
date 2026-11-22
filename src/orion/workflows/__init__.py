"""Capability expansion workflows for Orion."""

from orion.workflows.manager import WorkflowManager
from orion.workflows.models import DailyBriefing, Goal, Procedure, ReviewState, TriggerType

__all__ = [
    "DailyBriefing",
    "Goal",
    "Procedure",
    "ReviewState",
    "TriggerType",
    "WorkflowManager",
]
# Aliases
WorkflowEngine = WorkflowManager
ProcedureManager = WorkflowManager
