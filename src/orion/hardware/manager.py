"""Hardware and performance manager for Orion."""

from __future__ import annotations

import json
import platform
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
        os_raw = self._run_query(
            "(Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue "
            "| Select-Object -First 1 Caption,Version,BuildNumber "
            "| ConvertTo-Json -Compress)"
        )
        gpu_raw = self._run_query(
            "Get-CimInstance -ClassName Win32_VideoController -ErrorAction SilentlyContinue "
            "| Where-Object { $_.Name -and $_.Name -notlike '*Microsoft*' } "
            "| Select-Object Name,DriverVersion,PNPDeviceID,AdapterRAM "
            "| ConvertTo-Json -Compress"
        )
        # WMI AdapterRAM is a 32-bit field on Windows and cannot reliably
        # represent modern GPUs with more than 4 GiB. Prefer nvidia-smi when
        # available for NVIDIA VRAM, driver, and device identity.
        nvidia_raw = self._run_query(
            "$tool = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue; "
            "if ($tool) { & $tool.Source --query-gpu=name,memory.total,driver_version,uuid "
            "--format=csv,noheader,nounits }"
        )

        os_version = platform.platform()
        if os_raw:
            try:
                os_data = json.loads(os_raw)
                if isinstance(os_data, dict):
                    caption = str(os_data.get("Caption", "")).strip()
                    version = str(os_data.get("Version", "")).strip()
                    build = str(os_data.get("BuildNumber", "")).strip()
                    os_version = " ".join(part for part in (caption, version, build) if part)
            except (TypeError, ValueError):
                os_version = os_raw

        gpu_items: list[dict[str, object] | str] = []
        if gpu_raw:
            try:
                parsed = json.loads(gpu_raw)
                gpu_items = parsed if isinstance(parsed, list) else [parsed]
            except (TypeError, ValueError):
                # Retain compatibility with a single plain-text device name
                # returned by older PowerShell wrappers and test doubles.
                gpu_items = [line.strip() for line in gpu_raw.splitlines() if line.strip()]

        gpus: list[GPUInfo] = []
        for item in gpu_items:
            if isinstance(item, str):
                name = item
                driver = ""
                device_id = ""
                memory_bytes = 0
            elif isinstance(item, dict):
                name = str(item.get("Name") or "")
                driver = str(item.get("DriverVersion") or "")
                device_id = str(item.get("PNPDeviceID") or "")
                try:
                    memory_bytes = int(item.get("AdapterRAM") or 0)
                except (TypeError, ValueError):
                    memory_bytes = 0
                # Win32_VideoController.AdapterRAM is a 32-bit field; a
                # 4-GiB value is commonly a saturation marker, not real VRAM.
                if memory_bytes >= 4 * 1024**3:
                    memory_bytes = 0
            else:
                continue
            if name:
                vendor = _vendor_for_name(name)
                # Prefer nvidia-smi's per-device rows for NVIDIA adapters;
                # WMI cannot distinguish identical models reliably.
                if vendor is Vendor.NVIDIA and nvidia_raw:
                    continue
                gpus.append(
                    GPUInfo(
                        name=name,
                        vendor=vendor,
                        memory_mb=max(memory_bytes, 0) // (1024 * 1024),
                        driver_version=driver,
                        device_id=device_id,
                    )
                )

        inventory = HardwareInventory(
            os_version=os_version,
            os_arch=platform.machine() or "unknown",
            cpu=cpu or "unknown",
            ram_mb=ram_mb,
            python_version=sys.version.split()[0],
            gpus=gpus or [GPUInfo(name="unknown", vendor=Vendor.OTHER)],
        )
        for line in nvidia_raw.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 4:
                continue
            name, memory_text, driver, device_id = parts[:4]
            try:
                memory_mb = int(memory_text)
            except ValueError:
                memory_mb = 0
            gpus.append(
                GPUInfo(
                    name=name,
                    vendor=Vendor.NVIDIA,
                    memory_mb=max(memory_mb, 0),
                    driver_version=driver,
                    device_id=device_id,
                )
            )
        gpus.sort(key=lambda gpu: (gpu.vendor is not Vendor.NVIDIA, gpu.name, gpu.device_id))
        inventory.gpus = gpus or [GPUInfo(name="unknown", vendor=Vendor.OTHER)]
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
