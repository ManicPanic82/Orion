"""Alias package for Orion Evolution."""

from __future__ import annotations

import sys

from orion.learning import *  # noqa: F401,F403

for _name in ("models", "builder", "connector", "manager"):
    sys.modules.setdefault(f"{__name__}.{_name}", sys.modules[f"orion.learning.{_name}"])
    globals()[_name] = sys.modules[f"orion.learning.{_name}"]
