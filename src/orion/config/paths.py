"""Application data path resolution.

No developer home directory, drive letter, or username may be hard-coded
(AGENTS.md §7). Paths derive from the Windows ``%APPDATA%`` known folder, with an
explicit override for testing and for the per-run override allowed by
docs/operations/CONFIGURATION.md §3 for non-security-sensitive values.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "APP_DIR_NAME",
    "DATA_DIR_ENV_VAR",
    "app_data_dir",
    "console_log_path",
    "ensure_data_dir",
    "settings_path",
]

APP_DIR_NAME = "Orion"
DATA_DIR_ENV_VAR = "ORION_DATA_DIR"


def app_data_dir() -> Path:
    """Resolve the mutable application data directory.

    Precedence: explicit ``ORION_DATA_DIR`` override, then ``%APPDATA%\\Orion``,
    then the documented fallback under the user profile.
    """
    override = os.environ.get(DATA_DIR_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()

    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        return Path(appdata) / APP_DIR_NAME

    return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME


def settings_path() -> Path:
    """Path of the versioned UI settings document."""
    return app_data_dir() / "settings.json"


def console_log_path() -> Path:
    """Path reserved for the rotating diagnostic log.

    Phase 1 writes no log file; the location is defined here so that later phases
    do not invent a second convention.
    """
    return app_data_dir() / "logs" / "orion-workstation.log"


def ensure_data_dir() -> Path:
    """Create and return the application data directory."""
    path = app_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path
