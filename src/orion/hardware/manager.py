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
    Vendor,
)


def _vendor_for_name(name: str) -> Vendor:
    upper = name.upper()
    if "NVIDIA" in upper:
        return Vendor.NVIDIA
    if "AMD" in upper or "ATI" in upper:
        return Vendor.AMD
    if "INTEL" in upper:
        return Vendor.INTEL
    return Vendor.OTHER


class HardwareManager:
    def __init__(self) -> None:
        self._inventory: HardwareInventory | None = None
        self._telemetry: list[TelemetrySnapshot] = []
        self._benchmarks: list[BenchmarkResult] = []

    def _run_query(self, script: str, timeout: float = 15.0) -> str:
        """Run a PowerShell query and return its trimmed stdout, or "" on failure."""
        import subprocess

        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (proc.stdout or "").strip()
        except Exception:
            return ""

    def collect_inventory(self) -> HardwareInventory:
        # Real collection: PowerShell (no external deps) queries on Windows.
        cpu = self._run_query(
            "(Get-CimInstance -ClassName Win32_Processor -ErrorAction SilentlyContinue "
            "| Select-Object -First 1 -ExpandProperty Name)"
        )
        ram_bytes = self._run_query(
            "(Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction SilentlyContinue "
            "| Select-Object -First 1 -ExpandProperty TotalPhysicalMemory)"
        )
        try:
            ram_mb = int(ram_bytes) // (1024 * 1024) if ram_bytes else 0
        except ValueError:
            ram_mb = 0
        gpu_name = self._run_query(
            "(Get-CimInstance -ClassName Win32_VideoController -ErrorAction SilentlyContinue "
            "| Where-Object { $_.Name -and $_.Name -notlike '*Microsoft*' } "
            "| Select-Object -First 1 -ExpandProperty Name)"
        )
        inventory = HardwareInventory(
            os_version=sys.version.split(" (")[-1].strip(")")
            if sys.platform == "win32"
            else sys.platform,
            cpu=cpu or "unknown",
            ram_mb=ram_mb,
            python_version=sys.version.split()[0],
        )
        inventory.gpus = [GPUInfo(name=gpu_name or "unknown", vendor=_vendor_for_name(gpu_name))]
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
