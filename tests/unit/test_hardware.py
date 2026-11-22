"""Tests for hardware inventory/telemetry."""

from __future__ import annotations

import tempfile
from pathlib import Path

from orion.hardware import BenchmarkResult, HardwareManager, TelemetrySnapshot
from orion.hardware.models import Vendor


def _fake_queries(cpu="", ram_bytes="", gpu=""):
    def _run_query(self: HardwareManager, script: str, timeout: float = 15.0) -> str:
        if "Win32_Processor" in script:
            return cpu
        if "TotalPhysicalMemory" in script:
            return ram_bytes
        if "Win32_VideoController" in script:
            return gpu
        return ""

    return _run_query


def test_inventory_collects_real_values_when_queries_succeed(monkeypatch) -> None:
    monkeypatch.setattr(
        HardwareManager,
        "_run_query",
        _fake_queries(
            cpu="AMD Ryzen 9 7950X",
            ram_bytes=str(64 * 1024**3),
            gpu="NVIDIA GeForce RTX 4090",
        ),
    )
    inv = HardwareManager().collect_inventory()
    assert inv.cpu == "AMD Ryzen 9 7950X"
    assert inv.ram_mb == 65536
    assert inv.gpus[0].name == "NVIDIA GeForce RTX 4090"
    assert inv.gpus[0].vendor is Vendor.NVIDIA


def test_inventory_vendor_detection() -> None:
    assert HardwareManager and _vendor_is("AMD Radeon RX 5700 XT", Vendor.AMD)
    assert _vendor_is("Intel UHD Graphics 770", Vendor.INTEL)
    assert _vendor_is("ATI Radeon HD 4800", Vendor.AMD)
    assert _vendor_is("Some Vendor XYZ", Vendor.OTHER)


def _vendor_is(name: str, expected: Vendor) -> bool:
    from orion.hardware.manager import _vendor_for_name

    return _vendor_for_name(name) is expected


def test_inventory_falls_back_when_queries_return_nothing(monkeypatch) -> None:
    monkeypatch.setattr(HardwareManager, "_run_query", _fake_queries())
    inv = HardwareManager().collect_inventory()
    assert inv.cpu == "unknown"
    assert inv.ram_mb == 0
    assert inv.gpus[0].name == "unknown"


def test_inventory_collected() -> None:
    mgr = HardwareManager()
    inv = mgr.collect_inventory()
    assert inv.python_version
    assert inv.gpus


def test_telemetry_recorded() -> None:
    mgr = HardwareManager()
    snap = mgr.record_telemetry(TelemetrySnapshot())
    assert mgr.get_telemetry()[0] is snap


def test_benchmark_recorded() -> None:
    mgr = HardwareManager()
    mgr.record_benchmark(BenchmarkResult(model="mock", tokens_per_second=10.0))
    assert mgr.get_benchmarks()[0].tokens_per_second == 10.0


def test_report_saved() -> None:
    mgr = HardwareManager()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "report.json"
        mgr.save_benchmark_report(str(p))
        assert p.exists()

def test_inventory_collects_all_gpus_os_and_memory(monkeypatch) -> None:
    def query(self: HardwareManager, script: str, timeout: float = 15.0) -> str:
        if "Win32_OperatingSystem" in script:
            return '{"Caption":"Microsoft Windows 10 Pro","Version":"10.0.19045","BuildNumber":"19045","OSArchitecture":"64-bit"}'
        if "Win32_VideoController" in script:
            return (
                '[{"Name":"NVIDIA GeForce GTX 1660","AdapterRAM":6442450944,'
                '"DriverVersion":"1.2.3","PNPDeviceID":"PCI\\\\VEN_10DE"},'
                '{"Name":"Intel UHD Graphics","AdapterRAM":1073741824,'
                '"DriverVersion":"4.5.6","PNPDeviceID":"PCI\\\\VEN_8086"}]'
            )
        return ""

    monkeypatch.setattr(HardwareManager, "_run_query", query)
    inventory = HardwareManager().collect_inventory()
    assert inventory.os_version == "Microsoft Windows 10 Pro 10.0.19045 19045"
    assert inventory.os_arch == "x64"
    assert len(inventory.gpus) == 2
    assert inventory.gpus[0].memory_mb == 6144
    assert inventory.gpus[0].driver_version == "1.2.3"
    assert inventory.gpus[1].vendor is Vendor.INTEL
