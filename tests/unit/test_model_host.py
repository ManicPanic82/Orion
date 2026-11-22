"""Tests for model host adapters."""

from __future__ import annotations

from orion.models import MockModelHost, ModelLoadState


def test_mock_host_is_labelled_mock() -> None:
    host = MockModelHost()
    assert host.is_mock is True
    runtime = host.describe_runtime()
    assert runtime.mock is True
    assert runtime.backend == "mock"


def test_mock_host_load_health_generate() -> None:
    from orion.models import ModelProfile

    host = MockModelHost()
    profile = ModelProfile(profile_id="m", base_model="mock-base")
    host.load(profile)
    assert host.state is ModelLoadState.READY
    assert host.loaded_profile is not None
    check = host.health_check()
    assert check.status.value == "ok"
    out = host.generate("hello")
    assert "MOCK_RESPONSE" in out
    host.unload()
    assert host.state is ModelLoadState.UNLOADED
    assert host.loaded_profile is None


def test_mock_host_missing_required_adapter_fails() -> None:
    from orion.models import AdapterRequiredError, ModelProfile

    host = MockModelHost()
    profile = ModelProfile(profile_id="m", base_model="mock-base", adapter_requirement="required")
    try:
        host.load(profile)
    except AdapterRequiredError:
        pass
    else:
        raise AssertionError("expected AdapterRequiredError")
