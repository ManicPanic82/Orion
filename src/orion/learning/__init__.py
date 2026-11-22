"""Learning pipeline for Orion Evolution."""

from orion.learning.builder import BUILDER_VERSION, build_dataset
from orion.learning.connector import MockTrainerConnector, TrainerConnector
from orion.learning.manager import LearningManager
from orion.learning.models import (
    DatasetVersion,
    EvaluationResult,
    PromotionRecord,
    PromotionStatus,
    TrainingRun,
    TrainingStatus,
)

__all__ = [
    "BUILDER_VERSION",
    "DatasetVersion",
    "EvaluationResult",
    "LearningManager",
    "MockTrainerConnector",
    "PromotionRecord",
    "PromotionStatus",
    "TrainerConnector",
    "TrainingRun",
    "TrainingStatus",
    "build_dataset",
]
# Aliases
EvolutionManager = LearningManager
LearningEngine = LearningManager
