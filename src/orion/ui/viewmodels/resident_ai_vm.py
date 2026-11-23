"""Resident AI view model — conversation with the resident agent."""

from __future__ import annotations

from orion.config.settings import Severity
from orion.state.models import MAX_COMMAND_LENGTH, AppSnapshot, CommandResult, ComponentStatus
from orion.state.provider import StateProvider
from orion.ui.viewmodels.console_vm import ConsoleViewModel

__all__ = ["ResidentAIViewModel"]


class ResidentAIViewModel:
    """Conversation turns submitted through the Core objective pipeline."""

    def __init__(
        self,
        provider: StateProvider,
        console: ConsoleViewModel,
        *,
        max_chars: int = MAX_COMMAND_LENGTH,
    ) -> None:
        self._provider = provider
        self._console = console
        self._max_chars = max_chars
        self._messages: list[tuple[str, str]] = []

    @property
    def max_chars(self) -> int:
        return self._max_chars

    def snapshot(self) -> AppSnapshot:
        return self._provider.snapshot()

    def agent_status(self) -> ComponentStatus:
        return self._provider.snapshot().agent

    def messages(self) -> list[tuple[str, str]]:
        return list(self._messages)

    def can_send(self, text: str) -> bool:
        return bool(text.strip()) and len(text.strip()) <= self._max_chars

    def send(self, text: str, request_id: str) -> CommandResult:
        """Send an objective through the provider; record the exchange in the log."""
        stripped = text.strip()
        if not self.can_send(stripped):
            result = CommandResult(
                request_id=request_id,
                accepted=False,
                simulated=False,
                message=(f"Enter an objective to send (1–{self._max_chars} characters)."),
            )
            self._console.append(Severity.WARNING, "resident_ai", result.message)
            return result

        result = self._provider.submit_command(stripped, request_id)
        self._messages.append(("user", stripped))
        self._messages.append(("agent", result.message))
        severity = Severity.INFO if result.accepted else Severity.WARNING
        self._console.append(severity, "resident_ai", result.message)
        return result
