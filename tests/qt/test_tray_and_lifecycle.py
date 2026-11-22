"""Close-to-tray policy, quit path, and the startup prompt.

The system tray does not exist on the offscreen platform, so availability is
injected. These tests therefore prove Orion's policy, not Qt's tray rendering;
the real icon is verified manually on the desktop.
"""

from __future__ import annotations

import json

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

from helpers import FakeRegistry
from orion.config.settings import Settings
from orion.config.store import SettingsStore
from orion.mock.state_provider import MockStateProvider
from orion.startup import VALUE_NAME, StartupController, StartupRegistration
from orion.ui.main_window import MainWindow
from orion.ui.tray import TrayController

COMMAND = r'"C:\Program Files\Orion\pythonw.exe" -m orion --minimised'


def _window(qtbot, store: SettingsStore, **kwargs) -> MainWindow:
    kwargs.setdefault("provider", MockStateProvider())
    window = MainWindow(store, Settings(), **kwargs)
    qtbot.addWidget(window)
    return window


def _startup(store: SettingsStore, settings: Settings, registry: FakeRegistry):
    return StartupController(StartupRegistration(registry, COMMAND), settings, store)


def test_tray_is_installed_when_available(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: True)
    assert window.tray_installed is True


def test_close_hides_the_window_instead_of_quitting(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: True)
    window.show()

    window.close()

    assert window.isVisible() is False
    assert window.shutdown_requested is False


def test_restore_brings_the_hidden_window_back(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: True)
    window.show()
    window.close()
    assert window.isVisible() is False

    window.restore_from_tray()

    assert window.isVisible() is True


def test_close_falls_back_to_exit_without_a_tray(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: False)
    window.show()

    window.close()

    assert window.tray_installed is False
    assert window.isVisible() is False


def test_first_hide_shows_the_notice_once_and_persists_it(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: True)
    window.show()

    window.close()

    assert window.settings.ui.tray_notice_shown is True
    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["ui"]["tray_notice_shown"] is True

    window.restore_from_tray()
    window.close()
    assert window.settings.ui.tray_notice_shown is True


def test_notice_is_suppressed_when_already_recorded(qtbot, store: SettingsStore) -> None:
    settings = Settings()
    settings.ui.tray_notice_shown = True
    window = MainWindow(store, settings, provider=MockStateProvider(), tray_available=lambda: True)
    qtbot.addWidget(window)
    window.show()

    shown: list[bool] = []
    window.tray.notice_shown.connect(lambda: shown.append(True))
    window.close()

    assert shown == []


def test_quit_path_persists_and_removes_the_icon(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: True)
    window.show()

    window.request_quit()

    assert window.shutdown_requested is True
    assert window.tray_installed is False
    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["window"]["width"] > 0


def test_quit_is_idempotent(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: True)
    window.request_quit()
    window.request_quit()

    assert window.shutdown_requested is True


def test_ctrl_q_shortcut_exists(qtbot, store: SettingsStore) -> None:
    window = _window(qtbot, store, tray_available=lambda: True)
    sequences = {shortcut.key().toString() for shortcut in window.findChildren(QShortcut)}
    assert QKeySequence("Ctrl+Q").toString() in sequences


def test_startup_prompt_appears_once_and_registers_on_accept(qtbot, store: SettingsStore) -> None:
    settings = Settings()
    registry = FakeRegistry()
    startup = _startup(store, settings, registry)
    calls: list[bool] = []

    def prompt() -> bool:
        calls.append(True)
        return True

    window = MainWindow(
        store,
        settings,
        provider=MockStateProvider(),
        startup=startup,
        startup_prompt=prompt,
        tray_available=lambda: True,
    )
    qtbot.addWidget(window)
    window.show()

    window.prompt_startup_if_needed()

    assert len(calls) == 1
    assert settings.startup.prompted is True
    assert registry.values[VALUE_NAME] == COMMAND
    assert settings.startup.enabled is True

    window.restore_from_tray()
    window.prompt_startup_if_needed()

    assert len(calls) == 1


def test_startup_prompt_declined_writes_nothing(qtbot, store: SettingsStore) -> None:
    settings = Settings()
    registry = FakeRegistry()
    startup = _startup(store, settings, registry)

    window = MainWindow(
        store,
        settings,
        provider=MockStateProvider(),
        startup=startup,
        startup_prompt=lambda: False,
        tray_available=lambda: True,
    )
    qtbot.addWidget(window)
    window.show()

    window.prompt_startup_if_needed()

    assert settings.startup.prompted is True
    assert settings.startup.enabled is False
    assert registry.values == {}
    assert registry.writes == []


def test_startup_prompt_is_skipped_when_already_answered(qtbot, store: SettingsStore) -> None:
    settings = Settings()
    settings.startup.prompted = True
    registry = FakeRegistry()
    startup = _startup(store, settings, registry)
    calls: list[bool] = []

    window = MainWindow(
        store,
        settings,
        provider=MockStateProvider(),
        startup=startup,
        startup_prompt=lambda: calls.append(True) or True,
        tray_available=lambda: True,
    )
    qtbot.addWidget(window)
    window.show()

    window.prompt_startup_if_needed()

    assert calls == []


def test_closing_the_window_never_opens_the_startup_prompt(qtbot, store: SettingsStore) -> None:
    """A modal dialog in the close path blocks shutdown."""
    settings = Settings()
    startup = _startup(store, settings, FakeRegistry())
    calls: list[bool] = []

    window = MainWindow(
        store,
        settings,
        provider=MockStateProvider(),
        startup=startup,
        startup_prompt=lambda: calls.append(True) or True,
        tray_available=lambda: True,
    )
    qtbot.addWidget(window)
    window.show()

    window.close()

    assert calls == []
    assert settings.startup.prompted is False


def test_quit_never_opens_the_startup_prompt(qtbot, store: SettingsStore) -> None:
    settings = Settings()
    startup = _startup(store, settings, FakeRegistry())
    calls: list[bool] = []

    window = MainWindow(
        store,
        settings,
        provider=MockStateProvider(),
        startup=startup,
        startup_prompt=lambda: calls.append(True) or True,
        tray_available=lambda: True,
    )
    qtbot.addWidget(window)
    window.show()

    window.request_quit()

    assert calls == []


# -- tray readiness retry (ADR-010) ----------------------------------------


def test_tray_retries_until_the_shell_becomes_ready(qtbot) -> None:
    state = {"available": False}
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(
        window,
        is_available=lambda: state["available"],
        retries=5,
        retry_interval_ms=40,
    )

    assert tray.install() is False
    assert tray.available() is False

    state["available"] = True
    qtbot.waitUntil(tray.available, timeout=3_000)

    assert tray.available() is True
    tray.shutdown()


def test_tray_stops_retrying_after_the_bound(qtbot) -> None:
    window = QWidget()
    qtbot.addWidget(window)
    tray = TrayController(
        window,
        is_available=lambda: False,
        retries=2,
        retry_interval_ms=30,
    )

    assert tray.install() is False
    qtbot.wait(200)

    assert tray.available() is False
    tray.shutdown()
