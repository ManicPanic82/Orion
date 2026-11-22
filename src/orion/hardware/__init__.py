"""Hardware and performance validation for Orion."""

from orion.hardware.manager import HardwareManager
from orion.hardware.models import (
    BenchmarkResult,
    EnvironmentManifest,
    GPUInfo,
    HardwareInventory,
    TelemetrySnapshot,
    Vendor,
)

__all__ = [
    "BenchmarkResult",
    "EnvironmentManifest",
    "GPUInfo",
    "HardwareInventory",
    "HardwareManager",
    "TelemetrySnapshot",
    "Vendor",
]
# Aliases
HardwareMonitor = HardwareManager
