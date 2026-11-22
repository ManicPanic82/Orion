"""Schema-level tests for the versioned settings document."""

from __future__ import annotations

import pytest

from orion.config.settings import (
    SCHEMA_VERSION,
    CloseAction,
    Settings,
    Severity,
)


def test_defaults_are_valid_and_round_trip() -> None:
    settings = Settings()
    assert settings.validate() == []

    restored, problems = Settings.from_dict(settings.to_dict())
    assert problems == []
    assert restored.to_dict() == settings.to_dict()


def test_default_document_has_expected_shape() -> None:
    payload = Settings().to_dict()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["window"]["close_action"] == CloseAction.MINIMISE_TO_TRAY.value
    assert payload["console"]["min_severity"] == Severity.INFO.value
    assert payload["startup"] == {"enabled": False, "prompted": False}
    assert payload["ui"] == {"tray_notice_shown": False}


def test_enum_values_are_persisted_as_plain_strings() -> None:
    payload = Settings().to_dict()
    assert type(payload["window"]["close_action"]) is str
    assert type(payload["console"]["min_severity"]) is str


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("width", 100, "outside 900..10000"),
        ("height", 10_001, "outside 600..10000"),
        ("width", "wide", "expected an integer"),
        ("maximized", "yes", "expected a boolean"),
    ],
)
def test_invalid_window_values_fall_back_and_report(
    field: str, value: object, fragment: str
) -> None:
    raw = {"schema_version": SCHEMA_VERSION, "window": {field: value}}
    settings, problems = Settings.from_dict(raw)

    assert any(fragment in problem for problem in problems), problems
    assert settings.window.width == 1440
    assert settings.window.height == 900
    assert settings.window.maximized is False
    assert settings.validate() == []


def test_unknown_page_falls_back_to_command_centre() -> None:
    raw = {"schema_version": SCHEMA_VERSION, "navigation": {"active_page": "nonexistent"}}
    settings, problems = Settings.from_dict(raw)

    assert settings.navigation.active_page == "command_centre"
    assert any("not a known destination" in problem for problem in problems)


def test_unknown_enum_value_falls_back() -> None:
    raw = {
        "schema_version": SCHEMA_VERSION,
        "console": {"min_severity": "TRACE"},
        "window": {"close_action": "explode"},
    }
    settings, problems = Settings.from_dict(raw)

    assert settings.console.min_severity is Severity.INFO
    assert settings.window.close_action is CloseAction.MINIMISE_TO_TRAY
    assert sum("is not one of" in problem for problem in problems) == 2


def test_ui_scale_range_is_enforced() -> None:
    settings, problems = Settings.from_dict(
        {"schema_version": SCHEMA_VERSION, "appearance": {"ui_scale": 9.5}}
    )
    assert settings.appearance.ui_scale == 1.0
    assert any("outside 0.8..2.0" in problem for problem in problems)


def test_section_that_is_not_an_object_uses_defaults() -> None:
    settings, problems = Settings.from_dict({"schema_version": SCHEMA_VERSION, "console": "nope"})

    assert settings.console.expanded is True
    assert any("expected an object" in problem for problem in problems)


def test_validate_reports_constructed_inconsistencies() -> None:
    settings = Settings()
    settings.navigation.active_page = "not_a_page"
    settings.console.height = 5

    problems = settings.validate()
    assert len(problems) == 2
