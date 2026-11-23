"""System Monitor (Phase 15): real-time inventory and telemetry."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from orion.hardware.manager import HardwareManager
from orion.ui.viewmodels.system_monitor_vm import SystemMonitorViewModel
from orion.ui.widgets.card import Card

__all__ = ["SystemMonitorPage"]


class SystemMonitorPage(QWidget):
    """Shows the real hardware inventory from the Hardware Manager."""

    def __init__(self, hardware_manager: HardwareManager | None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SystemMonitorPage")
        self._vm = SystemMonitorViewModel(hardware_manager or HardwareManager())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("System Monitor", self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        card = Card("Hardware Inventory", "Real measurements via PowerShell collection.", self)
        inventory_card_body = card.body_layout()
        self._rows: list[tuple[str, QLabel]] = []
        for row_label in ("Operating System", "Architecture", "CPU", "RAM", "GPU(s)", "Python"):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(QLabel(f"{row_label}:", self))
            value = QLabel("", self)
            value.setProperty("role", "muted")
            value.setWordWrap(True)
            row.addWidget(value, 1)
            inventory_card_body.addLayout(row)
            self._rows.append((row_label.lower(), value))
        outer.addWidget(card)

        telemetry_card = Card("Telemetry", "Latest recorded telemetry snapshot.", self)
        self._telemetry_lines: list[QLabel] = []
        for row_label in (
            "VRAM total (MiB)",
            "VRAM used (MiB)",
            "RAM total (MiB)",
            "RAM used (MiB)",
        ):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(QLabel(f"{row_label}:", self))
            value = QLabel("", self)
            value.setProperty("role", "muted")
            row.addWidget(value, 1)
            telemetry_card.add_layout(row)
            self._telemetry_lines.append(value)
        outer.addWidget(telemetry_card)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        self._refresh_button = QPushButton("Refresh", self)
        self._refresh_button.setObjectName("Secondary")
        self._refresh_button.clicked.connect(self.refresh)
        row.addWidget(self._refresh_button, 0)
        outer.addLayout(row)

        self.refresh()

    def refresh(self) -> None:
        inventory = self._vm.refresh()
        gpus = ", ".join(
            f"{gpu.name} [{gpu.vendor.value}] {gpu.memory_mb} MiB" for gpu in inventory.gpus
        )
        rows = {
            "operating system": inventory.os_version or "unknown",
            "architecture": inventory.os_arch,
            "cpu": inventory.cpu or "unknown",
            "ram": f"{inventory.ram_mb} MiB",
            "gpu(s)": gpus or "unknown",
            "python": inventory.python_version or "unknown",
        }
        for label, value in self._rows:
            value.setText(str(rows.get(label, "")))
        telemetry = self._vm.telemetry()
        latest = telemetry[-1] if telemetry else None
        if latest is not None:
            self._telemetry_lines[0].setText(f"{latest.vram_total_mb:.0f}")
            self._telemetry_lines[1].setText(f"{latest.vram_used_mb:.0f}")
            self._telemetry_lines[2].setText(f"{latest.ram_total_mb:.0f}")
            self._telemetry_lines[3].setText(f"{latest.ram_used_mb:.0f}")
