"""Resident agent for Orion."""

from orion.agent.agent import ResidentAgent
from orion.agent.models import PlannedStep, VerificationResult
from orion.agent.planner import MockPlanner, Planner

__all__ = [
    "MockPlanner",
    "Planner",
    "PlannedStep",
    "ResidentAgent",
    "VerificationResult",
]
# Aliases
OrionAgent = ResidentAgent
Agent = ResidentAgent
