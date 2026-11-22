"""Expandable activity console.

The panel is a renderer over :class:`orion.ui.viewmodels.console_vm.ConsoleViewModel`.
It performs no buffering or filtering of its own, so the bounded-buffer and
redaction rules are tested once, without Qt.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from orion.config.settings import ConsoleSettings, Severity
from orion.ui.viewmodels.console_vm import ConsoleViewModel

__all__ = ["ConsolePanel"]

_EXPANDED_MAX_HEIGHT = 16_777_215


class ConsolePanel(QWidget):
    """Bottom console with severity filtering and collapse."""

    expanded_changed = Signal(bool)
    min_severity_changed = Signal(object)

    def __init__(
        self,
        console: ConsoleViewModel,
        settings: ConsoleSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ConsolePanel")
        self._console = console
        self._expanded = bool(settings.expanded)
        self._min_severity = Severity(settings.min_severity)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget(self)
        header.setObjectName("ConsoleHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 8, 16, 8)
        header_layout.setSpacing(10)

        self._toggle = QPushButton("", header)
        self._toggle.setObjectName("Ghost")
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.clicked.connect(self._on_toggle)
        header_layout.addWidget(self._toggle)

        self._count = QLabel("", header)
        self._count.setProperty("role", "muted")
        header_layout.addWidget(self._count)

        header_layout.addStretch(1)

        filter_label = QLabel("Minimum level", header)
        filter_label.setProperty("role", "muted")
        header_layout.addWidget(filter_label)

        self._severity = QComboBox(header)
        # Store the plain value: Qt's QVariant converts str subclasses to str, so
        # relying on itemData to round-trip an enum would silently lose its type.
        for severity in Severity:
            self._severity.addItem(severity.value)
        self._severity.setCurrentIndex(self._severity.findText(self._min_severity.value))
        self._severity.currentIndexChanged.connect(self._on_severity_changed)
        header_layout.addWidget(self._severity)

        self._clear = QPushButton("Clear", header)
        self._clear.setObjectName("Ghost")
        self._clear.clicked.connect(self._console.clear)
        header_layout.addWidget(self._clear)

        outer.addWidget(header)

        self._output = QPlainTextEdit(self)
        self._output.setObjectName("ConsoleOutput")
        self._output.setReadOnly(True)
        self._output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._output.setPlaceholderText("No activity recorded.")
        outer.addWidget(self._output, 1)

        self._console.add_listener(self._render)
        self._set_expanded(self._expanded, emit=False)
        self._render()

    # -- public API -------------------------------------------------------

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        self._set_expanded(bool(expanded), emit=True)

    def min_severity(self) -> Severity:
        return self._min_severity

    def set_min_severity(self, severity: Severity) -> None:
        index = self._severity.findText(severity.value)
        if index >= 0:
            self._severity.setCurrentIndex(index)

    def output_text(self) -> str:
        return self._output.toPlainText()

    # -- internals --------------------------------------------------------

    def _on_toggle(self) -> None:
        self._set_expanded(not self._expanded, emit=True)

    def _set_expanded(self, expanded: bool, *, emit: bool) -> None:
        self._expanded = expanded
        self._toggle.setText("Hide console" if expanded else "Show console")
        self._output.setVisible(expanded)
        if expanded:
            self.setMaximumHeight(_EXPANDED_MAX_HEIGHT)
        else:
            header_height = self._toggle.sizeHint().height() + 20
            self.setMaximumHeight(header_height)
        if emit:
            self.expanded_changed.emit(expanded)

    def _on_severity_changed(self, index: int) -> None:
        try:
            value = Severity(self._severity.itemText(index))
        except ValueError:
            return
        self._min_severity = value
        self._render()
        self.min_severity_changed.emit(value)

    def _render(self) -> None:
        entries = self._console.entries(self._min_severity)
        self._count.setText(f"{len(entries)} shown · {len(self._console)} buffered")

        if not entries:
            self._output.clear()
            return

        lines = [
            f"{entry.timestamp.astimezone():%H:%M:%S}  "
            f"{entry.severity.value:<7}  "
            f"{entry.source:<14}  "
            f"{entry.message}"
            for entry in entries
        ]
        self._output.setPlainText("\n".join(lines))
        scrollbar = self._output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
