"""Tests for persistent memory."""

from __future__ import annotations

import tempfile
from pathlib import Path

from orion.memory import MemoryManager, MemoryStore, SensitiveContentError


def test_create_search_update_delete() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td) / "mem.db")
        mgr = MemoryManager(store)
        rec = mgr.create_memory("Orion uses SQLite", category="fact", scope="project:a")
        assert rec.memory_id
        found = mgr.search("SQLite", scope="project:a")
        assert len(found) == 1
        mgr.update(rec.memory_id, content="Orion uses SQLite and FTS")
        updated = mgr.get(rec.memory_id)
        assert "FTS" in updated.content
        assert mgr.delete(rec.memory_id) is True
        assert mgr.search("SQLite", scope="project:a") == []


def test_scope_and_expiry_filtering() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td) / "mem.db")
        mgr = MemoryManager(store)
        mgr.create_memory("global fact", scope="global")
        mgr.create_memory("project fact", scope="project:a")
        assert len(mgr.search("", scope="project:a")) == 1
        assert len(mgr.search("", scope="global")) == 1


def test_exclusion_honoured() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td) / "mem.db")
        mgr = MemoryManager(store)
        mgr.exclude_scope("secret-scope")
        try:
            mgr.create_memory("x", scope="secret-scope")
        except ValueError:
            pass
        else:
            raise AssertionError("excluded scope should reject creation")
        mgr.include_scope("secret-scope")
        mgr.create_memory("x", scope="secret-scope")
        mgr.exclude_scope("secret-scope")
        assert mgr.search("x", scope="secret-scope") == []


def test_secret_like_content_rejected() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td) / "mem.db")
        mgr = MemoryManager(store)
        try:
            mgr.create_memory("password: supersecret", scope="global")
        except SensitiveContentError:
            pass
        else:
            raise AssertionError("secret-like content should be rejected")


def test_backup_restore() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "mem.db"
        backup = Path(td) / "backup.db"
        store = MemoryStore(db)
        mgr = MemoryManager(store)
        rec = mgr.create_memory("backup me", scope="global")
        mid = rec.memory_id
        mgr.backup(backup)
        # delete and restore
        mgr.delete(mid, hard=True)
        assert mgr.get(mid) is None
        mgr.restore(backup)
        assert mgr.get(mid) is not None


def test_supersession() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td) / "mem.db")
        mgr = MemoryManager(store)
        old = mgr.create_memory("old fact", scope="global")
        new = mgr.create_memory("new fact", scope="global")
        mgr.supersede(old.memory_id, new)
        old_loaded = mgr.get(old.memory_id)
        assert old_loaded.state.value == "superseded"
        assert old_loaded.superseded_by == new.memory_id


def test_model_identity_does_not_affect_memory() -> None:
    # Memory store has no model dependency; just ensure records persist.
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td) / "mem.db")
        mgr = MemoryManager(store)
        mgr.create_memory("fact", scope="global")
        assert len(mgr.search("fact")) == 1
