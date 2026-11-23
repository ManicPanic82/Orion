"""Tests for the Core-backed state provider."""

from __future__ import annotations

from pathlib import Path

from orion.core.service import OrionCore
from orion.core.services import build_default_services
from orion.state.models import StatusKind
from orion.ui.core_state_provider import CoreStateProvider


def test_core_state_provider_is_real_not_mock(tmp_path: Path) -> None:
    provider = CoreStateProvider(
        core=OrionCore(services=build_default_services(db_path=tmp_path / "orion.db"))
    )
    assert provider.is_mock is False
    snapshot = provider.snapshot()
    assert snapshot.is_mock is False
    assert snapshot.agent.kind is StatusKind.OPERATIONAL


def test_core_state_provider_submit_command_runs_the_agent(tmp_path: Path) -> None:
    provider = CoreStateProvider(
        core=OrionCore(services=build_default_services(db_path=tmp_path / "orion.db"))
    )
    provider.start()
    try:
        snapshot = provider.snapshot()
        assert snapshot.model.kind is StatusKind.OPERATIONAL
        assert snapshot.agent.kind is StatusKind.OPERATIONAL
        assert snapshot.tasks == ()

        result = provider.submit_command("echo hello", "req-1")
        assert result.accepted is True
        assert result.simulated is False
        assert result.request_id == "req-1"

        snapshot = provider.snapshot()
        assert len(snapshot.tasks) == 1
        assert snapshot.tasks[0].task_id
        assert snapshot.tasks[0].state.value == "completed"
    finally:
        provider.stop()


def test_core_state_provider_rejects_empty_command(tmp_path: Path) -> None:
    provider = CoreStateProvider(
        core=OrionCore(services=build_default_services(db_path=tmp_path / "orion.db"))
    )
    result = provider.submit_command("   ", "req-2")
    assert result.accepted is False
    assert result.simulated is False
