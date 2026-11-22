"""Alias package for Orion's model manager subsystem."""

from __future__ import annotations

import sys

# Re-export everything from the canonical package.
from orion.models import *  # noqa: F401,F403

# Alias submodules so ``orion.model_manager.profile`` etc. resolve.
for _name in ("profile", "host", "manager", "state", "errors", "compatibility", "repository"):
    sys.modules.setdefault(f"{__name__}.{_name}", sys.modules[f"orion.models.{_name}"])
# Expose as attributes too.
for _name in ("profile", "host", "manager", "state", "errors", "compatibility", "repository"):
    globals()[_name] = sys.modules[f"orion.models.{_name}"]
