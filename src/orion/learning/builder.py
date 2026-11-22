"""Dataset builder for Orion Evolution."""

from __future__ import annotations

from orion.experience.models import Experience, OutcomeClass
from orion.learning.models import DatasetExample, DatasetVersion

BUILDER_VERSION = "1.0"


def _example_from_experience(exp: Experience) -> DatasetExample:
    # Build a simple conversational example.
    input_payload = {
        "objective": exp.metadata.get("request", ""),
        "actions": [a.capability_id for a in exp.actions],
    }
    output_payload = {
        "outcome": exp.outcome.value,
        "summary": exp.metadata.get("summary", ""),
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
    # Split.
    eval_count = max(1, int(len(examples) * split_eval_fraction)) if examples else 0
    dataset.eval_ids = [e.example_id for e in examples[:eval_count]]
    dataset.train_ids = [e.example_id for e in examples[eval_count:]]
    dataset.checksum = dataset.compute_checksum()
    return dataset
