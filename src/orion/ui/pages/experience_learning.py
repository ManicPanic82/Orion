"""Experience & Learning (Phases 7–8): experience review and Evolution pipelines."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from orion.experience.manager import ExperienceRecorder
from orion.learning.manager import LearningManager
from orion.ui.viewmodels.experience_learning_vm import ExperienceLearningViewModel
from orion.ui.widgets.card import Card

__all__ = ["ExperienceLearningPage"]


class ExperienceLearningPage(QWidget):
    """Shows experiences, datasets, training runs, and promotions."""

    def __init__(
        self,
        experience_recorder: ExperienceRecorder | None,
        learning_manager: LearningManager | None,
        view_model: ExperienceLearningViewModel | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ExperienceLearningPage")
        self._vm = view_model or ExperienceLearningViewModel(
            experience_recorder or ExperienceRecorder(), learning_manager or LearningManager()
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Experience & Learning", self)
        title.setProperty("role", "display")
        outer.addWidget(title)

        self._experiences_card = Card(
            "Experiences", "Task episodes recorded by Orion (eligible vs. excluded).", self
        )
        self._experiences_list = QListWidget(self._experiences_card)
        self._experiences_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._experiences_card.add_widget(self._experiences_list)
        outer.addWidget(self._experiences_card)

        self._datasets_card = Card(
            "Datasets", "Immutable versioned Orion Evolution datasets.", self
        )
        self._datasets_list = QListWidget(self._datasets_card)
        self._datasets_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._datasets_card.add_widget(self._datasets_list)
        outer.addWidget(self._datasets_card)

        self._runs_card = Card("Training runs", "Registered training runs and their status.", self)
        self._runs_list = QListWidget(self._runs_card)
        self._runs_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._runs_card.add_widget(self._runs_list)
        outer.addWidget(self._runs_card)

        self._promotions_card = Card(
            "Promotions", "Candidate promotions issued by this Learning Manager.", self
        )
        self._promotions_list = QListWidget(self._promotions_card)
        self._promotions_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._promotions_card.add_widget(self._promotions_list)
        outer.addWidget(self._promotions_card)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        self._refresh_button = QPushButton("Refresh", self)
        self._refresh_button.setObjectName("Secondary")
        self._refresh_button.clicked.connect(self.refresh)
        row.addWidget(self._refresh_button, 0)
        outer.addLayout(row)

        self.refresh()

    def _fill(self, list_widget: QListWidget, rows: list[str]) -> None:
        list_widget.clear()
        for text in rows or []:
            list_widget.addItem(QListWidgetItem(text))

    def refresh(self) -> None:
        experiences = self._vm.experiences()
        rows = []
        for exp in experiences:
            redacted = f"  redacted={','.join(exp.redacted_fields)}" if exp.redacted_fields else ""
            rows.append(
                f"{exp.experience_id[:8]}  outcome={exp.outcome.value}"
                f"  privacy={exp.privacy_state.value}  quality={exp.quality_state.value}"
                f"  excluded={exp.excluded}{redacted}"
                + (f"  task={exp.task_id[:8]}" if exp.task_id else "")
            )
        self._fill(self._experiences_list, rows or ["No experiences yet."])

        datasets = self._vm.datasets()
        rows = [
            f"{ds.dataset_id[:8]}  v{ds.version}"
            f"  train={len(ds.train_ids)}  eval={len(ds.eval_ids)}"
            f"  checksum={ds.checksum[:8]}"
            for ds in datasets
        ]
        self._fill(self._datasets_list, rows or ["No datasets yet."])

        runs = self._vm.runs()
        rows = [
            f"{run.run_id[:8]}  status={run.status.value}"
            f"  dataset={run.dataset_version}"
            f"  metrics={sorted((run.metrics or {}).keys())}"
            for run in runs
        ]
        self._fill(self._runs_list, rows or ["No training runs yet."])

        promotions = self._vm.promotions()
        rows = [
            f"{promo.promotion_id[:8]}"
            f"  candidate={promo.candidate_profile_id}  status={promo.status.value}"
            + (f"  approver={promo.approver}" if promo.approver else "")
            for promo in promotions
        ]
        self._fill(self._promotions_list, rows or ["No promotions yet."])
