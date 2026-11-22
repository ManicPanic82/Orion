"""Trainer connector interface for Orion Evolution."""

from __future__ import annotations

from typing import Protocol

from orion.learning.models import TrainingRun, TrainingStatus


class TrainerConnector(Protocol):
    def submit(self, run: TrainingRun) -> TrainingRun: ...
    def status(self, run_id: str) -> TrainingRun: ...
    def cancel(self, run_id: str) -> TrainingRun: ...


class MockTrainerConnector:
    def __init__(self) -> None:
        self._runs: dict[str, TrainingRun] = {}

    def submit(self, run: TrainingRun) -> TrainingRun:
        run.status = TrainingStatus.RUNNING
        import datetime as _dt

        run.started_at = _dt.datetime.now(_dt.UTC).isoformat()
        self._runs[run.run_id] = run
        # Immediately complete for mock.
        run.status = TrainingStatus.COMPLETED
        run.finished_at = _dt.datetime.now(_dt.UTC).isoformat()
        run.output_path = f"mock://adapter/{run.run_id}"
        run.metrics = {"loss": 0.1, "accuracy": 0.9}
        return run

    def status(self, run_id: str) -> TrainingRun:
        if run_id not in self._runs:
            raise KeyError(f"run not found: {run_id}")
        return self._runs[run_id]

    def cancel(self, run_id: str) -> TrainingRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        run.status = TrainingStatus.CANCELLED
        return run
