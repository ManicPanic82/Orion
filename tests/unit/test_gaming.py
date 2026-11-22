"""Tests for gaming/visual interaction."""

from __future__ import annotations

from orion.gaming import GamingManager


def test_capture_lifecycle() -> None:
    mgr = GamingManager()
    assert mgr.capture_state.value == "off"
    mgr.start_capture("Game.exe")
    assert mgr.capture_state.value == "active"
    mgr.stop_capture()
    assert mgr.capture_state.value == "stopped"


def test_action_blocked_when_not_selected() -> None:
    mgr = GamingManager()
    mgr.start_capture("Game.exe")
    mgr.set_foreground("Other.exe")
    from orion.gaming.models import GamingAction

    action = mgr.fire_action(GamingAction(keys=["a"]))
    assert action is not None
    assert mgr.is_action_allowed() is False


def test_action_rate_limit() -> None:
    mgr = GamingManager()
    mgr.start_capture("Game.exe")
    mgr.set_foreground("Game.exe")
    # Fire once
    from orion.gaming.models import GamingAction

    mgr.fire_action(GamingAction(keys=["a"]))
    assert mgr.is_action_allowed() is False


def test_episode_recording() -> None:
    mgr = GamingManager()
    ep = mgr.create_episode(task_id="t1")
    mgr.finish_episode(ep.episode_id, success_metrics={"score": 10}, reward=0.5)
    got = mgr.get_episode(ep.episode_id)
    assert got.reward == 0.5
    assert got.ended_at is not None
