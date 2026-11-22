"""The Settings startup control must reflect the registry, not assume success."""

from __future__ import annotations

import json

from helpers import FakeRegistry
from orion.config.settings import Settings
from orion.config.store import SettingsStore
from orion.mock.state_provider import MockStateProvider
from orion.startup import VALUE_NAME, StartupController, StartupRegistration
from orion.ui.main_window import MainWindow

COMMAND = r'"C:\Program Files\Orion\pythonw.exe" -m orion --minimised'


def _window(qtbot, store: SettingsStore, registry: FakeRegistry, settings: Settings | None = None):
    settings = settings or Settings()
    startup = StartupController(StartupRegistration(registry, COMMAND), settings, store)
    window = MainWindow(
        store,
        settings,
        provider=MockStateProvider(),
        startup=startup,
        tray_available=lambda: False,
    )
    qtbot.addWidget(window)
    return window


def test_checkbox_starts_unchecked_and_explains_the_state(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, FakeRegistry())
    page = window.page("settings")

    assert page.startup_checkbox().isChecked() is False
    assert "Not registered" in page.startup_note()


def test_enabling_registers_the_exact_command(qtbot, store: SettingsStore) -> None:
    registry = FakeRegistry()
    window = _window(qtbot, store, registry)
    page = window.page("settings")

    page.startup_checkbox().setChecked(True)

    assert registry.values[VALUE_NAME] == COMMAND
    assert "starts in the notification area" in page.startup_note()

    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["startup"]["enabled"] is True


def test_disabling_removes_the_entry(qtbot, store: SettingsStore) -> None:
    registry = FakeRegistry({VALUE_NAME: COMMAND})
    settings = Settings()
    settings.startup.enabled = True
    window = _window(qtbot, store, registry, settings)
    page = window.page("settings")
    assert page.startup_checkbox().isChecked() is True

    page.startup_checkbox().setChecked(False)

    assert VALUE_NAME not in registry.values
    assert "Not registered" in page.startup_note()


def test_failure_reverts_the_checkbox_and_reports_the_error(qtbot, store: SettingsStore) -> None:
    registry = FakeRegistry()
    registry.fail_on_write = "policy blocked the write"
    window = _window(qtbot, store, registry)
    page = window.page("settings")

    page.startup_checkbox().setChecked(True)

    assert page.startup_checkbox().isChecked() is False
    assert window.settings.startup.enabled is False
    assert "policy blocked the write" in page._startup_error.text()


def test_foreign_entry_is_reported_not_deleted(qtbot, store: SettingsStore) -> None:
    registry = FakeRegistry({VALUE_NAME: r'"C:\Other\app.exe"'})
    settings = Settings()
    settings.startup.enabled = True
    window = _window(qtbot, store, registry, settings)
    page = window.page("settings")

    page.startup_checkbox().setChecked(False)

    assert registry.values[VALUE_NAME] == r'"C:\Other\app.exe"'
    assert "left untouched" in page._startup_error.text()
