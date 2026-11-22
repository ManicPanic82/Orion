"""Shell navigation, mock labelling, and preference persistence."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from orion.config.settings import Settings, Severity
from orion.config.store import SettingsStore
from orion.mock.state_provider import MockStateProvider
from orion.navigation import DESTINATIONS
from orion.ui.main_window import MainWindow
from orion.ui.pages.command_centre import CommandCentrePage
from orion.ui.pages.planned_page import PlannedPage
from orion.ui.pages.settings_page import SettingsPage
from orion.ui.widgets.mock_badge import MockBadge


def test_every_destination_has_a_page_and_a_nav_button(window: MainWindow) -> None:
    for destination in DESTINATIONS:
        assert window.page(destination.id) is not None
        assert window.nav_button(destination.id).isEnabled()


def test_command_centre_and_settings_are_implemented_others_are_planned(
    window: MainWindow,
) -> None:
    assert isinstance(window.page("command_centre"), CommandCentrePage)
    assert isinstance(window.page("settings"), SettingsPage)
    for destination in DESTINATIONS:
        if destination.implemented:
            continue
        assert isinstance(window.page(destination.id), PlannedPage)


def test_planned_pages_expose_no_interactive_controls(window: MainWindow) -> None:
    for destination in DESTINATIONS:
        if destination.implemented:
            continue
        page = window.page(destination.id)
        assert page.findChildren(QPushButton) == []
        assert "PLANNED" in _all_text(page)
        assert destination.phase in _all_text(page)


def test_ampersand_in_destination_label_is_not_a_mnemonic(window: MainWindow) -> None:
    button = window.nav_button("experience_learning")
    assert button.text() == "Experience && Learning"


def test_clicking_navigation_switches_page_and_persists(
    qtbot, window: MainWindow, store: SettingsStore
) -> None:
    assert window.current_page_id() == "command_centre"

    qtbot.mouseClick(window.nav_button("projects"), Qt.MouseButton.LeftButton)

    assert window.current_page_id() == "projects"
    assert window.nav_button("projects").isChecked()
    assert not window.nav_button("command_centre").isChecked()

    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["navigation"]["active_page"] == "projects"


def test_startup_page_is_restored_from_settings(store: SettingsStore) -> None:
    settings = Settings()
    settings.navigation.active_page = "model_manager"
    store.save(settings)

    restored = SettingsStore(store.path).load()
    window = MainWindow(store, restored.settings, provider=MockStateProvider())

    assert window.current_page_id() == "model_manager"
    assert window.nav_button("model_manager").isChecked()
    window.close()


def test_command_centre_shows_mock_badges(window: MainWindow) -> None:
    page = window.page("command_centre")
    badges = page.findChildren(MockBadge)

    assert badges, "Command Centre must carry a visible MOCK marker"
    assert all(badge.text() == "MOCK" for badge in badges)


def test_window_title_and_mock_status_bar(window: MainWindow) -> None:
    assert window.windowTitle() == "Orion Workstation"
    status_badges = window.statusBar().findChildren(MockBadge)
    assert status_badges


def test_console_starts_expanded_and_can_collapse(window: MainWindow, store: SettingsStore) -> None:
    panel = window.console_panel
    assert panel.is_expanded() is True

    panel.set_expanded(False)

    assert panel.is_expanded() is False
    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["console"]["expanded"] is False

    panel.set_expanded(True)
    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["console"]["expanded"] is True


def test_console_severity_preference_persists(window: MainWindow, store: SettingsStore) -> None:
    window.console_panel.set_min_severity(Severity.WARNING)

    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["console"]["min_severity"] == "WARNING"


def test_console_renders_seeded_events(window: MainWindow) -> None:
    text = window.console_panel.output_text()
    assert "Orion Workstation started" in text
    assert "INFO" in text


def test_composer_submission_creates_a_labelled_simulated_task(window: MainWindow) -> None:
    page = window.page("command_centre")
    assert isinstance(page, CommandCentrePage)

    page.composer().setPlainText("Summarise the roadmap")
    assert page.submit_button().isEnabled() is True

    page.submit_button().click()

    assert page.composer().toPlainText() == ""
    assert "sim-0001" in page.result_text()
    assert "sim-0001" in window.console_panel.output_text()


def test_composer_is_disabled_for_blank_input(window: MainWindow) -> None:
    page = window.page("command_centre")
    assert isinstance(page, CommandCentrePage)

    page.composer().setPlainText("   ")
    assert page.submit_button().isEnabled() is False


def test_closing_persists_geometry(window: MainWindow, store: SettingsStore) -> None:
    window.resize(1280, 800)
    window.close()

    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["window"]["width"] > 0
    assert saved["window"]["height"] > 0


def test_offscreen_geometry_is_clamped_onto_a_screen(store: SettingsStore) -> None:
    settings = Settings()
    settings.window.x = -20_000
    settings.window.y = -20_000
    settings.window.width = 1280
    settings.window.height = 800

    window = MainWindow(store, settings, provider=MockStateProvider())

    assert window.pos().x() > -10_000
    assert window.pos().y() > -10_000
    window.close()


def test_settings_file_is_created_only_after_a_change(
    qtbot, window: MainWindow, store: SettingsStore, settings_file: Path
) -> None:
    assert not settings_file.exists()

    qtbot.mouseClick(window.nav_button("settings"), Qt.MouseButton.LeftButton)

    assert settings_file.exists()


def _all_text(widget) -> str:
    from PySide6.QtWidgets import QLabel

    return "\n".join(label.text() for label in widget.findChildren(QLabel))
