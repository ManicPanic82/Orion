"""Core supervisor: real process supervision with bounded restart policy."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from orion.core.lifecycle import CoreLifecycleState

__all__ = ["CoreSupervisor", "RestartPolicy"]

_DEFAULT_MAX_RESTARTS = 1
_DEFAULT_INITIAL_DELAY_S = 1.0
_DEFAULT_MAX_DELAY_S = 30.0
_POLL_INTERVAL_S = 0.1
_TERMINATE_TIMEOUT_S = 5.0


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
        return attempt <= self.max_restarts

    def backoff_s(self, attempt: int) -> float:
        if self.initial_delay_s <= 0:
            return 0.0
        return min(self.initial_delay_s * (2 ** max(attempt - 1, 0)), self.max_delay_s)


class CoreSupervisor:
    """Supervise a child process with interruptible shutdown and restart."""

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
        self._attempts += 1
        self._crashes.append({"reason": reason, "exit_code": exit_code})

    def should_restart(self) -> bool:
        return self._policy.should_restart(self._attempts)

    def reset(self) -> None:
        self._attempts = 0
        self._crashes.clear()

    def final_state(self, *, crashed: bool) -> CoreLifecycleState:
        if crashed and not self.should_restart():
            return CoreLifecycleState.FAILED
        return CoreLifecycleState.STOPPED

    @staticmethod
    def _terminate_child(child: Any, finished: threading.Event) -> None:
        """Ask a running child to stop, escalating to kill after a bounded wait."""
        try:
            poll = getattr(child, "poll", None)
            if poll is None or poll() is None:
                terminate = getattr(child, "terminate", None)
                if terminate is not None:
                    terminate()
        except Exception:
            pass
        if finished.wait(_TERMINATE_TIMEOUT_S):
            return
        try:
            kill = getattr(child, "kill", None)
            if kill is not None:
                kill()
        except Exception:
            pass
        finished.wait(_TERMINATE_TIMEOUT_S)

    def supervise(
        self,
        spawn: Callable[[], Any],
        *,
        stop_event: threading.Event | None = None,
    ) -> int:
        """Return 0 on clean/requested stop, 1 when restart budget is exhausted."""
        if stop_event is not None and stop_event.is_set():
            return 0

        while True:
            child = spawn()
            result: dict[str, Any] = {}
            finished = threading.Event()

            def wait_for_child() -> None:
                try:
                    result["exit_code"] = child.wait()
                except Exception as exc:
                    result["error"] = exc
                finally:
                    finished.set()

            waiter = threading.Thread(target=wait_for_child, name="orion-child-wait", daemon=True)
            waiter.start()

            while not finished.wait(_POLL_INTERVAL_S):
                if stop_event is not None and stop_event.is_set():
                    self._terminate_child(child, finished)
                    return 0

            if stop_event is not None and stop_event.is_set():
                return 0
            if "error" in result:
                self.record_crash(reason=f"child_wait_failed: {result['error']}", exit_code=None)
            else:
                exit_code = result.get("exit_code")
                if exit_code == 0:
                    return 0
                self.record_crash(reason="child_exited", exit_code=exit_code)

            if not self.should_restart():
                return 1

            delay = self.policy.backoff_s(self._attempts)
            if stop_event is not None:
                if stop_event.wait(delay):
                    return 0
            elif delay:
                # Event-based wait keeps the delay interruptible if a stop
                # event is attached by a caller during supervision.
                threading.Event().wait(delay)
