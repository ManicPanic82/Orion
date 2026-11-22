"""Configuration and persistence for Orion Workstation UI preferences."""

from __future__ import annotations

from orion.config.paths import app_data_dir, settings_path
from orion.config.settings import SCHEMA_VERSION, Settings, SettingsError
from orion.config.store import LoadResult, SettingsStore

__all__ = [
    "SCHEMA_VERSION",
    "LoadResult",
    "Settings",
    "SettingsError",
    "SettingsStore",
    "app_data_dir",
    "settings_path",
]
