"""Task repositories."""

from __future__ import annotations

import copy
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from orion.tasks.models import Task

SCHEMA_VERSION = 1

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    task_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
"""


class TaskRepository:
    def save(self, task: Task) -> None: ...
    def get(self, task_id: str) -> Task: ...
    def list(self) -> list[Task]: ...
    def delete(self, task_id: str) -> None: ...


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def save(self, task: Task) -> None:
        self._tasks[task.task_id] = copy.deepcopy(task)

    def get(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise KeyError(f"task not found: {task_id}")
        return copy.deepcopy(self._tasks[task_id])

    def list(self) -> list[Task]:
        return [copy.deepcopy(task) for task in self._tasks.values()]

    def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    def clear(self) -> None:
        self._tasks.clear()


class SQLiteTaskRepository:
    """Durable task repository backed by SQLite.

    Task history survives process restarts; a new instance over the same
    database file sees previously saved tasks.
    """

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

    def save(self, task: Task) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO tasks"
                    " (task_id, task_json, created_at) VALUES (?, ?, ?)",
                    (task.task_id, json.dumps(task.as_dict()), task.created_at),
                )
                conn.commit()
            finally:
                conn.close()

    def get(self, task_id: str) -> Task:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT task_json FROM tasks WHERE task_id = ?", (task_id,)
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            raise KeyError(f"task not found: {task_id}")
        return Task.from_dict(json.loads(row["task_json"]))

    def list(self) -> list[Task]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT task_json FROM tasks ORDER BY created_at, task_id"
                ).fetchall()
            finally:
                conn.close()
        return [Task.from_dict(json.loads(row["task_json"])) for row in rows]

    def delete(self, task_id: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                conn.commit()
            finally:
                conn.close()
