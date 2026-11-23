"""Model Manager view model — registered profiles + live runtime status."""

from __future__ import annotations

from orion.models.manager import ModelManager
from orion.models.profile import ModelProfile

__all__ = ["ModelManagerViewModel"]


class ModelManagerViewModel:
    """Exposes the Model Manager's profile list and load state."""

    def __init__(self, model_manager: ModelManager) -> None:
        self._manager = model_manager

    @property
    def is_ready(self) -> bool:
        return self._manager.is_ready

    def status(self):  # noqa: ANN201 - models.state.ModelManagerStatus
        return self._manager.status

    def profiles(self) -> list[ModelProfile]:
        return self._manager.list_profiles()
