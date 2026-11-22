"""Process execution service for Orion automation."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Any

from orion.automation.models import ExecutionRequest, ExecutionResult
from orion.automation.workspace import ensure_within_roots, redact_text


class AutomationExecutor:
    def __init__(
        self,
        *,
        approved_roots: list[str] | None = None,
        permission_gateway: Any = None,
        allowed_executables: set[str] | None = None,
    ) -> None:
        self.approved_roots = list(approved_roots or [])
        self.permission_gateway = permission_gateway
        self.allowed_executables = set(allowed_executables or set())
        self._lock = threading.RLock()

    def validate_request(self, request: ExecutionRequest) -> None:
        if self.approved_roots and request.working_dir:
            ensure_within_roots(request.working_dir, self.approved_roots)
        if self.allowed_executables and request.executable not in self.allowed_executables:
            raise ValueError(f"executable not allowed: {request.executable}")

    def _permission_check(self, request: ExecutionRequest) -> None:
        if self.permission_gateway is None:
            # Fail closed for side-effecting commands.
            if request.idempotency.value != "read_only":
                raise PermissionError("permission gateway unavailable")
            return
        decision = self.permission_gateway.decide(
            "automation.execute",
            request.working_dir or "",
            idempotency=request.idempotency.value,
            task_id=request.task_id,
            args={"executable": request.executable, "args": request.args},
        )
        from orion.permissions.models import PermissionDecision

        if decision.decision is not PermissionDecision.ALLOW:
            raise PermissionError(
                f"permission {decision.decision.value}: {decision.rationale_code}"
            )

    def execute(self, request: ExecutionRequest, *, cancel_event: Any = None) -> ExecutionResult:
        self.validate_request(request)
        if request.dry_run:
            return ExecutionResult(
                request_id=request.request_id, exit_code=0, stdout="dry run", stderr=""
            )
        self._permission_check(request)

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

        try:
            proc = subprocess.Popen(
                [request.executable, *request.args],
                cwd=request.working_dir or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **request.env} if request.env else None,
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
        req = request or ExecutionRequest(
            executable="powershell.exe",
            args=["-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        )
        if not req.args:
            req.args = ["-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
        # Ensure executable.
        req.executable = req.executable or "powershell.exe"
        return self.execute(req)
