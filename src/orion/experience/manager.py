"""Experience recorder for Orion."""

from __future__ import annotations

import threading
from typing import Any

from orion.experience.models import (
    Experience,
    ExperienceAction,
    ExperienceFeedback,
    OutcomeClass,
    PrivacyState,
    QualityState,
)
from orion.experience.store import ExperienceStore


def _scrub_value(value: Any, fields: set[str]) -> Any:
    """Recursively redact matching keys in nested dictionaries and lists."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key in fields else _scrub_value(item, fields)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_scrub_value(item, fields) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(item, fields) for item in value)
    return value


def _scrub_mapping(mapping: dict, fields: list[str]) -> None:
    """Scrub matching keys at every nesting level in-place."""
    scrubbed = _scrub_value(mapping, set(fields))
    mapping.clear()
    mapping.update(scrubbed)


class ExperienceRecorder:
    def __init__(
        self,
        *,
        capture_enabled: bool = True,
        excluded_scopes: set[str] | None = None,
        store: ExperienceStore | None = None,
    ) -> None:
        self.capture_enabled = capture_enabled
        self.excluded_scopes: set[str] = set(excluded_scopes or set())
        # Optional durable backend (e.g. SQLiteExperienceStore). When set, the
        # in-memory dict is bypassed and all operations go through the store.
        self.store = store
        self._experiences: dict[str, Experience] = {}
        self._lock = threading.RLock()
        self.last_error: str | None = None

    def _save(self, exp: Experience) -> None:
        if self.store is not None:
            self.store.save(exp)

    def _discard(self, experience_id: str) -> bool:
        if self.store is not None:
            return self.store.delete(experience_id)
        with self._lock:
            return self._experiences.pop(experience_id, None) is not None

    def pause_capture(self) -> None:
        self.capture_enabled = False

    def resume_capture(self) -> None:
        self.capture_enabled = True

    def exclude_scope(self, scope: str) -> None:
        self.excluded_scopes.add(scope)

    def include_scope(self, scope: str) -> None:
        self.excluded_scopes.discard(scope)

    def capture_experience(
        self,
        *,
        objective_id: str = "",
        task_id: str = "",
        outcome: OutcomeClass | str = OutcomeClass.INCONCLUSIVE,
        actions: list[ExperienceAction] | None = None,
        scope: str = "global",
        metadata: dict[str, Any] | None = None,
    ) -> Experience | None:
        if not self.capture_enabled:
            self.last_error = "capture paused"
            return None
        if scope in self.excluded_scopes:
            self.last_error = f"scope {scope} excluded"
            return None
        try:
            if isinstance(outcome, str):
                outcome = OutcomeClass(outcome)
            exp = Experience(
                objective_id=objective_id,
                task_id=task_id,
                outcome=outcome,
                actions=list(actions or []),
                scope=scope,
                metadata=dict(metadata or {}),
            )
            self._save(exp)
            if self.store is None:
                with self._lock:
                    self._experiences[exp.experience_id] = exp
            self.last_error = None
            return exp
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def capture_from_task(
        self,
        task: Any,
        observations: list[Any] | None = None,
        outcome: OutcomeClass | str | None = None,
    ) -> Experience | None:
        try:
            if outcome is None:
                state = getattr(task, "state", None)
                if state is not None and getattr(state, "value", state) == "completed":
                    outcome = OutcomeClass.SUCCESS
                elif state is not None and getattr(state, "value", state) == "partial":
                    outcome = OutcomeClass.PARTIAL
                elif state is not None and getattr(state, "value", state) == "failed":
                    outcome = OutcomeClass.FAILURE
                elif state is not None and getattr(state, "value", state) == "cancelled":
                    outcome = OutcomeClass.ABANDONED
                else:
                    outcome = OutcomeClass.INCONCLUSIVE
            actions = []
            for step in getattr(task, "steps", []) or []:
                actions.append(
                    ExperienceAction(
                        capability_id=getattr(step, "capability_id", ""),
                        capability_version=getattr(step, "capability_version", "1"),
                        input=dict(getattr(step, "input", {}) or {}),
                        attempted_at=getattr(step, "started_at", None) or "",
                        observed_result=getattr(step, "output", None),
                        verified_outcome=getattr(step, "outcome", ""),
                        permission_decision=getattr(step, "permission_decision", ""),
                    )
                )
            return self.capture_experience(
                objective_id=getattr(task, "objective_id", ""),
                task_id=getattr(task, "task_id", ""),
                outcome=outcome,
                actions=actions,
                scope=getattr(task, "scope", "global"),
            )
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def get(self, experience_id: str) -> Experience | None:
        if self.store is not None:
            return self.store.get(experience_id)
        with self._lock:
            return self._experiences.get(experience_id)

    def list_experiences(self) -> list[Experience]:
        if self.store is not None:
            return self.store.list()
        with self._lock:
            return list(self._experiences.values())

    def add_feedback(
        self,
        experience_id: str,
        content: str,
        feedback_type: str = "correction",
        author: str = "user",
    ) -> ExperienceFeedback:
        exp = self.get(experience_id)
        if exp is None:
            raise KeyError(f"experience not found: {experience_id}")
        fb = ExperienceFeedback(content=content, feedback_type=feedback_type, author=author)
        with self._lock:
            exp.feedback.append(fb)
            # A correction does not change original outcome, but marks corrected if requested.
        self._save(exp)
        return fb

    def mark_corrected(self, experience_id: str) -> Experience:
        exp = self.get(experience_id)
        if exp is None:
            raise KeyError(f"experience not found: {experience_id}")
        exp.outcome = OutcomeClass.CORRECTED
        self._save(exp)
        return exp

    def review_privacy(self, experience_id: str, state: PrivacyState | str) -> Experience:
        exp = self.get(experience_id)
        if exp is None:
            raise KeyError(f"experience not found: {experience_id}")
        if isinstance(state, str):
            state = PrivacyState(state)
        exp.privacy_state = state
        exp.eligible_for_training = (
            exp.privacy_state in (PrivacyState.APPROVED, PrivacyState.REDACTED)
            and exp.quality_state is QualityState.APPROVED
            and not exp.excluded
        )
        self._save(exp)
        return exp

    def review_quality(self, experience_id: str, state: QualityState | str) -> Experience:
        exp = self.get(experience_id)
        if exp is None:
            raise KeyError(f"experience not found: {experience_id}")
        if isinstance(state, str):
            state = QualityState(state)
        exp.quality_state = state
        exp.eligible_for_training = (
            exp.privacy_state in (PrivacyState.APPROVED, PrivacyState.REDACTED)
            and exp.quality_state is QualityState.APPROVED
            and not exp.excluded
        )
        self._save(exp)
        return exp

    def exclude(self, experience_id: str) -> Experience:
        exp = self.get(experience_id)
        if exp is None:
            raise KeyError(f"experience not found: {experience_id}")
        exp.excluded = True
        exp.eligible_for_training = False
        self._save(exp)
        return exp

    def delete(self, experience_id: str) -> bool:
        return self._discard(experience_id)

    def redact(self, experience_id: str, fields: list[str]) -> Experience:
        exp = self.get(experience_id)
        if exp is None:
            raise KeyError(f"experience not found: {experience_id}")
        exp.redacted_fields = list(fields)
        exp.privacy_state = PrivacyState.REDACTED
        # Apply the redaction to the stored data, not only to the marker: the
        # dataset builder and any export must never see the original values.
        _scrub_mapping(exp.metadata, exp.redacted_fields)
        for action in exp.actions:
            _scrub_mapping(action.input, exp.redacted_fields)
            action.observed_result = _scrub_value(action.observed_result, set(exp.redacted_fields))
            if "observed_result" in exp.redacted_fields or "actions" in exp.redacted_fields:
                action.observed_result = "[REDACTED]"
        # Feedback is a separate nested collection, not part of metadata.
        # Scrub its content and any future nested values using the same schema.
        if "feedback" in exp.redacted_fields:
            exp.feedback = []
        else:
            for feedback in exp.feedback:
                if "content" in exp.redacted_fields:
                    feedback.content = "[REDACTED]"
        exp.eligible_for_training = exp.quality_state is QualityState.APPROVED and not exp.excluded
        self._save(exp)
        return exp

    def export(self, *, redact: bool = True) -> list[dict[str, Any]]:
        return [exp.as_dict(redact=redact) for exp in self.list_experiences() if not exp.excluded]
