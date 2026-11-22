"""Automation execution models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class IdempotencyClass(StrEnum):
    READ_ONLY = "read_only"
    IDEMPOTENT = "idempotent"
    NON_IDEMPOTENT = "non_idempotent"


@dataclass(slots=True)
class ExecutionRequest:
    # Default-deny: an unspecified classification is a side-effecting command.
    # ``READ_ONLY`` is only honoured through the executor's deterministic
    # allowlist, never trusted from a model-supplied value.
    request_id: str = field(default_factory=lambda: str(uuid4()))
    executable: str = ""
    args: list[str] = field(default_factory=list)
    working_dir: str = ""
    env: dict[str, str] = field(default_factory=dict)
    timeout_s: float = 30.0
    output_cap: int = 64 * 1024
    task_id: str | None = None
    correlation_id: str | None = None
    idempotency: IdempotencyClass = IdempotencyClass.NON_IDEMPOTENT
    dry_run: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "executable": self.executable,
            "args": list(self.args),
            "working_dir": self.working_dir,
            "timeout_s": self.timeout_s,
            "output_cap": self.output_cap,
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "idempotency": self.idempotency.value,
            "dry_run": self.dry_run,
        }


@dataclass(slots=True)
class ExecutionResult:
    request_id: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    cancelled: bool = False
    duration_s: float = 0.0
    error: str | None = None
    redacted: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "cancelled": self.cancelled,
            "duration_s": self.duration_s,
            "error": self.error,
            "redacted": self.redacted,
        }


@dataclass(slots=True)
class CommandProfile:
    profile_id: str = ""
    name: str = ""
    executable: str = ""
    args: list[str] = field(default_factory=list)
    working_dir: str = ""
    timeout_s: float = 300.0
    idempotency: IdempotencyClass = IdempotencyClass.IDEMPOTENT
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "executable": self.executable,
            "args": list(self.args),
            "working_dir": self.working_dir,
            "timeout_s": self.timeout_s,
            "idempotency": self.idempotency.value,
            "description": self.description,
        }
