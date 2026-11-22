"""Tests for experience recorder."""

from __future__ import annotations

from orion.experience import (
    ExperienceRecorder,
    OutcomeClass,
    PrivacyState,
    QualityState,
)


def test_task_episode_traceable() -> None:
    from orion.agent import ResidentAgent
    from orion.capabilities import CapabilityRegistry, register_mock_capabilities
    from orion.capabilities.executor import CapabilityExecutor
    from orion.capabilities.permissions import MockPermissionGateway
    from orion.tasks import InMemoryTaskRepository, TaskManager

    reg = CapabilityRegistry()
    register_mock_capabilities(reg)
    executor = CapabilityExecutor(reg, MockPermissionGateway())
    agent = ResidentAgent(
        registry=reg,
        executor=executor,
        task_manager=TaskManager(repository=InMemoryTaskRepository()),
    )
    task = agent.submit_and_create_task("echo hello")
    agent.run_task(task.task_id)
    recorder = ExperienceRecorder()
    exp = recorder.capture_from_task(agent.task_manager.get_task(task.task_id))
    assert exp is not None
    assert exp.task_id == task.task_id
    assert len(exp.actions) >= 1


def test_failed_attempt_stays_failure_after_correction() -> None:
    recorder = ExperienceRecorder()
    exp = recorder.capture_experience(
        objective_id="o",
        task_id="t",
        outcome=OutcomeClass.FAILURE,
        actions=[],
    )
    assert exp.outcome is OutcomeClass.FAILURE
    recorder.add_feedback(exp.experience_id, "corrected approach")
    recorder.mark_corrected(exp.experience_id)
    assert exp.outcome is OutcomeClass.CORRECTED
    # Original failure preserved in feedback, not overwritten silently
    assert len(exp.feedback) == 1


def test_capture_pause_exclusion() -> None:
    recorder = ExperienceRecorder()
    recorder.pause_capture()
    assert recorder.capture_experience(objective_id="o", task_id="t") is None
    recorder.resume_capture()
    recorder.exclude_scope("secret")
    assert recorder.capture_experience(objective_id="o", task_id="t", scope="secret") is None


def test_redaction_removes_sensitive_fields_from_export() -> None:
    recorder = ExperienceRecorder()
    exp = recorder.capture_experience(
        objective_id="o",
        task_id="t",
        outcome=OutcomeClass.SUCCESS,
        actions=[],
        metadata={"token": "secret"},
    )
    recorder.redact(exp.experience_id, ["token"])
    exported = recorder.export(redact=True)
    assert (
        exported[0]["metadata"].get("token") != "secret" or "token" not in exported[0]["metadata"]
    )


def test_redact_scrubs_stored_data() -> None:
    recorder = ExperienceRecorder()
    exp = recorder.capture_experience(
        objective_id="o",
        task_id="t",
        outcome=OutcomeClass.SUCCESS,
        metadata={"request": "secret-request", "summary": "secret-summary"},
    )
    recorder.redact(exp.experience_id, ["request", "summary"])
    stored = recorder.get(exp.experience_id)
    assert stored is not None
    assert stored.metadata["request"] != "secret-request"
    assert stored.metadata["summary"] != "secret-summary"
    exported = recorder.export(redact=True)
    assert exported[0]["metadata"]["request"] != "secret-request"


def test_eligibility_requires_review() -> None:
    recorder = ExperienceRecorder()
    exp = recorder.capture_experience(objective_id="o", task_id="t", outcome=OutcomeClass.SUCCESS)
    assert exp.eligible_for_training is False
    recorder.review_privacy(exp.experience_id, PrivacyState.APPROVED)
    recorder.review_quality(exp.experience_id, QualityState.APPROVED)
    assert exp.eligible_for_training is True
    recorder.exclude(exp.experience_id)
    assert exp.eligible_for_training is False


def test_sqlite_experience_store_roundtrip(tmp_path) -> None:
    from orion.experience import SQLiteExperienceStore

    store = SQLiteExperienceStore(tmp_path / "exp.db")
    recorder = ExperienceRecorder(store=store)
    exp = recorder.capture_experience(
        objective_id="o",
        task_id="t",
        outcome=OutcomeClass.SUCCESS,
        metadata={"request": "req-1"},
    )
    assert recorder.get(exp.experience_id) is not None

    # A fresh recorder over the same database file sees the experience:
    # experiences survive restart.
    recorder2 = ExperienceRecorder(store=SQLiteExperienceStore(tmp_path / "exp.db"))
    got = recorder2.get(exp.experience_id)
    assert got is not None
    assert got.metadata["request"] == "req-1"
    assert got.outcome is OutcomeClass.SUCCESS


def test_sqlite_experience_store_delete(tmp_path) -> None:
    from orion.experience import SQLiteExperienceStore

    recorder = ExperienceRecorder(store=SQLiteExperienceStore(tmp_path / "exp.db"))
    exp = recorder.capture_experience(objective_id="o", task_id="t", outcome=OutcomeClass.SUCCESS)
    assert recorder.delete(exp.experience_id) is True
    assert recorder.get(exp.experience_id) is None


def test_capture_failure_non_fatal() -> None:
    recorder = ExperienceRecorder()
    # Force failure by passing bad outcome
    result = recorder.capture_experience(
        objective_id="o", task_id="t", outcome="not_a_real_outcome"
    )
    assert result is None
    assert recorder.last_error is not None

def test_redaction_scrubs_nested_feedback_and_export() -> None:
    recorder = ExperienceRecorder()
    exp = recorder.capture_experience(
        objective_id="o",
        task_id="t",
        outcome=OutcomeClass.SUCCESS,
        metadata={"nested": {"token": "nested-secret"}},
    )
    recorder.add_feedback(exp.experience_id, "feedback-secret")
    recorder.redact(exp.experience_id, ["token", "content"])
    stored = recorder.get(exp.experience_id)
    assert stored is not None
    assert stored.metadata["nested"]["token"] == "[REDACTED]"
    assert stored.feedback[0].content == "[REDACTED]"
    exported = recorder.export(redact=True)[0]
    assert exported["feedback"][0]["content"] == "[REDACTED]"
    assert "feedback-secret" not in str(exported)
