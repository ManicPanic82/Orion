"""Runtime state enums and status objects for the Model Manager."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ModelLoadState(StrEnum):
    """Observable load state of a Model Manager."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"
    UNLOADING = "unloading"


# Aliases used by different callers/tests.
ProfileLoadState = ModelLoadState
ModelStatusState = ModelLoadState
ModelManagerState = ModelLoadState


@dataclass(slots=True)
class ModelManagerStatus:
    """Snapshot of a Model Manager."""

    state: ModelLoadState
    active_profile_id: str | None = None
    is_mock: bool = False
    last_error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "active_profile_id": self.active_profile_id,
            "is_mock": self.is_mock,
            "last_error": self.last_error,
        }
