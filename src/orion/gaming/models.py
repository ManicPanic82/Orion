"""Gaming and visual interaction models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class CaptureState(StrEnum):
    OFF = "off"
    ACTIVE = "active"
    STOPPED = "stopped"


class ActionType(StrEnum):
    KEY = "key"
    MOUSE = "mouse"
    RESIZE = "resize"
    NAVIGATE = "navigate"


@dataclass(slots=True)
class VisualObservation:
    frame_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    window_handle: str = ""
    image_data: str = ""  # base64
    width: int = 0
    height: int = 0
    task_id: str = ""


@dataclass(slots=True)
class GamingAction:
    action_id: str = field(default_factory=lambda: str(uuid4()))
    action_type: ActionType = ActionType.KEY
    keys: list[str] = field(default_factory=list)
    button: str = ""
    coords: tuple[int, int] | None = None
    duration_ms: int = 50
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    task_id: str = ""
    episode_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "keys": list(self.keys),
            "button": self.button,
            "coords": self.coords,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "episode_id": self.episode_id,
        }


@dataclass(slots=True)
class GamingEpisode:
    episode_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ended_at: str | None = None
    observations: list[VisualObservation] = field(default_factory=list)
    actions: list[GamingAction] = field(default_factory=list)
    success_metrics: dict[str, Any] = field(default_factory=dict)
    reward: float = 0.0
    notes: str = ""
