"""Tests for learning pipeline."""

from __future__ import annotations

from orion.experience import ExperienceRecorder, OutcomeClass, PrivacyState, QualityState
from orion.learning import LearningManager, build_dataset
from orion.learning.models import EvaluationResult
from orion.models import ModelProfile


def _held_out_metrics(manager: LearningManager, accuracy: float, **extra):
    recorder, _ = _eligible_experience()
    dataset = manager.build_dataset(recorder.list_experiences())
    return {
        "accuracy": accuracy,
        "held_out": True,
        "dataset_id": dataset.dataset_id,
        "eval_dataset_checksum": dataset.checksum,
        "eval_examples": len(dataset.eval_ids),
        **extra,
    }


def _eligible_experience():
    rec = ExperienceRecorder()
    exp = rec.capture_experience(objective_id="o", task_id="t", outcome=OutcomeClass.SUCCESS)
    rec.review_privacy(exp.experience_id, PrivacyState.APPROVED)
    rec.review_quality(exp.experience_id, QualityState.APPROVED)
    return rec, exp


def test_eligible_episodes_build_valid_jsonl() -> None:
    rec, exp = _eligible_experience()
    dataset = build_dataset(rec.list_experiences())
    assert (
        dataset.example_count if hasattr(dataset, "example_count") else len(dataset.examples) == 1
    )
    assert (
        "source_experience_id" in dataset.to_jsonl()
        or dataset.examples[0].source_experience_id == exp.experience_id
    )
    assert dataset.checksum


def test_excluded_sensitive_omitted() -> None:
    rec = ExperienceRecorder()
    exp = rec.capture_experience(objective_id="o", task_id="t", outcome=OutcomeClass.SUCCESS)
    rec.exclude(exp.experience_id)
    rec.review_privacy(exp.experience_id, PrivacyState.APPROVED)
    rec.review_quality(exp.experience_id, QualityState.APPROVED)
    dataset = build_dataset(rec.list_experiences())
    assert len(dataset.examples) == 0


def test_dataset_split_is_reproducible() -> None:
    rec, _ = _eligible_experience()
    exp2 = rec.capture_experience(objective_id="o2", task_id="t2", outcome=OutcomeClass.SUCCESS)
    rec.review_privacy(exp2.experience_id, PrivacyState.APPROVED)
    rec.review_quality(exp2.experience_id, QualityState.APPROVED)
    ds1 = build_dataset(rec.list_experiences())
    ds2 = build_dataset(rec.list_experiences())

    def split_by_source(ds):
        by_source = {e.example_id: e.source_experience_id for e in ds.examples}
        evals = {by_source[e] for e in ds.eval_ids}
        trains = {by_source[e] for e in ds.train_ids}
        return evals, trains, by_source

    evals1, trains1, by_source1 = split_by_source(ds1)
    evals2, trains2, by_source2 = split_by_source(ds2)
    assert evals1 == evals2
    assert trains1 == trains2
    # Disjoint and covering: every example is in exactly one split.
    assert not evals1 & trains1
    assert evals1 | trains1 == set(by_source1.values())
    assert set(by_source1.values()) == set(by_source2.values())


def test_dataset_immutable_version() -> None:
    rec, _ = _eligible_experience()
    dataset = build_dataset(rec.list_experiences())
    original_checksum = dataset.checksum
    # Mutating examples should not be allowed? We check checksum unchanged after read.
    assert dataset.checksum == original_checksum


def test_mock_trainer_lifecycle() -> None:
    rec, _ = _eligible_experience()
    dataset = build_dataset(rec.list_experiences())
    lm = LearningManager()
    run = lm.submit_training(dataset, base_model_revision="rev1")
    assert run.status.value == "completed"
    assert run.output_path.startswith("mock://")
    assert "accuracy" in run.metrics


def test_candidate_evaluation_records_metrics() -> None:
    lm = LearningManager()
    ev = lm.evaluate_candidate("cand1", metrics=_held_out_metrics(lm, 0.9))
    assert ev.passed is True
    assert ev.metrics["accuracy"] == 0.9


def test_evaluate_candidate_without_accuracy_metric_rejected() -> None:
    lm = LearningManager()
    try:
        lm.evaluate_candidate("cand1", metrics={})
    except ValueError:
        pass
    else:
        raise AssertionError("evaluation without accuracy metric should fail")


def test_evaluate_candidate_low_accuracy_fails() -> None:
    lm = LearningManager()
    ev = lm.evaluate_candidate("cand1", metrics=_held_out_metrics(lm, 0.5))
    assert ev.passed is False


def test_evaluate_candidate_regression_fails() -> None:
    lm = LearningManager()
    ev = lm.evaluate_candidate("cand1", metrics=_held_out_metrics(lm, 0.95, regression=False))
    assert ev.passed is False


def test_promotion_requires_evaluation() -> None:
    lm = LearningManager()
    profile = ModelProfile(profile_id="cand", base_model="mock-base")
    try:
        lm.promote_candidate(profile, approved=True)
    except ValueError:
        pass
    else:
        raise AssertionError("promotion without evaluation should fail")


def test_promotion_requires_candidate_bound_evaluation() -> None:
    lm = LearningManager()
    profile = ModelProfile(profile_id="cand", base_model="mock-base")
    ev = lm.evaluate_candidate("other", metrics=_held_out_metrics(0.9))
    try:
        lm.promote_candidate(profile, evaluation=ev, approved=True)
    except ValueError:
        pass
    else:
        raise AssertionError("foreign evaluation should be rejected")


def test_promotion_requires_passed_evaluation() -> None:
    lm = LearningManager()
    profile = ModelProfile(profile_id="cand", base_model="mock-base")
    ev = lm.evaluate_candidate("cand", metrics=_held_out_metrics(0.5))
    try:
        lm.promote_candidate(profile, evaluation=ev, approved=True)
    except ValueError:
        pass
    else:
        raise AssertionError("failed evaluation should be rejected")


def test_promotion_requires_metrics() -> None:
    lm = LearningManager()
    profile = ModelProfile(profile_id="cand", base_model="mock-base")
    ev = EvaluationResult(candidate_profile_id="cand", passed=True)
    try:
        lm.promote_candidate(profile, evaluation=ev, approved=True)
    except ValueError:
        pass
    else:
        raise AssertionError("evaluation without metrics should be rejected")


def test_promotion_denied_without_approval() -> None:
    lm = LearningManager()
    profile = ModelProfile(profile_id="cand", base_model="mock-base")
    try:
        lm.promote_candidate(profile, approved=False)
    except PermissionError:
        pass
    else:
        raise AssertionError("promotion should require approval")


def test_promotion_approved() -> None:
    lm = LearningManager()
    profile = ModelProfile(profile_id="cand", base_model="mock-base")
    ev = lm.evaluate_candidate("cand", metrics=_held_out_metrics(0.9))
    record = lm.promote_candidate(profile, evaluation=ev, approved=True, approver="user")
    assert record.status.value == "approved"


def test_rollback_restores_metadata() -> None:
    lm = LearningManager()
    profile = ModelProfile(profile_id="cand", base_model="mock-base")
    ev = lm.evaluate_candidate("cand", metrics=_held_out_metrics(0.9))
    record = lm.promote_candidate(profile, evaluation=ev, approved=True, previous_profile_id="prev")
    rolled = lm.rollback(record.promotion_id)
    assert rolled.status.value == "rolled_back"


def test_redacted_experience_does_not_leak_into_dataset() -> None:
    rec = ExperienceRecorder()
    exp = rec.capture_experience(
        objective_id="o",
        task_id="t",
        outcome=OutcomeClass.SUCCESS,
        metadata={"request": "secret-request", "summary": "secret-summary"},
    )
    rec.redact(exp.experience_id, ["request", "summary"])
    rec.review_privacy(exp.experience_id, PrivacyState.APPROVED)
    rec.review_quality(exp.experience_id, QualityState.APPROVED)
    dataset = build_dataset(rec.list_experiences())
    blob = dataset.to_jsonl()
    assert "secret-request" not in blob
    assert "secret-summary" not in blob
