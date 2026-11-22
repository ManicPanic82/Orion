"""Windows login autostart: registry mechanics, drift, and honest reporting.

Every test uses an in-memory registry backend. Nothing here touches HKCU\\Run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers import FakeRegistry
from orion.config.settings import Settings
from orion.config.store import SettingsStore
from orion.startup import (
    VALUE_NAME,
    StartupController,
    StartupRegistration,
    UnregisterOutcome,
    build_run_command,
    resolve_launch_command,
)

COMMAND = r'"C:\Program Files\Orion\pythonw.exe" -m orion --minimised'


def _registration(registry: FakeRegistry) -> StartupRegistration:
    return StartupRegistration(registry, COMMAND)


# -- command construction ---------------------------------------------------


def test_run_command_quotes_paths_with_spaces() -> None:
    command = build_run_command(Path(r"C:\Program Files\Orion\orion.exe"), ["--minimised"])
    assert command == r'"C:\Program Files\Orion\orion.exe" --minimised'


def test_launch_command_prefers_pythonw_when_present(tmp_path: Path) -> None:
    python = tmp_path / "python.exe"
    pythonw = tmp_path / "pythonw.exe"
    python.touch()
    pythonw.touch()

    command = resolve_launch_command(str(python))

    assert "pythonw.exe" in command
    assert "-m orion" in command
    assert "--minimised" in command


def test_launch_command_falls_back_to_the_given_interpreter(tmp_path: Path) -> None:
    python = tmp_path / "python.exe"
    python.touch()

    command = resolve_launch_command(str(python))

    assert "python.exe" in command
    assert "pythonw.exe" not in command


def test_launch_command_quotes_a_path_with_spaces(tmp_path: Path) -> None:
    spaced = tmp_path / "Program Files" / "Orion"
    spaced.mkdir(parents=True)
    python = spaced / "python.exe"
    python.touch()

    command = resolve_launch_command(str(python))

    assert command.startswith('"')


# -- registration -----------------------------------------------------------


def test_register_writes_only_the_owned_value() -> None:
    registry = FakeRegistry({"SomethingElse": "keep-me"})
    _registration(registry).register()

    assert registry.values[VALUE_NAME] == COMMAND
    assert registry.values["SomethingElse"] == "keep-me"
    assert registry.writes == [(VALUE_NAME, COMMAND)]


def test_unregister_removes_the_owned_value() -> None:
    registry = FakeRegistry({VALUE_NAME: COMMAND})
    outcome = _registration(registry).unregister()

    assert outcome is UnregisterOutcome.REMOVED
    assert VALUE_NAME not in registry.values
    assert registry.deletes == [VALUE_NAME]


def test_unregister_absent_is_a_no_op() -> None:
    registry = FakeRegistry()
    assert _registration(registry).unregister() is UnregisterOutcome.ABSENT
    assert registry.deletes == []


def test_unregister_leaves_a_foreign_value_untouched() -> None:
    registry = FakeRegistry({VALUE_NAME: r'"C:\Other\app.exe"'})
    outcome = _registration(registry).unregister()

    assert outcome is UnregisterOutcome.FOREIGN
    assert registry.values[VALUE_NAME] == r'"C:\Other\app.exe"'
    assert registry.deletes == []


def test_registration_is_idempotent() -> None:
    registry = FakeRegistry()
    registration = _registration(registry)
    registration.register()
    registration.register()

    assert registry.values[VALUE_NAME] == COMMAND
    assert registration.matches_expected() is True


# -- controller status ------------------------------------------------------


def _controller(tmp_path: Path, registry: FakeRegistry) -> tuple[StartupController, Settings]:
    store = SettingsStore(tmp_path / "settings.json")
    settings = Settings()
    store.save(settings)
    return StartupController(_registration(registry), settings, store), settings


def test_status_reports_unregistered(tmp_path: Path) -> None:
    controller, _ = _controller(tmp_path, FakeRegistry())
    status = controller.status()

    assert status.desired is False
    assert status.registered is False
    assert status.matches_expected is False
    assert "Not registered" in status.note
    assert status.error is None


def test_status_reports_registered(tmp_path: Path) -> None:
    controller, _ = _controller(tmp_path, FakeRegistry({VALUE_NAME: COMMAND}))
    status = controller.status()

    assert status.registered is True
    assert status.matches_expected is True
    assert "starts in the notification area" in status.note


def test_status_reports_a_foreign_command(tmp_path: Path) -> None:
    controller, _ = _controller(tmp_path, FakeRegistry({VALUE_NAME: r'"C:\Other\app.exe"'}))
    status = controller.status()

    assert status.registered is True
    assert status.matches_expected is False
    assert "different startup command" in status.note


def test_status_flags_drift_between_preference_and_registry(tmp_path: Path) -> None:
    controller, settings = _controller(tmp_path, FakeRegistry())
    settings.startup.enabled = True

    status = controller.status()

    assert "disagree" in status.note


def test_status_reports_read_failure_honestly(tmp_path: Path) -> None:
    registry = FakeRegistry()
    registry.fail_on_read = "access denied"
    controller, _ = _controller(tmp_path, registry)

    status = controller.status()

    assert status.error == "access denied"
    assert "could not be read" in status.note


# -- enabling and disabling -------------------------------------------------


def test_set_enabled_true_registers_and_persists(tmp_path: Path) -> None:
    registry = FakeRegistry()
    controller, settings = _controller(tmp_path, registry)

    status = controller.set_enabled(True)

    assert registry.values[VALUE_NAME] == COMMAND
    assert settings.startup.enabled is True
    assert status.registered is True
    assert status.error is None

    reloaded = SettingsStore(tmp_path / "settings.json").load()
    assert reloaded.settings.startup.enabled is True


def test_set_enabled_false_unregisters_and_persists(tmp_path: Path) -> None:
    registry = FakeRegistry({VALUE_NAME: COMMAND})
    controller, settings = _controller(tmp_path, registry)
    settings.startup.enabled = True

    status = controller.set_enabled(False)

    assert VALUE_NAME not in registry.values
    assert settings.startup.enabled is False
    assert status.error is None


def test_write_failure_is_reported_and_preference_is_not_claimed(tmp_path: Path) -> None:
    registry = FakeRegistry()
    registry.fail_on_write = "policy blocked the write"
    controller, settings = _controller(tmp_path, registry)

    status = controller.set_enabled(True)

    assert status.error == "policy blocked the write"
    assert settings.startup.enabled is False
    assert registry.values == {}


def test_disable_of_a_foreign_entry_is_reported(tmp_path: Path) -> None:
    registry = FakeRegistry({VALUE_NAME: r'"C:\Other\app.exe"'})
    controller, settings = _controller(tmp_path, registry)

    status = controller.set_enabled(False)

    assert status.error is not None
    assert "left untouched" in status.error
    assert registry.values[VALUE_NAME] == r'"C:\Other\app.exe"'


def test_mark_prompted_persists_once(tmp_path: Path) -> None:
    controller, settings = _controller(tmp_path, FakeRegistry())

    controller.mark_prompted()
    assert settings.startup.prompted is True

    reloaded = SettingsStore(tmp_path / "settings.json").load()
    assert reloaded.settings.startup.prompted is True


@pytest.mark.parametrize("desired", [True, False])
def test_status_never_claims_success_without_a_registry_match(
    tmp_path: Path, desired: bool
) -> None:
    controller, settings = _controller(tmp_path, FakeRegistry())
    settings.startup.enabled = desired

    status = controller.status()

    assert status.matches_expected is (desired and False)
