"""Gaming and visual interaction manager for Orion."""

from __future__ import annotations

import threading
import time
from typing import Any

from orion.gaming.models import (
    CaptureState,
    GamingAction,
    GamingEpisode,
    VisualObservation,
)


class GamingManager:
    def __init__(
        self,
        *,
        selected_window: str = "",
        max_actions_per_second: float = 10.0,
        max_duration_s: float = 300.0,
    ) -> None:
        self.selected_window = selected_window
        self.max_actions_per_second = max_actions_per_second
        self.max_duration_s = max_duration_s
        self.capture_state = CaptureState.OFF
        self.foreground_window: str | None = None
        self._lock = threading.RLock()
        self._episodes: dict[str, GamingEpisode] = {}
        self._last_action_time = 0.0
        self._stop_event = threading.Event()

    def start_capture(self, window: str | None = None) -> CaptureState:
        self.selected_window = window or self.selected_window
        self.capture_state = CaptureState.ACTIVE
        self._stop_event.clear()
        return self.capture_state

    def stop_capture(self) -> CaptureState:
        self.capture_state = CaptureState.STOPPED
        self._stop_event.set()
        return self.capture_state

    def set_foreground(self, window: str) -> None:
        self.foreground_window = window

    def is_action_allowed(self) -> bool:
        if self._stop_event.is_set():
            return False
        if self.capture_state is not CaptureState.ACTIVE:
            return False
        if self.foreground_window != self.selected_window:
            return False
        now = time.monotonic()
        min_interval = 1.0 / self.max_actions_per_second if self.max_actions_per_second > 0 else 0
        return not now - self._last_action_time < min_interval

    def fire_action(self, action: GamingAction) -> GamingAction:
        if not self.is_action_allowed():
            return action
        self._last_action_time = time.monotonic()
        action.duration_ms = max(0, min(action.duration_ms, 5000))
        # Record into active episode if any
        if action.episode_id:
            ep = self._episodes.get(action.episode_id)
            if ep:
                ep.actions.append(action)
        return action

    def record_observation(self, obs: VisualObservation) -> VisualObservation:
        if self.capture_state is not CaptureState.ACTIVE:
            raise RuntimeError("capture not active")
        return obs

    def create_episode(self, task_id: str = "") -> GamingEpisode:
        ep = GamingEpisode(task_id=task_id)
        self._episodes[ep.episode_id] = ep
        return ep

    def finish_episode(
        self, episode_id: str, success_metrics: dict[str, Any] | None = None, reward: float = 0.0
    ) -> GamingEpisode:
        ep = self._episodes.get(episode_id)
        if ep is None:
            raise KeyError(f"episode not found: {episode_id}")
        import datetime as _dt

        ep.ended_at = _dt.datetime.now(_dt.UTC).isoformat()
        ep.success_metrics = success_metrics or {}
        ep.reward = reward
        return ep

    def get_episode(self, episode_id: str) -> GamingEpisode:
        return self._episodes[episode_id]

    def list_episodes(self) -> list[GamingEpisode]:
        return list(self._episodes.values())
