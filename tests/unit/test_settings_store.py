"""Persistence behaviour for :class:`orion.config.store.SettingsStore`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orion.config.settings import SCHEMA_VERSION, Settings, SettingsError
from orion.config.store import SettingsStore


def test_missing_file_yields_defaults_without_writing(settings_file: Path) -> None:
    store = SettingsStore(settings_file)
    result = store.load()

    assert result.settings == Settings()
    assert result.problems == ()
    assert result.writable is True
    assert not settings_file.exists()


def test_save_then_load_round_trip(settings_file: Path) -> None:
    store = SettingsStore(settings_file)
    settings = Settings()
    settings.window.width = 1280
    settings.window.height = 800
    settings.window.x = 40
    settings.window.y = 60
    settings.navigation.active_page = "settings"
    settings.console.expanded = False
    settings.console.height = 300

    store.save(settings)

    reloaded = SettingsStore(settings_file).load()
    assert reloaded.problems == ()
    assert reloaded.settings.to_dict() == settings.to_dict()


def test_save_is_atomic_and_leaves_no_temporary_file(settings_file: Path) -> None:
    store = SettingsStore(settings_file)
    store.save(Settings())

    siblings = sorted(p.name for p in settings_file.parent.iterdir())
    assert siblings == ["settings.json"]


def test_save_creates_parent_directories(settings_file: Path) -> None:
    assert not settings_file.parent.exists()
    SettingsStore(settings_file).save(Settings())
    assert settings_file.exists()


def test_corrupt_document_is_quarantined_not_overwritten(settings_file: Path) -> None:
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text("{ this is not json", encoding="utf-8")

    store = SettingsStore(settings_file)
    result = store.load()

    assert result.settings == Settings()
    assert result.quarantined is not None
    assert result.quarantined.exists()
    assert result.quarantined.read_text(encoding="utf-8") == "{ this is not json"
    assert not settings_file.exists()
    assert result.writable is True
    assert any("not valid JSON" in problem for problem in result.problems)


def test_non_object_document_is_quarantined(settings_file: Path) -> None:
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text("[1, 2, 3]", encoding="utf-8")

    result = SettingsStore(settings_file).load()

    assert result.quarantined is not None
    assert any("must be a JSON object" in problem for problem in result.problems)


def test_document_without_schema_version_is_quarantined(settings_file: Path) -> None:
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(json.dumps({"window": {"width": 1280}}), encoding="utf-8")

    result = SettingsStore(settings_file).load()

    assert result.quarantined is not None
    assert any("schema_version" in problem for problem in result.problems)


def test_newer_schema_refuses_writes(settings_file: Path) -> None:
    settings_file.parent.mkdir(parents=True)
    original = json.dumps({"schema_version": SCHEMA_VERSION + 1, "future": True})
    settings_file.write_text(original, encoding="utf-8")

    store = SettingsStore(settings_file)
    result = store.load()

    assert result.writable is False
    assert result.settings == Settings()
    assert any("newer than this build" in problem for problem in result.problems)

    with pytest.raises(SettingsError):
        store.save(Settings())

    # The original document must survive untouched.
    assert settings_file.read_text(encoding="utf-8") == original


def test_invalid_settings_are_not_persisted(settings_file: Path) -> None:
    store = SettingsStore(settings_file)
    broken = Settings()
    broken.window.width = 1

    with pytest.raises(SettingsError):
        store.save(broken)

    assert not settings_file.exists()


def test_field_level_problems_do_not_block_saving(settings_file: Path) -> None:
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "window": {"width": 12}}),
        encoding="utf-8",
    )

    store = SettingsStore(settings_file)
    result = store.load()
    assert result.problems
    assert result.writable is True

    store.save(result.settings)
    assert SettingsStore(settings_file).load().problems == ()
