"""Shared test fixtures.

Qt must be configured for offscreen rendering *before* any PySide6 import, which
is why the environment variable is set at module import time rather than inside a
fixture.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ORION_DATA_DIR at an isolated temporary directory."""
    path = tmp_path / "data"
    monkeypatch.setenv("ORION_DATA_DIR", str(path))
    return path


@pytest.fixture
def settings_file(data_dir: Path) -> Path:
    return data_dir / "settings.json"
