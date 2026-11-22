"""Tests for the SQLite-backed task repository."""

from __future__ import annotations

from pathlib import Path

from orion.tasks import SQLiteTaskRepository, TaskManager
from orion.tasks.models import TaskState


def test_sqlite_repository_roundtrip(tmp_path: Path) -> None:
    repo = SQLiteTaskRepository(tmp_path / "tasks.db")
    tm = TaskManager(repository=repo)
    obj = tm.create_objective("obj")
    task = tm.create_task(obj, title="t")
    got = repo.get(task.task_id)
    assert got.task_id == task.task_id
    assert got.title == "t"
    assert got.state is TaskState.CREATED


def test_sqlite_repository_survives_restart(tmp_path: Path) -> None:
    db = tmp_path / "tasks.db"
    tm = TaskManager(repository=SQLiteTaskRepository(db))
    obj = tm.create_objective("obj")
    task = tm.create_task(obj, title="t")

    tm2 = TaskManager(repository=SQLiteTaskRepository(db))
    ids = {t.task_id for t in tm2.list_tasks()}
    assert task.task_id in ids
    assert tm2.get_task(task.task_id).title == "t"


def test_sqlite_repository_delete(tmp_path: Path) -> None:
    repo = SQLiteTaskRepository(tmp_path / "tasks.db")
    tm = TaskManager(repository=repo)
    task = tm.create_task(tm.create_objective("obj"), title="t")
    repo.delete(task.task_id)
    assert tm.list_tasks() == []
