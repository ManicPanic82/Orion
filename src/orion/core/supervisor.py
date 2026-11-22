"""Core supervisor: real process supervision with bounded restart policy."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from orion.core.lifecycle import CoreLifecycleState

__all__ = ["CoreSupervisor", "RestartPolicy"]

_DEFAULT_MAX_RESTARTS = 1
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
    """Supervises child processes: watches them and restarts crashed ones.

    The supervisor is the decision layer for restart behaviour (bounded
    backoff policy + crash diagnostics); :meth:`supervise` is the execution
    layer: it actually starts a child, watches it, and restarts it while the
    policy allows.
    """

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

    def supervise(
        self,
        spawn: Callable[[], Any],
        *,
        stop_event: threading.Event | None = None,
    ) -> int:
        """Supervise a child process with the restart policy.

        Starts the child via ``spawn`` and loops: when the child exits, the
        exit is recorded as a crash and a new child is spawned with
        backoff while the policy permits. Returns ``0`` on clean exit or a
        requested stop; returns ``1`` when the restart budget is exhausted
        after repeated crashes.
        """
        if stop_event is not None and stop_event.is_set():
            return 0

        child = spawn()
        while True:
            if stop_event is not None and stop_event.is_set():
                self._stop_child(child)
                return 0

            crash_reason = "child_exited"
            try:
                poll = getattr(child, "poll", None)
                if callable(poll):
                    exit_code = poll()
                    if exit_code is None:
                        if stop_event is not None:
                            stop_event.wait(0.05)
                        else:
                            time.sleep(0.05)
                        continue
                else:
                    try:
                        exit_code = child.wait(timeout=0.1)
                    except TypeError as exc:
                        if stop_event is not None:
                            raise RuntimeError(
                                "child must support poll() or wait(timeout=) for interruptible shutdown"
                            ) from exc
                        # Compatibility for simple synchronous test doubles.
                        exit_code = child.wait()
                    except subprocess.TimeoutExpired:
                        continue
            except Exception as exc:  # child died hard: treat as crash
                crash_reason = f"child_wait_failed: {exc}"
                exit_code = 1

            if stop_event is not None and stop_event.is_set():
                self._stop_child(child)
                return 0
            if exit_code == 0:
                return 0

            self.record_crash(reason=crash_reason, exit_code=exit_code)
            if not self.should_restart():
                return 1

            delay = self.policy.backoff_s(self._attempts)
            if stop_event is not None:
                if stop_event.wait(delay):
                    return 0
            else:
                time.sleep(delay)
            child = spawn()

    @staticmethod
    def _stop_child(child: Any, *, grace_seconds: float = 2.0) -> None:
        """Request graceful child shutdown, escalating to kill after a grace period."""
        terminate = getattr(child, "terminate", None)
        if not callable(terminate):
            kill = getattr(child, "kill", None)
            if callable(kill):
                kill()
                try:
                    child.wait(timeout=grace_seconds)
                except (subprocess.TimeoutExpired, TypeError):
                    pass
                return
            raise RuntimeError("supervised child does not support terminate or kill")
        try:
            terminate()
            try:
                child.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                kill = getattr(child, "kill", None)
                if callable(kill):
                    kill()
                    child.wait(timeout=grace_seconds)
            except TypeError:
                child.wait()
        except Exception:
            # Shutdown is best-effort here; the supervisor's caller still exits.
            kill = getattr(child, "kill", None)
            if callable(kill):
                try:
                    kill()
                    try:
                        child.wait(timeout=grace_seconds)
                    except (subprocess.TimeoutExpired, TypeError):
                        pass
                except Exception:
                    pass
