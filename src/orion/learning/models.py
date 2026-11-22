"""Learning pipeline domain models for Orion Evolution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TrainingStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PromotionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class DatasetExample:
    example_id: str = field(default_factory=lambda: str(uuid4()))
    source_experience_id: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "source_experience_id": self.source_experience_id,
            "input": dict(self.input),
            "output": dict(self.output),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class DatasetVersion:
    dataset_id: str = field(default_factory=lambda: str(uuid4()))
    version: str = "1"
    builder_version: str = "1.0"
    format: str = "jsonl"
    schema: str = "orion.conversational.v1"
    examples: list[DatasetExample] = field(default_factory=list)
    source_experience_ids: list[str] = field(default_factory=list)
    review_approvals: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    split_strategy: str = "held_out_10"
    train_ids: list[str] = field(default_factory=list)
    eval_ids: list[str] = field(default_factory=list)
    checksum: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    immutable: bool = True

    def compute_checksum(self) -> str:
        payload = json.dumps([e.as_dict() for e in self.examples], sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def as_manifest(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "builder_version": self.builder_version,
            "format": self.format,
            "schema": self.schema,
            "example_count": len(self.examples),
            "source_experience_ids": list(self.source_experience_ids),
            "review_approvals": list(self.review_approvals),
            "exclusions": list(self.exclusions),
            "split_strategy": self.split_strategy,
            "train_count": len(self.train_ids),
            "eval_count": len(self.eval_ids),
            "checksum": self.checksum,
            "created_at": self.created_at,
            "immutable": self.immutable,
        }

    def to_jsonl(self) -> str:
        lines = []
        for ex in self.examples:
            lines.append(
                json.dumps(
                    {
                        "input": ex.input,
                        "output": ex.output,
                        "source_experience_id": ex.source_experience_id,
                    }
                )
            )
        return "\n".join(lines)


@dataclass(slots=True)
class TrainingRun:
    run_id: str = field(default_factory=lambda: str(uuid4()))
    dataset_id: str = ""
    dataset_version: str = ""
    base_model_revision: str = ""
    trainer_version: str = "mock-trainer-1.0"
    config: dict[str, Any] = field(default_factory=dict)
    status: TrainingStatus = TrainingStatus.QUEUED
    output_path: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "base_model_revision": self.base_model_revision,
            "trainer_version": self.trainer_version,
            "config": dict(self.config),
            "status": self.status.value,
            "output_path": self.output_path,
            "metrics": dict(self.metrics),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


@dataclass(slots=True)
class EvaluationResult:
    evaluation_id: str = field(default_factory=lambda: str(uuid4()))
    candidate_profile_id: str = ""
    baseline_profile_id: str = ""
    benchmark_version: str = "1.0"
    metrics: dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    details: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "candidate_profile_id": self.candidate_profile_id,
            "baseline_profile_id": self.baseline_profile_id,
            "benchmark_version": self.benchmark_version,
            "metrics": dict(self.metrics),
            "passed": self.passed,
            "details": self.details,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class PromotionRecord:
    promotion_id: str = field(default_factory=lambda: str(uuid4()))
    candidate_profile_id: str = ""
    previous_profile_id: str | None = None
    status: PromotionStatus = PromotionStatus.PENDING
    approver: str | None = None
    approved_at: str | None = None
    rollback_profile_id: str | None = None
    details: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "candidate_profile_id": self.candidate_profile_id,
            "previous_profile_id": self.previous_profile_id,
            "status": self.status.value,
            "approver": self.approver,
            "approved_at": self.approved_at,
            "rollback_profile_id": self.rollback_profile_id,
            "details": self.details,
        }
