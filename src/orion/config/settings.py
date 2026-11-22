"""Versioned, validated UI settings for Orion Workstation.

Phase 1 persists presentation preferences only: window geometry, the active
destination, console state, and startup preference. Domain state (objectives,
tasks, memory, profiles) belongs in the Core database introduced in a later
phase and must not be smuggled in here.

Validation never silently becomes permissive. Every rejected value is reported
and replaced by its documented default; a settings document that cannot be
interpreted is quarantined by :mod:`orion.config.store` rather than overwritten.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from orion.navigation import DEFAULT_PAGE_ID, PAGE_IDS

__all__ = [
    "SCHEMA_VERSION",
    "AppearanceSettings",
    "CloseAction",
    "ConsoleSettings",
    "NavigationSettings",
    "Severity",
    "Settings",
    "SettingsError",
    "StartupSettings",
    "UiSettings",
    "WindowSettings",
]

SCHEMA_VERSION = 1

DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 900
DEFAULT_CONSOLE_HEIGHT = 220
DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"
MIN_WIDTH = 900
MAX_WIDTH = 10_000
MIN_HEIGHT = 600
MAX_HEIGHT = 10_000
MIN_CONSOLE_HEIGHT = 80
MAX_CONSOLE_HEIGHT = 1_200
MIN_UI_SCALE = 0.8
MAX_UI_SCALE = 2.0


class SettingsError(ValueError):
    """Raised when settings cannot be represented or persisted safely."""


class Severity(StrEnum):
    """Console severity, ordered from least to most severe."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    @property
    def rank(self) -> int:
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.DEBUG: 10,
    Severity.INFO: 20,
    Severity.WARNING: 30,
    Severity.ERROR: 40,
}


class CloseAction(StrEnum):
    """What the window close button does."""

    MINIMISE_TO_TRAY = "minimise_to_tray"
    EXIT = "exit"


@dataclass(slots=True)
class WindowSettings:
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    x: int | None = None
    y: int | None = None
    maximized: bool = False
    close_action: CloseAction = CloseAction.MINIMISE_TO_TRAY


@dataclass(slots=True)
class NavigationSettings:
    active_page: str = DEFAULT_PAGE_ID


@dataclass(slots=True)
class ConsoleSettings:
    expanded: bool = True
    height: int = DEFAULT_CONSOLE_HEIGHT
    min_severity: Severity = Severity.INFO


@dataclass(slots=True)
class AppearanceSettings:
    ui_scale: float = 1.0


@dataclass(slots=True)
class StartupSettings:
    """Windows login autostart preference.

    ``enabled`` reflects the user's decision, not the registry. The store of
    record for whether the entry exists is the registry itself; drift between
    the two is detected and reported by the startup registration service.
    """

    enabled: bool = False
    prompted: bool = False


@dataclass(slots=True)
class CoreSettings:
    """Orion Core connection configuration.

    Phase 2 introduces a remote Core process with loopbound API. This settings document
    defines how the UI connects to the Core service.
    """

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8765
    token: str = ""


@dataclass(slots=True)
class UiSettings:
    tray_notice_shown: bool = False


@dataclass(slots=True)
class Settings:
    """The complete persisted UI settings document."""

    schema_version: int = SCHEMA_VERSION
    window: WindowSettings = field(default_factory=WindowSettings)
    navigation: NavigationSettings = field(default_factory=NavigationSettings)
    console: ConsoleSettings = field(default_factory=ConsoleSettings)
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    startup: StartupSettings = field(default_factory=StartupSettings)
    ui: UiSettings = field(default_factory=UiSettings)
    core: CoreSettings = field(default_factory=CoreSettings)

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "window": {
                "width": int(self.window.width),
                "height": int(self.window.height),
                "x": None if self.window.x is None else int(self.window.x),
                "y": None if self.window.y is None else int(self.window.y),
                "maximized": bool(self.window.maximized),
                "close_action": CloseAction(self.window.close_action).value,
            },
            "navigation": {"active_page": self.navigation.active_page},
            "console": {
                "expanded": bool(self.console.expanded),
                "height": int(self.console.height),
                "min_severity": Severity(self.console.min_severity).value,
            },
            "appearance": {"ui_scale": float(self.appearance.ui_scale)},
            "startup": {
                "enabled": bool(self.startup.enabled),
                "prompted": bool(self.startup.prompted),
            },
            "ui": {"tray_notice_shown": bool(self.ui.tray_notice_shown)},
            "core": {
                "enabled": bool(self.core.enabled),
                "host": str(self.core.host),
                "port": int(self.core.port),
                "token": self.core.token,
            },
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> tuple[Settings, list[str]]:
        """Build settings from a decoded document, collecting every problem."""
        problems: list[str] = []

        window_raw = _section(raw, "window", problems)
        navigation_raw = _section(raw, "navigation", problems)
        console_raw = _section(raw, "console", problems)
        appearance_raw = _section(raw, "appearance", problems)
        startup_raw = _section(raw, "startup", problems)
        ui_raw = _section(raw, "ui", problems)
        core_raw = _section(raw, "core", problems)

        window = WindowSettings(
            width=_int(
                window_raw, "window", "width", DEFAULT_WIDTH, MIN_WIDTH, MAX_WIDTH, problems
            ),
            height=_int(
                window_raw,
                "window",
                "height",
                DEFAULT_HEIGHT,
                MIN_HEIGHT,
                MAX_HEIGHT,
                problems,
            ),
            x=_optional_int(window_raw, "window", "x", problems),
            y=_optional_int(window_raw, "window", "y", problems),
            maximized=_bool(window_raw, "window", "maximized", False, problems),
            close_action=_enum(
                window_raw,
                "window",
                "close_action",
                CloseAction,
                CloseAction.MINIMISE_TO_TRAY,
                problems,
            ),
        )

        page = navigation_raw.get("active_page", DEFAULT_PAGE_ID)
        if not isinstance(page, str) or page not in PAGE_IDS:
            problems.append(
                f"navigation.active_page: {page!r} is not a known destination; "
                f"using {DEFAULT_PAGE_ID!r}"
            )
            page = DEFAULT_PAGE_ID
        navigation = NavigationSettings(active_page=page)

        console = ConsoleSettings(
            expanded=_bool(console_raw, "console", "expanded", True, problems),
            height=_int(
                console_raw,
                "console",
                "height",
                DEFAULT_CONSOLE_HEIGHT,
                MIN_CONSOLE_HEIGHT,
                MAX_CONSOLE_HEIGHT,
                problems,
            ),
            min_severity=_enum(
                console_raw, "console", "min_severity", Severity, Severity.INFO, problems
            ),
        )

        appearance = AppearanceSettings(
            ui_scale=_float(
                appearance_raw,
                "appearance",
                "ui_scale",
                1.0,
                MIN_UI_SCALE,
                MAX_UI_SCALE,
                problems,
            )
        )

        ui = UiSettings(
            tray_notice_shown=_bool(ui_raw, "ui", "tray_notice_shown", False, problems),
        )

        startup = StartupSettings(
            enabled=_bool(startup_raw, "startup", "enabled", False, problems),
            prompted=_bool(startup_raw, "startup", "prompted", False, problems),
        )

        ui = UiSettings(
            tray_notice_shown=_bool(ui_raw, "ui", "tray_notice_shown", False, problems),
        )

        startup = StartupSettings(
            enabled=_bool(startup_raw, "startup", "enabled", False, problems),
            prompted=_bool(startup_raw, "startup", "prompted", False, problems),
        )

        core = CoreSettings(
            enabled=_bool(core_raw, "core", "enabled", False, problems),
            host=str(core_raw.get("host", DEFAULT_HOST)),
            port=int(core_raw.get("port", DEFAULT_PORT)),
            token=core_raw.get("token", ""),
        )

        settings = cls(
            schema_version=SCHEMA_VERSION,
            window=window,
            navigation=navigation,
            console=console,
            appearance=appearance,
            startup=startup,
            ui=ui,
            core=core,
        )
        return settings, problems

    # -- validation -------------------------------------------------------

    def validate(self) -> list[str]:
        """Return a list of invariant violations; empty means valid."""
        problems: list[str] = []
        if not MIN_WIDTH <= self.window.width <= MAX_WIDTH:
            problems.append(f"window.width {self.window.width} outside {MIN_WIDTH}..{MAX_WIDTH}")
        if not MIN_HEIGHT <= self.window.height <= MAX_HEIGHT:
            problems.append(
                f"window.height {self.window.height} outside {MIN_HEIGHT}..{MAX_HEIGHT}"
            )
        if self.navigation.active_page not in PAGE_IDS:
            problems.append(f"navigation.active_page {self.navigation.active_page!r} unknown")
        if not MIN_CONSOLE_HEIGHT <= self.console.height <= MAX_CONSOLE_HEIGHT:
            problems.append(
                f"console.height {self.console.height} outside "
                f"{MIN_CONSOLE_HEIGHT}..{MAX_CONSOLE_HEIGHT}"
            )
        if not MIN_UI_SCALE <= self.appearance.ui_scale <= MAX_UI_SCALE:
            problems.append(
                f"appearance.ui_scale {self.appearance.ui_scale} outside "
                f"{MIN_UI_SCALE}..{MAX_UI_SCALE}"
            )
        # Validate Core settings
        if self.core.port < 1 or self.core.port > 65535:
            problems.append(f"core.port {self.core.port} outside 1..65535")
        return problems


# ---------------------------------------------------------------------------
# Typed field readers. Each reports a problem and falls back to its default.
# ---------------------------------------------------------------------------


def _section(raw: Mapping[str, Any], key: str, problems: list[str]) -> Mapping[str, Any]:
    value = raw.get(key, {})
    if not isinstance(value, Mapping):
        problems.append(f"{key}: expected an object, got {type(value).__name__}; using defaults")
        return {}
    return value


def _int(
    section: Mapping[str, Any],
    section_name: str,
    key: str,
    default: int,
    low: int,
    high: int,
    problems: list[str],
) -> int:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, int):
        problems.append(
            f"{section_name}.{key}: expected an integer, got {type(value).__name__}; "
            f"using {default}"
        )
        return default
    if not low <= value <= high:
        problems.append(f"{section_name}.{key}: {value} outside {low}..{high}; using {default}")
        return default
    return value


def _optional_int(
    section: Mapping[str, Any], section_name: str, key: str, problems: list[str]
) -> int | None:
    if key not in section or section[key] is None:
        return None
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, int):
        problems.append(
            f"{section_name}.{key}: expected an integer or null, got {type(value).__name__}; "
            "using null"
        )
        return None
    return value


def _float(
    section: Mapping[str, Any],
    section_name: str,
    key: str,
    default: float,
    low: float,
    high: float,
    problems: list[str],
) -> float:
    if key not in section:
        return default
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        problems.append(
            f"{section_name}.{key}: expected a number, got {type(value).__name__}; using {default}"
        )
        return default
    number = float(value)
    if not low <= number <= high:
        problems.append(f"{section_name}.{key}: {number} outside {low}..{high}; using {default}")
        return default
    return number


def _bool(
    section: Mapping[str, Any], section_name: str, key: str, default: bool, problems: list[str]
) -> bool:
    if key not in section:
        return default
    value = section[key]
    if not isinstance(value, bool):
        problems.append(
            f"{section_name}.{key}: expected a boolean, got {type(value).__name__}; using {default}"
        )
        return default
    return value


def _enum[EnumT: StrEnum](
    section: Mapping[str, Any],
    section_name: str,
    key: str,
    enum_type: type[EnumT],
    default: EnumT,
    problems: list[str],
) -> EnumT:
    if key not in section:
        return default
    value = section[key]
    try:
        return enum_type(value)
    except ValueError:
        allowed = ", ".join(member.value for member in enum_type)
        problems.append(
            f"{section_name}.{key}: {value!r} is not one of [{allowed}]; using {default.value!r}"
        )
        return default
