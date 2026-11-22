"""Reusable card container with an optional title, subtitle, and header slot."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QVBoxLayout,
    QWidget,
)

__all__ = ["Card"]


class Card(QFrame):
    """A bordered surface that groups related content."""

    def __init__(
        self,
        title: str | None = None,
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        self._header = QHBoxLayout()
        self._header.setSpacing(8)
        self._header.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel(title or "", self)
        self._title.setProperty("role", "title")
        self._title.setVisible(bool(title))
        self._header.addWidget(self._title)
        self._header.addStretch(1)
        outer.addLayout(self._header)

        self._subtitle = QLabel(subtitle or "", self)
        self._subtitle.setProperty("role", "muted")
        self._subtitle.setWordWrap(True)
        self._subtitle.setVisible(bool(subtitle))
        outer.addWidget(self._subtitle)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        outer.addLayout(self.body)

    def add_header_widget(self, widget: QWidget) -> None:
        self._header.addWidget(widget)

    def add_widget(self, widget: QWidget) -> None:
        self.body.addWidget(widget)

    def add_layout(self, layout: QLayout) -> None:
        self.body.addLayout(layout)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))

    def body_layout(self) -> QVBoxLayout:
        return self.body
