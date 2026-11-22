"""Tests for hardware inventory/telemetry."""

from __future__ import annotations

import tempfile
from pathlib import Path

from orion.hardware import BenchmarkResult, HardwareManager, TelemetrySnapshot


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
