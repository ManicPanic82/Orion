"""System Monitor view model — real hardware inventory + telemetry."""

from __future__ import annotations

from orion.hardware.manager import HardwareManager
from orion.hardware.models import HardwareInventory, TelemetrySnapshot

__all__ = ["SystemMonitorViewModel"]


class SystemMonitorViewModel:
    """Hardware inventory, latest telemetry, and refresh via the Hardware Manager."""

    def __init__(self, hardware_manager: HardwareManager) -> None:
        self._hardware = hardware_manager

    def inventory(self) -> HardwareInventory:
        return self._hardware.get_inventory()

    def telemetry(self) -> tuple[TelemetrySnapshot, ...]:
        return tuple(self._hardware.get_telemetry())

    def refresh(self) -> HardwareInventory:
        """Collect the inventory again and record a telemetry snapshot."""
        inventory = self._hardware.collect_inventory()
        self._hardware.record_telemetry(
            TelemetrySnapshot(
                vram_total_mb=sum(gpu.memory_mb for gpu in inventory.gpus if gpu.memory_mb),
                ram_total_mb=float(inventory.ram_mb or 0),
            )
        )
        return inventory
