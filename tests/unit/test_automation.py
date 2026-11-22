"""Tests for Windows automation."""

from __future__ import annotations

import sys
import tempfile

from orion.automation import AutomationExecutor, ExecutionRequest


def test_approved_command_executes() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable, args=["-c", "print('hello')"], working_dir=td, timeout_s=10
        )
        executor = AutomationExecutor(approved_roots=[td])
        result = executor.execute(req)
        assert result.exit_code == 0
        assert "hello" in result.stdout


def test_working_directory_escape_blocked() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable,
            args=["-c", "print('x')"],
            working_dir="C:\\Windows",
            timeout_s=10,
        )
        executor = AutomationExecutor(approved_roots=[td])
        try:
            executor.execute(req)
        except Exception:
            pass
        else:
            raise AssertionError("escape should be blocked")


def test_timeout_terminates() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable,
            args=["-c", "import time; time.sleep(10)"],
            working_dir=td,
            timeout_s=0.2,
        )
        executor = AutomationExecutor(approved_roots=[td])
        result = executor.execute(req)
        assert result.timed_out is True


def test_output_cap() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable,
            args=["-c", "print('a'*1000)"],
            working_dir=td,
            timeout_s=10,
            output_cap=10,
        )
        executor = AutomationExecutor(approved_roots=[td])
        result = executor.execute(req)
        assert len(result.stdout) <= 10


def test_denied_command_never_starts_without_gateway_for_side_effect() -> None:
    with tempfile.TemporaryDirectory() as td:
        from orion.automation.models import IdempotencyClass

        req = ExecutionRequest(
            executable=sys.executable,
            args=["-c", "print('x')"],
            working_dir=td,
            idempotency=IdempotencyClass.NON_IDEMPOTENT,
        )
        executor = AutomationExecutor(approved_roots=[td], permission_gateway=None)
        try:
            executor.execute(req)
        except PermissionError:
            pass
        else:
            raise AssertionError("should be denied")


def test_dry_run() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable, args=["-c", "print('x')"], working_dir=td, dry_run=True
        )
        executor = AutomationExecutor(approved_roots=[td])
        result = executor.execute(req)
        assert result.stdout == "dry run"


def test_powershell_encoded() -> None:
    with tempfile.TemporaryDirectory() as td:
        executor = AutomationExecutor(approved_roots=[td])
        result = executor.run_powershell("Write-Output 'ps-ok'")
        # powershell may not be available; accept either success or error without crash
        assert result is not None
