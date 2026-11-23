"""Dataset builder for Orion Evolution."""

from __future__ import annotations

import hashlib
import random

from orion.experience.models import Experience, OutcomeClass, PrivacyState
from orion.learning.models import DatasetExample, DatasetVersion

BUILDER_VERSION = "1.0"


def _split_ids(
    examples: list[DatasetExample], fraction: float, seed_source: str
) -> tuple[list[str], list[str]]:
    """Split example IDs into (eval_ids, train_ids) reproducibly.

    The split is a pure function of ``seed_source`` (dataset version +
    eligible source experiences) and the examples list: the same dataset
    content always yields the same split, and eval/train are disjoint.
    """
    seed = int.from_bytes(hashlib.sha256(seed_source.encode("utf-8")).digest()[:8], "big")
    order = list(range(len(examples)))
    random.Random(seed).shuffle(order)
    eval_count = max(1, int(len(order) * fraction)) if order else 0
    eval_ids = [examples[i].example_id for i in order[:eval_count]]
    train_ids = [examples[i].example_id for i in order[eval_count:]]
    return eval_ids, train_ids


def _redacted(exp: Experience, key: str) -> bool:
    """Hide fields named directly or through their serialized metadata path."""
    fields = set(exp.redacted_fields)
    return (
        key in fields
        or f"metadata.{key}" in fields
        or "metadata" in fields
        or exp.privacy_state is PrivacyState.REDACTED
    )


def _scrub(exp: Experience, value: str, key: str) -> str:
    return "[REDACTED]" if _redacted(exp, key) else value


def _example_from_experience(exp: Experience) -> DatasetExample:
    # Build a simple conversational example. Redacted fields never enter the
    # dataset in original form; the builder re-applies redaction as a second
    # layer of defence (defense in depth).
    input_payload = {
        "objective": _scrub(exp, exp.metadata.get("request", ""), "request"),
        "actions": [
            "[REDACTED]"
            if {"actions", "actions.capability_id", "capability_id"} & set(exp.redacted_fields)
            else a.capability_id
            for a in exp.actions
        ],
    }
    output_payload = {
        "outcome": _scrub(exp, exp.outcome.value, "outcome"),
        "summary": _scrub(exp, exp.metadata.get("summary", ""), "summary"),
    }
    return DatasetExample(
        source_experience_id=exp.experience_id,
        input=input_payload,
        output=output_payload,
        metadata={
            "privacy_state": exp.privacy_state.value,
            "quality_state": exp.quality_state.value,
        },
    )


def build_dataset(
    experiences: list[Experience],
    *,
    version: str = "1",
    split_eval_fraction: float = 0.1,
) -> DatasetVersion:
    # Eligibility: privacy approved/redacted, quality approved, not excluded, not secret?
    eligible = [
        e
        for e in experiences
        if e.privacy_state.value in ("approved", "redacted")
        and e.quality_state.value == "approved"
        and not e.excluded
        and e.outcome in (OutcomeClass.SUCCESS, OutcomeClass.CORRECTED, OutcomeClass.PARTIAL)
    ]
    examples = [_example_from_experience(e) for e in eligible]
    dataset = DatasetVersion(
        version=version,
        builder_version=BUILDER_VERSION,
        examples=examples,
        source_experience_ids=[e.experience_id for e in eligible],
        review_approvals=[],
        exclusions=[e.experience_id for e in experiences if e not in eligible],
        split_strategy=f"held_out_{int(split_eval_fraction * 100)}",
    )
    # Reproducible split: shuffled with a seed derived from the dataset
    # content (version + eligible source experiences), never "first N".
    seed_source = (
        f"{version}|{len(examples)}|{','.join(sorted({e.source_experience_id for e in examples}))}"
    )
    dataset.eval_ids, dataset.train_ids = _split_ids(examples, split_eval_fraction, seed_source)
    dataset.checksum = dataset.compute_checksum()
    return dataset
