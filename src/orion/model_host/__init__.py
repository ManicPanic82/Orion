"""Alias package for Orion's model host subsystem."""

from __future__ import annotations

import sys

from orion.models import *  # noqa: F401,F403

for _name in ("profile", "host", "manager", "state", "errors", "compatibility", "repository"):
    sys.modules.setdefault(f"{__name__}.{_name}", sys.modules[f"orion.models.{_name}"])
    globals()[_name] = sys.modules[f"orion.models.{_name}"]
