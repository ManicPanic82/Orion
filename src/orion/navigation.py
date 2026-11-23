"""Static navigation metadata for the Operations Centre.

This module deliberately imports no Qt. Both the settings schema (which validates
the persisted active page) and the presentation layer (which builds the nav rail)
read from the same source, so a page cannot exist in one and be missing from the
other.

``implemented`` is a statement of fact, not a roadmap intention. Pages that are
not implemented yet must render an honest "planned" state.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["DESTINATIONS", "PAGE_IDS", "NavDestination", "destination"]


@dataclass(frozen=True, slots=True)
class NavDestination:
    """A single Operations Centre destination."""

    id: str
    label: str
    subtitle: str
    phase: str
    implemented: bool


DESTINATIONS: tuple[NavDestination, ...] = (
    NavDestination(
        id="command_centre",
        label="Command Centre",
        subtitle="Objectives, agent status and activity",
        phase="Phase 1",
        implemented=True,
    ),
    NavDestination(
        id="resident_ai",
        label="Resident AI",
        subtitle="Conversation with the resident agent",
        phase="Phase 4",
        implemented=True,
    ),
    NavDestination(
        id="agent_activity",
        label="Agent Activity",
        subtitle="Tasks, steps and execution history",
        phase="Phase 4",
        implemented=True,
    ),
    NavDestination(
        id="projects",
        label="Projects",
        subtitle="Project registry and evidence-based briefings",
        phase="Phase 11",
        implemented=True,
    ),
    NavDestination(
        id="automation",
        label="Automation",
        subtitle="Schedules, triggers and approved commands",
        phase="Phase 10",
        implemented=False,
    ),
    NavDestination(
        id="experience_learning",
        label="Experience & Learning",
        subtitle="Experience review and Orion Evolution",
        phase="Phases 7–8",
        implemented=True,
    ),
    NavDestination(
        id="model_manager",
        label="Model Manager",
        subtitle="Model profiles and runtime state",
        phase="Phase 3",
        implemented=True,
    ),
    NavDestination(
        id="system_monitor",
        label="System Monitor",
        subtitle="Runtime health and resource reporting",
        phase="Phase 15",
        implemented=True,
    ),
    NavDestination(
        id="settings",
        label="Settings",
        subtitle="Application preferences and startup",
        phase="Phase 1",
        implemented=True,
    ),
)

PAGE_IDS: frozenset[str] = frozenset(d.id for d in DESTINATIONS)

DEFAULT_PAGE_ID = "command_centre"

_BY_ID = {d.id: d for d in DESTINATIONS}


def destination(page_id: str) -> NavDestination:
    """Return the destination with ``page_id``, or raise ``KeyError``."""
    return _BY_ID[page_id]
