"""Profile repositories for Orion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from orion.models.errors import ProfileNotFoundError, ProfileRepositoryError
from orion.models.profile import ModelProfile


class ProfileRepository(Protocol):
    def save(self, profile: ModelProfile) -> None: ...
    def get(self, profile_id: str) -> ModelProfile: ...
    def list(self) -> list[ModelProfile]: ...
    def delete(self, profile_id: str) -> None: ...


class InMemoryProfileRepository:
    """In-memory profile repository."""

    def __init__(self) -> None:
        self._profiles: dict[str, ModelProfile] = {}

    def save(self, profile: ModelProfile) -> None:
        self._profiles[profile.profile_id_or_name] = profile

    def get(self, profile_id: str) -> ModelProfile:
        if profile_id not in self._profiles:
            raise ProfileNotFoundError(f"profile not found: {profile_id!r}")
        return self._profiles[profile_id]

    def list(self) -> list[ModelProfile]:
        return list(self._profiles.values())

    def delete(self, profile_id: str) -> None:
        if profile_id in self._profiles:
            del self._profiles[profile_id]

    def clear(self) -> None:
        self._profiles.clear()


class JsonProfileRepository:
    """File-backed profile repository storing one JSON file per profile."""

    def __init__(self, root: Any) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, profile_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in profile_id)
        return self.root / f"{safe}.json"

    def save(self, profile: ModelProfile) -> None:
        path = self._path_for(profile.profile_id_or_name)
        try:
            path.write_text(profile.to_json(), encoding="utf-8")
        except OSError as exc:
            raise ProfileRepositoryError(str(exc)) from exc

    def get(self, profile_id: str) -> ModelProfile:
        path = self._path_for(profile_id)
        if not path.exists():
            raise ProfileNotFoundError(f"profile not found: {profile_id!r}")
        try:
            return ModelProfile.from_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ProfileRepositoryError(str(exc)) from exc

    def list(self) -> list[ModelProfile]:
        profiles: list[ModelProfile] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                profiles.append(ModelProfile.from_json(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return profiles

    def delete(self, profile_id: str) -> None:
        path = self._path_for(profile_id)
        if path.exists():
            path.unlink()
