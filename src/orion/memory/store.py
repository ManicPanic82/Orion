"""SQLite-backed memory store with migrations."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from orion.memory.models import MemoryCategory, MemoryRecord, MemorySensitivity, MemoryState

SCHEMA_VERSION = 1

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    scope TEXT NOT NULL DEFAULT 'global',
    project_id TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    sensitivity TEXT NOT NULL DEFAULT 'normal',
    state TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    verified_at TEXT,
    valid_from TEXT,
    valid_until TEXT,
    superseded_by TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
"""


class MemoryStore:
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
                    "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (SCHEMA_VERSION,)
                )
                conn.commit()
            finally:
                conn.close()

    def close(self) -> None:
        pass

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def save(self, record: MemoryRecord) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO memories
                    (memory_id, category, content, provenance, source, scope,
                     project_id, confidence,
                     sensitivity, state, created_at, verified_at, valid_from, valid_until,
                     superseded_by, metadata)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        record.memory_id,
                        record.category.value,
                        record.content,
                        record.provenance,
                        record.source,
                        record.scope,
                        record.project_id,
                        float(record.confidence),
                        record.sensitivity.value,
                        record.state.value,
                        record.created_at,
                        record.verified_at,
                        record.valid_from,
                        record.valid_until,
                        record.superseded_by,
                        json.dumps(record.metadata),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def get(self, memory_id: str) -> MemoryRecord | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM memories WHERE memory_id=?", (memory_id,)
                ).fetchone()
                return self._row_to_record(row) if row else None
            finally:
                conn.close()

    def delete(self, memory_id: str, *, hard: bool = False) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                if hard:
                    cur = conn.execute("DELETE FROM memories WHERE memory_id=?", (memory_id,))
                else:
                    cur = conn.execute(
                        "UPDATE memories SET state='deleted' WHERE memory_id=?", (memory_id,)
                    )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def list_all(self, *, include_deleted: bool = False) -> list[MemoryRecord]:
        with self._lock:
            conn = self._connect()
            try:
                if include_deleted:
                    rows = conn.execute("SELECT * FROM memories").fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM memories WHERE state != 'deleted'"
                    ).fetchall()
                return [self._row_to_record(r) for r in rows]
            finally:
                conn.close()

    def search(
        self,
        query: str = "",
        *,
        scope: str | None = None,
        project_id: str | None = None,
        category: str | None = None,
        include_deleted: bool = False,
        include_expired: bool = False,
        include_superseded: bool = False,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        clauses = []
        params: list[Any] = []
        if not include_deleted:
            clauses.append("state != 'deleted'")
        if not include_superseded:
            clauses.append("state != 'superseded'")
        if scope is not None:
            clauses.append("scope = ?")
            params.append(scope)
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if query:
            clauses.append("(content LIKE ? OR provenance LIKE ? OR category LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like, like])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM memories{where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(sql, params).fetchall()
            finally:
                conn.close()
        records = [self._row_to_record(r) for r in rows]
        if not include_expired:
            records = [r for r in records if not r.is_expired()]
        return records

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        import json as _json

        metadata = {}
        try:
            metadata = _json.loads(row["metadata"] or "{}")
        except _json.JSONDecodeError:
            metadata = {}
        return MemoryRecord(
            memory_id=row["memory_id"],
            category=MemoryCategory(row["category"]),
            content=row["content"],
            provenance=row["provenance"],
            source=row["source"],
            scope=row["scope"],
            project_id=row["project_id"],
            confidence=float(row["confidence"]),
            sensitivity=MemorySensitivity(row["sensitivity"]),
            state=MemoryState(row["state"]),
            created_at=row["created_at"],
            verified_at=row["verified_at"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            superseded_by=row["superseded_by"],
            metadata=metadata,
        )

    def backup(self, destination: Any) -> None:
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            src_conn = self._connect()
            dst_conn = sqlite3.connect(str(dest))
            try:
                src_conn.backup(dst_conn)
            finally:
                src_conn.close()
                dst_conn.close()

    def restore(self, source: Any) -> None:
        src = Path(source)
        if not src.exists():
            raise FileNotFoundError(str(src))
        with self._lock:
            import shutil

            shutil.copyfile(src, self.db_path)
