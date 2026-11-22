"""Durable SQLite store for experiences.

The :class:`ExperienceRecorder` keeps an in-memory mirror by default;
instances that pass a store (e.g. :class:`SQLiteExperienceStore`) are
durable: experiences survive process restarts.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Protocol

from orion.experience.models import (
    Experience,
    ExperienceAction,
    ExperienceFeedback,
    OutcomeClass,
    PrivacyState,
    QualityState,
)

SCHEMA_VERSION = 1

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS experiences (
    experience_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


class ExperienceStore(Protocol):
    """Contract implemented by the recorder's experience backend."""

    def save(self, exp: Experience) -> None: ...
    def get(self, experience_id: str) -> Experience | None: ...
    def list(self) -> list[Experience]: ...
    def delete(self, experience_id: str) -> bool: ...


def _experience_from_dict(data: dict[str, Any]) -> Experience:
    actions = [
        ExperienceAction(
            action_id=a["action_id"],
            capability_id=a.get("capability_id", ""),
            capability_version=a.get("capability_version", "1"),
            input=dict(a.get("input", {}) or {}),
            attempted_at=a.get("attempted_at", ""),
            observed_result=a.get("observed_result"),
            verified_outcome=a.get("verified_outcome", ""),
            permission_decision=a.get("permission_decision", ""),
        )
        for a in data.get("actions", [])
    ]
    feedback = [
        ExperienceFeedback(
            feedback_id=f["feedback_id"],
            feedback_type=f.get("feedback_type", "correction"),
            content=f.get("content", ""),
            created_at=f.get("created_at", ""),
            author=f.get("author", "user"),
        )
        for f in data.get("feedback", [])
    ]
    return Experience(
        experience_id=data["experience_id"],
        objective_id=data.get("objective_id", ""),
        task_id=data.get("task_id", ""),
        outcome=OutcomeClass(data.get("outcome", "inconclusive")),
        created_at=data.get("created_at", ""),
        actions=actions,
        feedback=feedback,
        privacy_state=PrivacyState(data.get("privacy_state", "pending")),
        quality_state=QualityState(data.get("quality_state", "pending")),
        eligible_for_training=data.get("eligible_for_training", False),
        excluded=data.get("excluded", False),
        redacted_fields=list(data.get("redacted_fields", [])),
        scope=data.get("scope", "global"),
        metadata=dict(data.get("metadata", {}) or {}),
    )


class SQLiteExperienceStore:
    """Durable SQLite backend implementing :class:`ExperienceStore`."""

    def __init__(self, db_path: Any) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _migrate(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.cursor()
                cur.executescript(_CREATE_TABLES)
                cur.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
                conn.commit()
            finally:
                conn.close()

    def save(self, exp: Experience) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO experiences (experience_id, created_at, payload)"
                    " VALUES (?, ?, ?)",
                    (exp.experience_id, exp.created_at, json.dumps(exp.as_dict())),
                )
                conn.commit()
            finally:
                conn.close()

    def get(self, experience_id: str) -> Experience | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT payload FROM experiences WHERE experience_id = ?",
                    (experience_id,),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        return _experience_from_dict(json.loads(row["payload"]))

    def list(self) -> list[Experience]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT payload FROM experiences ORDER BY created_at, experience_id"
                ).fetchall()
            finally:
                conn.close()
        return [_experience_from_dict(json.loads(row["payload"])) for row in rows]

    def delete(self, experience_id: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "DELETE FROM experiences WHERE experience_id = ?", (experience_id,)
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()
