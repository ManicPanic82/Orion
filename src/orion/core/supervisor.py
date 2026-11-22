"""Core supervisor: bounded restart policy and crash diagnostics."""

from __future__ import annotations

from orion.core.lifecycle import CoreLifecycleState

__all__ = ["CoreSupervisor", "RestartPolicy"]

_DEFAULT_MAX_RESTARTS = 3
_DEFAULT_INITIAL_DELAY_S = 1.0
_DEFAULT_MAX_DELAY_S = 30.0


class RestartPolicy:
    """Bounded exponential-backoff restart policy."""

    def __init__(
        self,
        *,
        max_restarts: int = _DEFAULT_MAX_RESTARTS,
        initial_delay_s: float = _DEFAULT_INITIAL_DELAY_S,
        max_delay_s: float = _DEFAULT_MAX_DELAY_S,
    ) -> None:
        self.max_restarts = max(int(max_restarts), 0)
        self.initial_delay_s = max(float(initial_delay_s), 0.0)
        self.max_delay_s = max(float(max_delay_s), 0.0)

    def should_restart(self, attempt: int) -> bool:
        """Return True while restart attempt ``attempt`` is within budget."""
        return attempt <= self.max_restarts

    def backoff_s(self, attempt: int) -> float:
        """Return the delay before restart attempt ``attempt`` (1-based)."""
        if self.initial_delay_s <= 0:
            return 0.0
        delay = self.initial_delay_s * (2 ** max(attempt - 1, 0))
        return min(delay, self.max_delay_s)


class CoreSupervisor:
    """Owns restart decisions and crash diagnostics for the Core process."""

    def __init__(self, policy: RestartPolicy | None = None) -> None:
        self._policy = policy or RestartPolicy()
        self._attempts = 0
        self._crashes: list[dict[str, object]] = []

    @property
    def policy(self) -> RestartPolicy:
        return self._policy

    @property
    def crashes(self) -> tuple[dict[str, object], ...]:
        return tuple(self._crashes)

    @property
    def attempts(self) -> int:
        return self._attempts

    def record_crash(self, *, reason: str, exit_code: int | None = None) -> None:
        """Record a crash occurrence and move the restart attempt counter."""
        self._attempts += 1
        self._crashes.append({"reason": reason, "exit_code": exit_code})

    def should_restart(self) -> bool:
        """Return True while another bounded restart is permitted."""
        return self._policy.should_restart(self._attempts)

    def reset(self) -> None:
        """Clear crash history after a clean stop."""
        self._attempts = 0
        self._crashes.clear()

    def final_state(self, *, crashed: bool) -> CoreLifecycleState:
        """Return the terminal state after a crash or a clean stop."""
        if crashed and not self.should_restart():
            return CoreLifecycleState.FAILED
        return CoreLifecycleState.STOPPED
