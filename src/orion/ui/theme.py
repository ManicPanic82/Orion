"""Design tokens and the single generated stylesheet for Orion Workstation.

Every colour, spacing step, and radius lives here exactly once. Widgets must not
hard-code hex values; they either consume these tokens directly or use one of the
stylesheet selectors defined below. That keeps the dark theme consistent and
makes a future theme change a one-file edit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from string import Template

__all__ = ["TOKENS", "Tokens", "build_stylesheet"]


@dataclass(frozen=True, slots=True)
class Tokens:
    # Surfaces
    bg_base: str = "#0B0F14"
    bg_surface: str = "#121821"
    bg_raised: str = "#18202B"
    bg_input: str = "#0E141C"

    # Lines
    border: str = "#24303F"
    border_strong: str = "#33445A"

    # Text
    text_primary: str = "#E6EDF5"
    text_secondary: str = "#9FB0C4"
    text_muted: str = "#6B7C91"

    # Accents and status
    accent: str = "#3B82F6"
    accent_hover: str = "#2F6FE0"
    accent_teal: str = "#14B8A6"
    accent_mock: str = "#A855F7"
    success: str = "#22C55E"
    warning: str = "#F59E0B"
    danger: str = "#EF4444"

    # Spacing scale
    space_xs: int = 4
    space_sm: int = 8
    space_md: int = 12
    space_lg: int = 16
    space_xl: int = 24
    space_2xl: int = 32

    # Radii
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12

    # Typography
    font_family: str = '"Segoe UI Variable Text", "Segoe UI", sans-serif'
    font_mono: str = '"Cascadia Mono", "Consolas", monospace'


TOKENS = Tokens()


_STYLESHEET = Template(
    """
/* Base ------------------------------------------------------------- */
QMainWindow,
QWidget#PageRoot {
    background: $bg_base;
}

QWidget {
    color: $text_primary;
    font-family: $font_family;
    font-size: 13px;
}

QToolTip {
    background: $bg_raised;
    color: $text_primary;
    border: 1px solid $border_strong;
    padding: 6px 8px;
}

/* Navigation rail -------------------------------------------------- */
QWidget#NavRail {
    background: $bg_surface;
    border-right: 1px solid $border;
}

QLabel#NavBrand {
    font-size: 19px;
    font-weight: 600;
    letter-spacing: 2px;
    color: $text_primary;
}

QLabel#NavBrandSub {
    font-size: 10px;
    letter-spacing: 1px;
    color: $text_muted;
}

QPushButton#NavItem {
    text-align: left;
    padding: 9px 12px;
    border: 1px solid transparent;
    border-radius: $radius_md;
    background: transparent;
    color: $text_secondary;
    font-size: 13px;
}

QPushButton#NavItem:hover {
    background: $bg_raised;
    color: $text_primary;
}

QPushButton#NavItem:checked {
    background: $bg_raised;
    border: 1px solid $border_strong;
    color: $text_primary;
    font-weight: 600;
}

/* Cards ------------------------------------------------------------ */
QFrame#Card {
    background: $bg_surface;
    border: 1px solid $border;
    border-radius: $radius_lg;
}

QFrame#Divider {
    background: $border;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

/* Text roles ------------------------------------------------------- */
QLabel[role="display"] {
    font-size: 23px;
    font-weight: 600;
}

QLabel[role="title"] {
    font-size: 15px;
    font-weight: 600;
}

QLabel[role="subtitle"] {
    color: $text_secondary;
    font-size: 12px;
}

QLabel[role="muted"] {
    color: $text_muted;
    font-size: 12px;
}

QLabel[role="mono"] {
    font-family: $font_mono;
    font-size: 12px;
}

QLabel[tone="danger"] {
    color: $danger;
}

/* Status pills ----------------------------------------------------- */
QLabel#StatusPill {
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#StatusPill[tone="mock"] {
    background: rgba(168, 85, 247, 0.16);
    color: $accent_mock;
    border: 1px solid rgba(168, 85, 247, 0.45);
}

QLabel#StatusPill[tone="operational"] {
    background: rgba(34, 197, 94, 0.14);
    color: $success;
    border: 1px solid rgba(34, 197, 94, 0.40);
}

QLabel#StatusPill[tone="degraded"] {
    background: rgba(245, 158, 11, 0.14);
    color: $warning;
    border: 1px solid rgba(245, 158, 11, 0.40);
}

QLabel#StatusPill[tone="unavailable"] {
    background: rgba(107, 124, 145, 0.14);
    color: $text_muted;
    border: 1px solid rgba(107, 124, 145, 0.40);
}

QLabel#StatusPill[tone="danger"] {
    background: rgba(239, 68, 68, 0.14);
    color: $danger;
    border: 1px solid rgba(239, 68, 68, 0.40);
}

/* Buttons ---------------------------------------------------------- */
QPushButton {
    background: $bg_raised;
    border: 1px solid $border_strong;
    border-radius: $radius_md;
    padding: 7px 14px;
    color: $text_primary;
}

QPushButton:hover {
    border-color: $accent;
}

QPushButton:pressed {
    background: $bg_input;
}

QPushButton:disabled {
    color: $text_muted;
    border-color: $border;
    background: $bg_surface;
}

QPushButton#Primary {
    background: $accent;
    border: 1px solid $accent;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#Primary:hover {
    background: $accent_hover;
    border-color: $accent_hover;
}

QPushButton#Primary:disabled {
    background: $bg_raised;
    border-color: $border;
    color: $text_muted;
}

QPushButton#Ghost {
    background: transparent;
    border: 1px solid transparent;
    color: $text_secondary;
    padding: 5px 8px;
}

QPushButton#Ghost:hover {
    background: $bg_raised;
    color: $text_primary;
}

/* Inputs ----------------------------------------------------------- */
QLineEdit,
QPlainTextEdit,
QTextEdit,
QComboBox {
    background: $bg_input;
    border: 1px solid $border;
    border-radius: $radius_md;
    padding: 8px 10px;
    color: $text_primary;
    selection-background-color: $accent;
    selection-color: #FFFFFF;
}

QLineEdit:focus,
QPlainTextEdit:focus,
QTextEdit:focus,
QComboBox:focus {
    border-color: $accent;
}

QPlainTextEdit#ConsoleOutput {
    font-family: $font_mono;
    font-size: 12px;
    background: $bg_base;
    border: 1px solid $border;
}

QCheckBox {
    spacing: 8px;
    color: $text_primary;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $border_strong;
    border-radius: $radius_sm;
    background: $bg_input;
}

QCheckBox::indicator:hover {
    border-color: $accent;
}

QCheckBox::indicator:checked {
    background: $accent;
    border-color: $accent;
}

QCheckBox::indicator:disabled {
    border-color: $border;
    background: $bg_surface;
}

/* Splitter and scrollbars ------------------------------------------ */
QSplitter::handle {
    background: $border;
    height: 1px;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: $border_strong;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: $text_muted;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: $border_strong;
    border-radius: 5px;
    min-width: 24px;
}

QScrollBar::add-line,
QScrollBar::sub-line,
QScrollBar::add-page,
QScrollBar::sub-page {
    background: transparent;
    border: none;
    height: 0;
    width: 0;
}

/* Status bar ------------------------------------------------------- */
QStatusBar {
    background: $bg_surface;
    border-top: 1px solid $border;
    color: $text_muted;
}

QStatusBar::item {
    border: none;
}
"""
)


def build_stylesheet(tokens: Tokens = TOKENS) -> str:
    """Render the application stylesheet from ``tokens``."""
    return _STYLESHEET.substitute(asdict(tokens))
