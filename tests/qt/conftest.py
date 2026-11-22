"""Fixtures for Qt-level tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from orion.config.settings import Settings
from orion.config.store import SettingsStore
from orion.mock.state_provider import MockStateProvider
from orion.ui.main_window import MainWindow


@pytest.fixture
def store(settings_file: Path) -> SettingsStore:
    return SettingsStore(settings_file)


@pytest.fixture
def window(qtbot, store: SettingsStore) -> MainWindow:
    main_window = MainWindow(store, Settings(), provider=MockStateProvider())
    qtbot.addWidget(main_window)
    return main_window
