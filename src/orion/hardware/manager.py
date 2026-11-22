"""Hardware and performance manager for Orion."""

from __future__ import annotations

import json
import sys

from orion.hardware.models import (
    BenchmarkResult,
    EnvironmentManifest,
    GPUInfo,
    HardwareInventory,
    TelemetrySnapshot,
)


class HardwareManager:
    def __init__(self) -> None:
        self._inventory: HardwareInventory | None = None
        self._telemetry: list[TelemetrySnapshot] = []
        self._benchmarks: list[BenchmarkResult] = []

    def collect_inventory(self) -> HardwareInventory:
        inventory = HardwareInventory(
            os_version=sys.version.split(" (")[-1].strip(")")
            if sys.platform == "win32"
            else sys.platform,
            cpu="unknown",
            ram_mb=0,
            python_version=sys.version.split()[0],
        )
        # Try to read GPU info from basic diagnostics without external deps.
        gpu = GPUInfo(name="unknown")
        try:
            import platform

            gpu.name = platform.processor() or "unknown"
        except Exception:
            pass
        inventory.gpus = [gpu]
        self._inventory = inventory
        return inventory

    def get_inventory(self) -> HardwareInventory:
        if self._inventory is None:
            return self.collect_inventory()
        return self._inventory

    def record_telemetry(self, snap: TelemetrySnapshot) -> TelemetrySnapshot:
        self._telemetry.append(snap)
        return snap

    def get_telemetry(self) -> list[TelemetrySnapshot]:
        return list(self._telemetry)

    def record_benchmark(self, result: BenchmarkResult) -> BenchmarkResult:
        self._benchmarks.append(result)
        return result

    def get_benchmarks(self) -> list[BenchmarkResult]:
        return list(self._benchmarks)

    def export_environment(self) -> EnvironmentManifest:
        inv = self.get_inventory()
        return EnvironmentManifest(
            os_version=inv.os_version,
            os_arch=inv.os_arch,
            cpu=inv.cpu,
            ram_mb=inv.ram_mb,
            gpus=inv.gpus,
            python_version=inv.python_version,
        )

    def save_benchmark_report(self, path: str) -> None:
        data = [b.as_dict() for b in self._benchmarks]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"benchmarks": data, "inventory": self.get_inventory().as_dict()}, f, indent=2
            )
