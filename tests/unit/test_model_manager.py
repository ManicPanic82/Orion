"""Tests for ModelManager lifecycle."""

from __future__ import annotations

import contextlib

from orion.models import (
    AdapterRequiredError,
    ModelLoadState,
    ModelManager,
    ModelProfile,
    UnsupportedBackendError,
)


def test_valid_mock_profile_loads_and_generates() -> None:
    manager = ModelManager()
    profile = ModelProfile(profile_id="mock", base_model="mock-base")
    manager.register(profile)
    loaded = manager.load_profile(profile)
    assert loaded.profile_id == "mock"
    assert manager.is_ready is True
    assert manager.state is ModelLoadState.READY
    assert "MOCK_RESPONSE" in manager.generate("hi")
    assert manager.status.is_mock is True


def test_missing_required_adapter_fails() -> None:
    manager = ModelManager()
    profile = ModelProfile(profile_id="req", base_model="mock-base", adapter_requirement="required")
    try:
        manager.load_profile(profile)
    except AdapterRequiredError:
        pass
    else:
        raise AssertionError("expected failure")
    assert manager.state is ModelLoadState.FAILED
    assert manager.active_profile is None


def test_incompatible_backend_fails() -> None:
    manager = ModelManager()
    profile = ModelProfile(profile_id="bad", base_model="x", backend="nonexistent")
    # backend stored on base_model
    profile.base_model.backend = "nonexistent"
    try:
        manager.load_profile(profile)
    except UnsupportedBackendError:
        pass
    else:
        raise AssertionError("expected failure")


def test_partial_load_cleans_up() -> None:
    from orion.models import MockModelHost

    host = MockModelHost(fail_health=True)
    manager = ModelManager(host=host)
    profile = ModelProfile(profile_id="h", base_model="mock-base")
    with contextlib.suppress(Exception):
        manager.load_profile(profile)
    assert manager.state is ModelLoadState.FAILED
    assert host.loaded_profile is None
    assert host.state is ModelLoadState.UNLOADED


def test_profile_switching() -> None:
    manager = ModelManager()
    p1 = ModelProfile(profile_id="p1", base_model="mock-base")
    p2 = ModelProfile(profile_id="p2", base_model="mock-base")
    manager.load_profile(p1)
    assert manager.active_profile_id == "p1"
    manager.load_profile(p2)
    assert manager.active_profile_id == "p2"
    manager.unload()
    assert manager.state is ModelLoadState.UNLOADED
    assert manager.active_profile is None


def test_health_failure_prevents_ready() -> None:
    from orion.models import MockModelHost

    host = MockModelHost(fail_health=True)
    manager = ModelManager(host=host)
    profile = ModelProfile(profile_id="hf", base_model="mock-base")
    with contextlib.suppress(Exception):
        manager.load_profile(profile)
    assert manager.state is not ModelLoadState.READY
