"""Orion Workstation: the desktop Operations Centre.

Phase 1 provides a presentation shell only. It performs no inference, no
automation, no filesystem agent work, and no network calls. All assistant,
task, and model state shown in this phase is explicitly labelled mock state.
"""

from __future__ import annotations

__all__ = ["APP_NAME", "ORG_NAME", "PRODUCT_NAME", "PHASE_LABEL", "__version__"]

PRODUCT_NAME = "Orion"
APP_NAME = "Orion Workstation"
ORG_NAME = "Orion"
PHASE_LABEL = "Phase 1 · Operations Centre shell"
__version__ = "0.1.0"
