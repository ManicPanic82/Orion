"""Command Centre behaviour, free of Qt.

The page widget renders what this object exposes. Validation, provider calls, and
console side effects happen here so they are testable without a QApplication.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from orion.config.settings import Severity
from orion.state.models import MAX_COMMAND_LENGTH, AppSnapshot, CommandResult
from orion.state.provider import StateProvider
from orion.ui.viewmodels.console_vm import ConsoleViewModel

__all__ = ["CommandCentreViewModel", "COMMAND_MAX_LENGTH"]

COMMAND_MAX_LENGTH = MAX_COMMAND_LENGTH


class CommandCentreViewModel:
    """Coordinates snapshots and command submissions for the Command Centre."""

    def __init__(
        self,
        provider: StateProvider,
        console: ConsoleViewModel,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._provider = provider
        self._console = console
        self._request_id_factory = request_id_factory or (lambda: uuid.uuid4().hex)
        self._last_result: CommandResult | None = None

    @property
    def provider(self) -> StateProvider:
        return self._provider

    @property
    def last_result(self) -> CommandResult | None:
        return self._last_result

    def snapshot(self) -> AppSnapshot:
        return self._provider.snapshot()

    def can_submit(self, text: str) -> bool:
        stripped = text.strip()
        return bool(stripped) and len(stripped) <= COMMAND_MAX_LENGTH

    def submit(self, text: str) -> CommandResult:
        """Validate and submit ``text``, mirroring the outcome into the console."""
        stripped = text.strip()
        request_id = str(self._request_id_factory())

        if not stripped:
            result = CommandResult(
                request_id=request_id,
                accepted=False,
                simulated=True,
                message="Enter an objective before submitting.",
            )
            self._last_result = result
            self._console.append(Severity.WARNING, "composer", result.message)
            return result

        if len(stripped) > COMMAND_MAX_LENGTH:
            result = CommandResult(
                request_id=request_id,
                accepted=False,
                simulated=True,
                message=f"Objective exceeds {COMMAND_MAX_LENGTH} characters.",
            )
            self._last_result = result
            self._console.append(Severity.WARNING, "composer", result.message)
            return result

        result = self._provider.submit_command(stripped, request_id)
        self._last_result = result
        severity = Severity.INFO if result.accepted else Severity.WARNING
        self._console.append(severity, "composer", result.message)
        return result
