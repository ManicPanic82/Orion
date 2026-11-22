"""Tests for Model Profile schema and validation."""

from __future__ import annotations

import json

from orion.models import (
    AdapterRequirement,
    ModelProfile,
    validate_profile,
)


def test_valid_mock_profile_round_trips() -> None:
    profile = ModelProfile(
        profile_id="mock-profile",
        name="Mock Profile",
        base_model="mock-base",
        adapter_requirement="none",
        backend="mock",
        context_limit=1024,
        generation_limit=128,
    )
    assert profile.adapter_required is False
    text = profile.to_json()
    restored = ModelProfile.from_json(text)
    assert restored == profile
    assert restored.base_model.identity == "mock-base"


def test_required_adapter_missing_fails() -> None:
    profile = ModelProfile(
        profile_id="req",
        base_model="mock-base",
        adapter_requirement="required",
    )
    problems = validate_profile(profile)
    assert any("required adapter" in p for p in problems)


def test_schema_version_mismatch_fails() -> None:
    profile = ModelProfile(profile_id="x", schema_version=999)
    problems = profile.validate()
    assert any("schema_version" in p for p in problems)


def test_adapter_requirement_aliases() -> None:
    profile = ModelProfile(profile_id="a", required_adapter=True)
    assert profile.adapter.requirement is AdapterRequirement.REQUIRED
    assert profile.adapter_required is True


def test_import_export_round_trip() -> None:
    raw = {
        "profile_id": "p",
        "name": "P",
        "base_model": {"identity": "base", "revision": "r1", "path": "", "backend": "mock"},
        "adapter": {"requirement": "optional", "path": "/tmp/a", "type": "lora", "revision": "r2"},
        "context_limit": 2048,
    }
    profile = ModelProfile.from_dict(raw)
    assert profile.adapter.requirement.value == "optional"
    assert json.loads(profile.to_json())["profile_id"] == "p"
