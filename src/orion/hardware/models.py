"""Hardware inventory and telemetry models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class Vendor(StrEnum):
    NVIDIA = "NVIDIA"
    INTEL = "Intel"
    AMD = "AMD"
    OTHER = "other"


@dataclass(slots=True)
class GPUInfo:
    name: str = ""
    vendor: Vendor = Vendor.OTHER
    compute_capability: str = ""
    memory_mb: int = 0
    driver_version: str = ""
    device_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "vendor": self.vendor.value,
            "compute_capability": self.compute_capability,
            "memory_mb": self.memory_mb,
            "driver_version": self.driver_version,
            "device_id": self.device_id,
        }


@dataclass(slots=True)
class HardwareInventory:
    inventory_id: str = field(default_factory=lambda: str(uuid4()))
    collected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    os_version: str = ""
    os_arch: str = "x64"
    cpu: str = ""
    ram_mb: int = 0
    gpus: list[GPUInfo] = field(default_factory=list)
    python_version: str = ""
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "inventory_id": self.inventory_id,
            "collected_at": self.collected_at,
            "os_version": self.os_version,
            "os_arch": self.os_arch,
            "cpu": self.cpu,
            "ram_mb": self.ram_mb,
            "gpus": [g.as_dict() for g in self.gpus],
            "python_version": self.python_version,
            "notes": list(self.notes),
        }


@dataclass(slots=True)
class TelemetrySnapshot:
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    gpu: GPUInfo | None = None
    vram_used_mb: float = 0.0
    vram_total_mb: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    cpu_temp_c: float | None = None
    power_w: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "vram_used_mb": self.vram_used_mb,
            "vram_total_mb": self.vram_total_mb,
            "ram_used_mb": self.ram_used_mb,
            "ram_total_mb": self.ram_total_mb,
            "cpu_temp_c": self.cpu_temp_c,
            "power_w": self.power_w,
            "gpu": self.gpu.as_dict() if self.gpu else None,
        }


@dataclass(slots=True)
class BenchmarkResult:
    result_id: str = field(default_factory=lambda: str(uuid4()))
    model: str = ""
    adapter: str | None = None
    quantisation: str = "none"
    context_length: int = 0
    load_time_s: float = 0.0
    time_to_first_token_s: float = 0.0
    tokens_per_second: float = 0.0
    peak_vram_mb: float = 0.0
    peak_ram_mb: float = 0.0
    sustained_ok: bool = True
    output_sample: str = ""
    notes: str = ""
    run_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "model": self.model,
            "adapter": self.adapter,
            "quantisation": self.quantisation,
            "context_length": self.context_length,
            "load_time_s": self.load_time_s,
            "time_to_first_token_s": self.time_to_first_token_s,
            "tokens_per_second": self.tokens_per_second,
            "peak_vram_mb": self.peak_vram_mb,
            "peak_ram_mb": self.peak_ram_mb,
            "sustained_ok": self.sustained_ok,
            "output_sample": self.output_sample,
            "notes": self.notes,
            "run_at": self.run_at,
        }


@dataclass(slots=True)
class EnvironmentManifest:
    os_version: str = ""
    os_arch: str = "x64"
    cpu: str = ""
    ram_mb: int = 0
    gpus: list[GPUInfo] = field(default_factory=list)
    python_version: str = ""
    cuda_version: str = ""
    torch_version: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "os_version": self.os_version,
            "os_arch": self.os_arch,
            "cpu": self.cpu,
            "ram_mb": self.ram_mb,
            "gpus": [g.as_dict() for g in self.gpus],
            "python_version": self.python_version,
            "cuda_version": self.cuda_version,
            "torch_version": self.torch_version,
            "created_at": self.created_at,
        }
