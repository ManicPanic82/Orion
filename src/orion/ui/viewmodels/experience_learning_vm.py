"""Experience & Learning view model — review experiences and Evolution pipelines."""

from __future__ import annotations

from orion.experience.manager import ExperienceRecorder
from orion.learning.manager import LearningManager
from orion.learning.models import DatasetVersion, PromotionRecord, TrainingRun

__all__ = ["ExperienceLearningViewModel"]


class ExperienceLearningViewModel:
    """Exposes experience review and Orion Evolution pipeline state."""

    def __init__(
        self,
        experience_recorder: ExperienceRecorder,
        learning_manager: LearningManager,
    ) -> None:
        self._experience_recorder = experience_recorder
        self._learning_manager = learning_manager

    def experiences(self):  # noqa: ANN201 - list[Experience]
        return self._experience_recorder.list_experiences()

    def datasets(self) -> list[DatasetVersion]:
        return self._learning_manager.list_datasets()

    def runs(self) -> list[TrainingRun]:
        return self._learning_manager.list_runs()

    def promotions(self) -> list[PromotionRecord]:
        return self._learning_manager.list_promotions()
