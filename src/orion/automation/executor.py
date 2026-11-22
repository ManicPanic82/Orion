"""Process execution service for Orion automation."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from orion.automation.models import ExecutionRequest, ExecutionResult, IdempotencyClass
from orion.automation.workspace import PathEscapeError, redact_text

# Deterministic read-only commands: (allowed executable names, argument prefix).
# This allowlist is the *only* way a request is classified as read-only without a
# permission gateway. It is owned by this module, never by the model supplying
# the request.
_PROTECTED_ENV_KEYS = frozenset(
    {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "PYTHONPATH",
        "PYTHONHOME",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "DYLD_INSERT_LIBRARIES",
        "GIT_PAGER",
        "PAGER",
        "GIT_OPTIONAL_LOCKS",
        "GIT_CONFIG_NOSYSTEM",
    }
)


_DETERMINISTIC_READ_ONLY_COMMANDS: tuple[tuple[frozenset[str], tuple[str, ...]], ...] = (
    (frozenset({"git.exe", "git"}), ("status",)),
)


def classify_request(request: ExecutionRequest) -> IdempotencyClass:
    """Deterministically classify the side effects of an execution request.

    Read-only requires both an explicit ``READ_ONLY`` marking *and* a match on
    the fixed allowlist above. Everything else is non-idempotent: the
    classification never defaults to the safe category, so an omitted or
    model-supplied classification can never widen permissions.
    """
    if request.idempotency is not IdempotencyClass.READ_ONLY:
        return IdempotencyClass.NON_IDEMPOTENT
    name = Path(request.executable).name.lower()
    for allowed_names, prefix in _DETERMINISTIC_READ_ONLY_COMMANDS:
        if name in allowed_names and request.args[: len(prefix)] == list(prefix):
            return IdempotencyClass.READ_ONLY
    return IdempotencyClass.NON_IDEMPOTENT


class AutomationExecutor:
    def __init__(
        self,
        *,
        approved_roots: list[str] | None = None,
        permission_gateway: Any = None,
        allowed_executables: set[str] | None = None,
    ) -> None:
        # Mandatory restrictions are immutable after construction. Resolve
        # roots once so a later symlink replacement cannot widen the workspace.
        self._approved_roots = tuple(
            Path(root).resolve(strict=False) for root in (approved_roots or [])
        )
        self._permission_gateway = permission_gateway
        configured_executables = frozenset(str(item) for item in (allowed_executables or set()))
        self._allowed_executables = configured_executables
        self._resolved_executables: dict[str, str] = {}
        for configured in configured_executables:
            resolved = self._resolve_executable(configured)
            if resolved is not None:
                self._resolved_executables[os.path.normcase(configured)] = resolved
        self._lock = threading.RLock()

    def _resolve_executable(self, configured: str) -> str | None:
        candidate = Path(configured)
        try:
            if candidate.is_absolute():
                resolved = candidate.resolve(strict=True)
            else:
                located = shutil.which(configured)
                if located is None:
                    return None
                resolved = Path(located).resolve(strict=True)
        except (OSError, RuntimeError):
            return None
        if not resolved.is_file():
            return None
        if any(resolved.is_relative_to(root) for root in self._approved_roots):
            return None
        return str(resolved)

    @property
    def approved_roots(self) -> tuple[str, ...]:
        return tuple(str(root) for root in self._approved_roots)

    @property
    def allowed_executables(self) -> frozenset[str]:
        return self._allowed_executables

    @property
    def permission_gateway(self) -> Any:
        return self._permission_gateway

    def validate_request(self, request: ExecutionRequest) -> tuple[Path, str]:
        if not self._allowed_executables:
            raise ValueError("AutomationExecutor requires an allowed_executables allowlist")
        executable_key = os.path.normcase(request.executable)
        resolved_executable = self._resolved_executables.get(executable_key)
        if resolved_executable is None:
            raise ValueError(f"executable is not allowlisted or could not be resolved: {request.executable}")
        protected_overrides = {
            key.upper()
            for key in (request.env or {})
            if key.upper() in _PROTECTED_ENV_KEYS or key.upper().startswith("GIT_")
        }
        if protected_overrides:
            raise ValueError(
                "environment cannot override executable resolution or code-loading keys: "
                + ", ".join(sorted(protected_overrides))
            )
        if not self._approved_roots:
            raise ValueError("AutomationExecutor requires approved_roots")
        requested_root = request.working_dir or str(self._approved_roots[0])
        resolved = Path(requested_root).resolve(strict=False)
        if not any(resolved.is_relative_to(root) for root in self._approved_roots):
            raise PathEscapeError(f"path {resolved} is outside approved roots")
        return resolved, resolved_executable

    def _permission_check(
        self, request: ExecutionRequest, working_dir: Path
    ) -> None:
        effective = classify_request(request)
        if effective is IdempotencyClass.READ_ONLY:
            # Deterministically allowlisted read-only command, no gateway needed.
            return
        if self._permission_gateway is None:
            # Fail closed for side-effecting commands.
            raise PermissionError("permission gateway unavailable")
        decision = self._permission_gateway.decide(
            "automation.execute",
            str(working_dir) if working_dir is not None else "",
            idempotency=effective.value,
            task_id=request.task_id,
            args={"executable": request.executable, "args": request.args},
        )
        from orion.permissions.models import PermissionDecision

        if decision.decision is not PermissionDecision.ALLOW:
            raise PermissionError(
                f"permission {decision.decision.value}: {decision.rationale_code}"
            )

    def execute(self, request: ExecutionRequest, *, cancel_event: Any = None) -> ExecutionResult:
        working_dir, executable = self.validate_request(request)
        if request.dry_run:
            return ExecutionResult(
                request_id=request.request_id, exit_code=0, stdout="dry run", stderr=""
            )
        self._permission_check(request, working_dir)

        result = ExecutionResult(request_id=request.request_id)
        start = time.monotonic()
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        def _reader(pipe, chunks, cap):
            try:
                while True:
                    data = pipe.read(4096)
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")
                    current = sum(len(c) for c in chunks)
                    if current < cap:
                        chunks.append(text[: cap - current])
            finally:
                pipe.close()

        command_args = list(request.args)
        process_env = {**os.environ, **request.env} if request.env else dict(os.environ)
        if classify_request(request) is IdempotencyClass.READ_ONLY:
            # The only unprivileged command is Git status with optional writes,
            # filesystem monitors, and pagers disabled.
            command_args = [
                "--no-pager",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                "--no-optional-locks",
                "status",
                *request.args[1:],
            ]
            for key in tuple(process_env):
                if key.upper().startswith("GIT_"):
                    process_env.pop(key, None)
            process_env.update(
                {
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_OPTIONAL_LOCKS": "0",
                    "GIT_PAGER": "cat",
                    "PAGER": "cat",
                }
            )
        try:
            proc = subprocess.Popen(
                [executable, *command_args],
                cwd=str(working_dir) if working_dir is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env,
                text=False,
            )
        except Exception as exc:
            result.error = str(exc)
            result.duration_s = time.monotonic() - start
            return result

        t_out = threading.Thread(
            target=_reader, args=(proc.stdout, stdout_chunks, request.output_cap), daemon=True
        )
        t_err = threading.Thread(
            target=_reader, args=(proc.stderr, stderr_chunks, request.output_cap), daemon=True
        )
        t_out.start()
        t_err.start()

        timed_out = False
        cancelled = False
        try:
            while proc.poll() is None:
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    proc.terminate()
                    break
                if time.monotonic() - start >= request.timeout_s:
                    timed_out = True
                    proc.terminate()
                    break
                time.sleep(0.05)
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            timed_out = True
        except Exception as exc:
            result.error = str(exc)

        t_out.join(timeout=5.0)
        t_err.join(timeout=5.0)

        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)
        result.stdout = redact_text(stdout, [])
        result.stderr = redact_text(stderr, [])
        result.exit_code = proc.returncode
        result.timed_out = timed_out
        result.cancelled = cancelled
        result.duration_s = time.monotonic() - start
        result.redacted = True
        return result

    # PowerShell helper
    def run_powershell(
        self, script: str, *, request: ExecutionRequest | None = None
    ) -> ExecutionResult:
        import base64

        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        # The supplied script is the command to run: a caller-provided request
        # may carry other options (timeout, task_id, ...), but any command
        # arguments are dropped so the script is never ignored.
        req = request or ExecutionRequest(executable="powershell.exe")
        req.executable = req.executable or "powershell.exe"
        req.args = ["-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
        return self.execute(req)
