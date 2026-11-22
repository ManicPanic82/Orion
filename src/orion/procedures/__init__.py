"""Alias package for Orion procedures."""

from __future__ import annotations

import sys

from orion.workflows import *  # noqa: F401,F403

for _name in ("models", "manager"):
    sys.modules.setdefault(f"{__name__}.{_name}", sys.modules[f"orion.workflows.{_name}"])
    globals()[_name] = sys.modules[f"orion.workflows.{_name}"]
