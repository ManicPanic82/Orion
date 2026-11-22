"""Learning pipeline manager for Orion Evolution."""

from __future__ import annotations

import copy
import datetime
import math
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
        if passed is not None:
            raise ValueError(
                "passed is evaluator output, not caller input; omit it and provide held-out metrics"
            )
        accuracy = metrics.get("accuracy")
        if (
            isinstance(accuracy, bool)
            or not isinstance(accuracy, (int, float))
            or not math.isfinite(accuracy)
            or not 0.0 <= accuracy <= 1.0
        ):
            raise ValueError("evaluation requires a finite accuracy metric between 0 and 1")
        if metrics.get("held_out") is not True:
            raise ValueError("evaluation must identify a held-out dataset")
        dataset_id = metrics.get("dataset_id")
        with self._lock:
            dataset = self._datasets.get(dataset_id) if isinstance(dataset_id, str) else None
        if dataset is None or not dataset.eval_ids:
            raise ValueError("evaluation must reference a registered dataset with an eval split")
        if metrics.get("eval_dataset_checksum") != dataset.checksum:
            raise ValueError("evaluation dataset checksum does not match the registered dataset")
        try:
            evaluated_examples = int(metrics.get("eval_examples", 0))
        except (TypeError, ValueError):
            evaluated_examples = 0
        if evaluated_examples != len(dataset.eval_ids):
            raise ValueError("evaluation example count does not match the held-out split")
        passed = bool(accuracy >= 0.8)
        if metrics.get("regression") is False:
            # Regression checks: a known regression fails the candidate.
            passed = False
        ev = EvaluationResult(
            candidate_profile_id=candidate_profile_id,
            baseline_profile_id=baseline_profile_id or "",
            metrics=metrics,
            passed=passed,
            details="evaluation completed",
        )
        with self._lock:
            self._evaluations[ev.evaluation_id] = copy.deepcopy(ev)
        return ev

    def get_evaluation(self, evaluation_id: str) -> EvaluationResult:
        with self._lock:
            if evaluation_id not in self._evaluations:
                raise KeyError(f"evaluation not found: {evaluation_id}")
            return copy.deepcopy(self._evaluations[evaluation_id])

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
        candidate_id = getattr(candidate_profile, "profile_id", str(candidate_profile))
        # Mandatory, candidate-specific held-out evaluation before promotion.
        if evaluation is None:
            raise ValueError("promotion requires a held-out evaluation result")
        with self._lock:
            registered = self._evaluations.get(evaluation.evaluation_id)
        if registered is None or registered != evaluation:
            raise ValueError("promotion requires an evaluation issued by this LearningManager")
        metrics = evaluation.metrics
        dataset_id = metrics.get("dataset_id")
        with self._lock:
            dataset = self._datasets.get(dataset_id) if isinstance(dataset_id, str) else None
        if (
            dataset is None
            or not dataset.eval_ids
            or metrics.get("held_out") is not True
            or metrics.get("eval_dataset_checksum") != dataset.checksum
        ):
            raise ValueError("evaluation lacks registered held-out dataset provenance")
        try:
            evaluated_examples = int(metrics.get("eval_examples", 0))
            accuracy_value = metrics.get("accuracy", -1)
            accuracy = float(accuracy_value)
        except (TypeError, ValueError):
            evaluated_examples = 0
            accuracy = -1
        if (
            isinstance(accuracy_value, bool)
            or evaluated_examples != len(dataset.eval_ids)
            or not math.isfinite(accuracy)
            or not 0 <= accuracy <= 1
        ):
            raise ValueError("evaluation metrics are incomplete or invalid")
        if evaluation.candidate_profile_id != candidate_id:
            raise ValueError("evaluation does not belong to the candidate being promoted")
        if not evaluation.passed or accuracy < 0.8 or metrics.get("regression") is False:
            raise ValueError("candidate failed evaluation")
        record = PromotionRecord(
            candidate_profile_id=candidate_id,
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
