"""Atomic, self-healing persistence for :class:`orion.config.settings.Settings`.

Design rules:

* Writes are atomic (temporary file in the same directory, then ``os.replace``),
  so a crash mid-write cannot truncate live settings.
* A document that cannot be parsed is *quarantined*, never silently overwritten.
* A document written by a newer Orion refuses further writes, so an older build
  cannot destroy settings it does not understand.
* Nothing here creates domain tables. Phase 1 persists UI preferences only.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from orion.config.paths import settings_path
from orion.config.settings import SCHEMA_VERSION, Settings, SettingsError

__all__ = ["LoadResult", "SettingsStore"]

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Outcome of reading the settings document."""

    settings: Settings
    problems: tuple[str, ...] = ()
    quarantined: Path | None = None
    writable: bool = True

    @property
    def is_clean(self) -> bool:
        return not self.problems and self.quarantined is None


class SettingsStore:
    """Reads and writes the versioned settings document."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else settings_path()
        self._refuse_write_reason: str | None = None

    @property
    def path(self) -> Path:
        return self._path

    # -- reading ----------------------------------------------------------

    def load(self) -> LoadResult:
        self._refuse_write_reason = None

        if not self._path.exists():
            return LoadResult(settings=Settings())

        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            reason = f"could not read {self._path}: {exc}"
            log.warning("settings unreadable: %s", reason)
            self._refuse_write_reason = reason
            return LoadResult(settings=Settings(), problems=(reason,), writable=False)

        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            return self._quarantine(f"settings document is not valid JSON: {exc}")

        if not isinstance(raw, dict):
            return self._quarantine(
                f"settings document must be a JSON object, got {type(raw).__name__}"
            )

        version = raw.get("schema_version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            return self._quarantine(f"settings document has no usable schema_version: {version!r}")

        if version > SCHEMA_VERSION:
            reason = (
                f"settings schema version {version} is newer than this build supports "
                f"({SCHEMA_VERSION}); using defaults and refusing to overwrite"
            )
            log.warning("%s", reason)
            self._refuse_write_reason = reason
            return LoadResult(settings=Settings(), problems=(reason,), writable=False)

        problems: list[str] = []
        if version < SCHEMA_VERSION:
            # No older schema exists in Phase 1; the branch exists so the migration
            # hook is added deliberately rather than invented later.
            problems.append(
                f"settings schema version {version} predates {SCHEMA_VERSION}; "
                "using defaults for unknown fields"
            )

        settings, field_problems = Settings.from_dict(raw)
        problems.extend(field_problems)
        for problem in problems:
            log.warning("settings: %s", problem)

        return LoadResult(settings=settings, problems=tuple(problems))

    # -- writing ----------------------------------------------------------

    def save(self, settings: Settings) -> None:
        """Persist ``settings`` atomically, or raise :class:`SettingsError`."""
        if self._refuse_write_reason is not None:
            raise SettingsError(self._refuse_write_reason)

        problems = settings.validate()
        if problems:
            raise SettingsError("refusing to persist invalid settings: " + "; ".join(problems))

        payload = settings.to_dict()
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_name(self._path.name + ".tmp")
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, self._path)

    # -- helpers ----------------------------------------------------------

    def _quarantine(self, reason: str) -> LoadResult:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        target = self._path.with_name(f"{self._path.stem}.corrupt-{stamp}{self._path.suffix}")
        message = f"{reason}; moved to {target.name} and using defaults"
        log.warning("settings quarantined: %s", message)
        try:
            os.replace(self._path, target)
        except OSError as exc:
            return LoadResult(
                settings=Settings(),
                problems=(f"{reason}; quarantine failed: {exc}",),
                writable=False,
            )
        return LoadResult(settings=Settings(), problems=(message,), quarantined=target)
