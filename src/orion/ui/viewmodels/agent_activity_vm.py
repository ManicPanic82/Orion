"""Agent Activity view model — the real task engine state via the provider."""

from __future__ import annotations

from orion.state.models import AppSnapshot, TaskSummary
from orion.state.provider import StateProvider


class AgentActivityViewModel:
    """Exposes live task state from the provider for the task list."""

    def __init__(self, provider: StateProvider) -> None:
        self._provider = provider

    def snapshot(self) -> AppSnapshot:
        return self._provider.snapshot()

    def tasks(self) -> tuple[TaskSummary, ...]:
        return self._provider.snapshot().tasks
