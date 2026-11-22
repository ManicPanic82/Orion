"""Learning pipeline manager for Orion Evolution."""

from __future__ import annotations

import datetime
import threading
from typing import Any

from orion.experience.models import Experience
from orion.learning.builder import build_dataset
from orion.learning.connector import MockTrainerConnector, TrainerConnector
from orion.learning.models import (
    DatasetVersion,
    EvaluationResult,
    PromotionRecord,
    PromotionStatus,
    TrainingRun,
)
from orion.models import ModelManager


class LearningManager:
    def __init__(
        self,
        connector: TrainerConnector | None = None,
        model_manager: ModelManager | None = None,
    ) -> None:
        self.connector = connector or MockTrainerConnector()
        self.model_manager = model_manager
        self._datasets: dict[str, DatasetVersion] = {}
        self._runs: dict[str, TrainingRun] = {}
        self._evaluations: dict[str, EvaluationResult] = {}
        self._promotions: dict[str, PromotionRecord] = {}
        self._lock = threading.RLock()

    # -- datasets --------------------------------------------------------

    def build_dataset(self, experiences: list[Experience], **kwargs: Any) -> DatasetVersion:
        dataset = build_dataset(experiences, **kwargs)
        with self._lock:
            self._datasets[dataset.dataset_id] = dataset
        return dataset

    def get_dataset(self, dataset_id: str) -> DatasetVersion:
        with self._lock:
            if dataset_id not in self._datasets:
                raise KeyError(f"dataset not found: {dataset_id}")
            return self._datasets[dataset_id]

    def list_datasets(self) -> list[DatasetVersion]:
        with self._lock:
            return list(self._datasets.values())

    # -- training --------------------------------------------------------

    def submit_training(
        self,
        dataset: DatasetVersion,
        *,
        base_model_revision: str = "",
        config: dict[str, Any] | None = None,
    ) -> TrainingRun:
        run = TrainingRun(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.version,
            base_model_revision=base_model_revision,
            config=dict(config or {}),
        )
        run = self.connector.submit(run)
        with self._lock:
            self._runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> TrainingRun:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(f"run not found: {run_id}")
            return self._runs[run_id]

    def list_runs(self) -> list[TrainingRun]:
        with self._lock:
            return list(self._runs.values())

    # -- evaluation ------------------------------------------------------

    def evaluate_candidate(
        self,
        candidate_profile_id: str,
        *,
        baseline_profile_id: str | None = None,
        metrics: dict[str, Any] | None = None,
        passed: bool | None = None,
    ) -> EvaluationResult:
        metrics = dict(metrics or {})
        if passed is None:
            # Simple rule: passed if accuracy >= 0.8 (if provided).
            acc = metrics.get("accuracy")
            passed = True if acc is None else bool(acc >= 0.8)
        ev = EvaluationResult(
            candidate_profile_id=candidate_profile_id,
            baseline_profile_id=baseline_profile_id or "",
            metrics=metrics,
            passed=passed,
            details="evaluation completed",
        )
        with self._lock:
            self._evaluations[ev.evaluation_id] = ev
        return ev

    def get_evaluation(self, evaluation_id: str) -> EvaluationResult:
        with self._lock:
            if evaluation_id not in self._evaluations:
                raise KeyError(f"evaluation not found: {evaluation_id}")
            return self._evaluations[evaluation_id]

    # -- promotion -------------------------------------------------------

    def promote_candidate(
        self,
        candidate_profile: Any,
        *,
        previous_profile_id: str | None = None,
        evaluation: EvaluationResult | None = None,
        approved: bool = False,
        approver: str = "",
    ) -> PromotionRecord:
        if not approved:
            raise PermissionError("promotion requires explicit approval")
        if evaluation is not None and not evaluation.passed:
            raise ValueError("candidate failed evaluation")
        record = PromotionRecord(
            candidate_profile_id=getattr(candidate_profile, "profile_id", str(candidate_profile)),
            previous_profile_id=previous_profile_id,
            status=PromotionStatus.APPROVED,
            approver=approver or "user",
            approved_at=datetime.datetime.now(datetime.UTC).isoformat(),
            rollback_profile_id=previous_profile_id,
            details="promoted with user approval",
        )
        with self._lock:
            self._promotions[record.promotion_id] = record
        # Do not mutate active profile here; caller decides.
        return record

    def rollback(self, promotion_id: str) -> PromotionRecord:
        with self._lock:
            record = self._promotions.get(promotion_id)
            if record is None:
                raise KeyError(f"promotion not found: {promotion_id}")
            record.status = PromotionStatus.ROLLED_BACK
            return record

    def list_promotions(self) -> list[PromotionRecord]:
        with self._lock:
            return list(self._promotions.values())
