"""Memory manager for Orion."""

from __future__ import annotations

import re
import threading
from typing import Any

from orion.memory.models import MemoryCategory, MemoryRecord, MemorySensitivity, MemoryState
from orion.memory.store import MemoryStore

SECRET_PATTERNS = [
    re.compile(r"password\s*[:=]", re.I),
    re.compile(r"api[_-]?key\s*[:=]", re.I),
    re.compile(r"bearer\s+[a-z0-9._-]+", re.I),
    re.compile(r"sk-[a-z0-9]{10,}", re.I),
    re.compile(r"token\s*[:=]\s*\S{8,}", re.I),
]


class SensitiveContentError(ValueError):
    """Raised when memory content appears to contain secrets."""


class MemoryManager:
    def __init__(
        self,
        store: MemoryStore,
        *,
        capture_enabled: bool = True,
        excluded_scopes: set[str] | None = None,
    ) -> None:
        self.store = store
        self.capture_enabled = capture_enabled
        self.excluded_scopes: set[str] = set(excluded_scopes or set())
        self._lock = threading.RLock()

    def _check_sensitive(self, content: str) -> None:
        for pat in SECRET_PATTERNS:
            if pat.search(content):
                raise SensitiveContentError("content appears to contain a secret")

    def create_memory(
        self,
        content: str,
        *,
        category: MemoryCategory | str = MemoryCategory.FACT,
        provenance: str = "",
        source: str = "",
        scope: str = "global",
        project_id: str | None = None,
        confidence: float = 1.0,
        sensitivity: MemorySensitivity | str = MemorySensitivity.NORMAL,
        valid_until: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        if scope in self.excluded_scopes:
            raise ValueError(f"scope {scope!r} is excluded")
        if not self.capture_enabled:
            raise RuntimeError("memory capture is paused")
        self._check_sensitive(content)
        if isinstance(category, str):
            category = MemoryCategory(category)
        if isinstance(sensitivity, str):
            sensitivity = MemorySensitivity(sensitivity)
        record = MemoryRecord(
            category=category,
            content=content,
            provenance=provenance,
            source=source,
            scope=scope,
            project_id=project_id,
            confidence=confidence,
            sensitivity=sensitivity,
            valid_until=valid_until,
            metadata=dict(metadata or {}),
        )
        self.store.save(record)
        return record

    def get(self, memory_id: str) -> MemoryRecord | None:
        return self.store.get(memory_id)

    def update(self, memory_id: str, **changes: Any) -> MemoryRecord:
        record = self.store.get(memory_id)
        if record is None:
            raise KeyError(f"memory not found: {memory_id}")
        if record.state is MemoryState.DELETED:
            raise ValueError("cannot update deleted memory")
        if "content" in changes:
            self._check_sensitive(str(changes["content"]))
        for key, value in changes.items():
            if hasattr(record, key):
                setattr(record, key, value)
        if "category" in changes and isinstance(changes["category"], str):
            record.category = MemoryCategory(changes["category"])
        if "sensitivity" in changes and isinstance(changes["sensitivity"], str):
            record.sensitivity = MemorySensitivity(changes["sensitivity"])
        import datetime as _dt

        record.verified_at = _dt.datetime.now(_dt.UTC).isoformat()
        self.store.save(record)
        return record

    def delete(self, memory_id: str, *, hard: bool = False) -> bool:
        return self.store.delete(memory_id, hard=hard)

    def supersede(self, old_id: str, new_record: MemoryRecord) -> MemoryRecord:
        old = self.store.get(old_id)
        if old is None:
            raise KeyError(f"memory not found: {old_id}")
        old.state = MemoryState.SUPERSEDED
        old.superseded_by = new_record.memory_id
        self.store.save(old)
        self.store.save(new_record)
        return new_record

    def search(self, query: str = "", **kwargs: Any) -> list[MemoryRecord]:
        # Honour exclusions.
        results = self.store.search(query, **kwargs)
        return [
            r
            for r in results
            if r.scope not in self.excluded_scopes
            and r.state not in (MemoryState.DELETED, MemoryState.EXCLUDED)
        ]

    def list_all(self, **kwargs: Any) -> list[MemoryRecord]:
        results = self.store.list_all(**kwargs)
        return [r for r in results if r.scope not in self.excluded_scopes]

    def exclude_scope(self, scope: str) -> None:
        self.excluded_scopes.add(scope)

    def include_scope(self, scope: str) -> None:
        self.excluded_scopes.discard(scope)

    def pause_capture(self) -> None:
        self.capture_enabled = False

    def resume_capture(self) -> None:
        self.capture_enabled = True

    def export(self) -> list[dict[str, Any]]:
        return [r.as_dict() for r in self.list_all(include_deleted=True)]

    def backup(self, destination: Any) -> None:
        self.store.backup(destination)

    def restore(self, source: Any) -> None:
        self.store.restore(source)
