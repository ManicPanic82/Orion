"""Small Qt helpers shared by widgets."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

__all__ = ["repolish"]


def repolish(widget: QWidget) -> None:
    """Re-apply the stylesheet after a dynamic property changes."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
