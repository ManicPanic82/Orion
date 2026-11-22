"""Gaming and visual interaction for Orion."""

from orion.gaming.manager import GamingManager
from orion.gaming.models import (
    ActionType,
    CaptureState,
    GamingAction,
    GamingEpisode,
    VisualObservation,
)

__all__ = [
    "ActionType",
    "CaptureState",
    "GamingAction",
    "GamingEpisode",
    "GamingManager",
    "VisualObservation",
]
# Aliases
VisualInteractionManager = GamingManager
