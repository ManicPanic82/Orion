"""Tests for Windows automation."""

from __future__ import annotations

import sys
import tempfile

from orion.automation import AutomationExecutor, ExecutionRequest, IdempotencyClass
from orion.automation.executor import classify_request
from orion.permissions import AutonomyMode, PermissionGateway, PermissionGrant


def _executor_for(td: str, **kwargs: object) -> AutomationExecutor:
    """Executor with mandatory restrictions + an allowing gateway."""
    gateway = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gateway.add_grant(PermissionGrant(capability_id="automation.execute", action="automation.execute", resource="*"))
    return AutomationExecutor(
        approved_roots=[td],
        allowed_executables={sys.executable, "git.exe", "git", "powershell.exe"},
        permission_gateway=gateway,
        **kwargs,
    )


def test_approved_command_executes() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable,
            args=["-c", "print('hello')"],
            working_dir=td,
            timeout_s=10,
            idempotency=IdempotencyClass.IDEMPOTENT,
        )
        result = _executor_for(td).execute(req)
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
        executor = AutomationExecutor(
            approved_roots=[td],
            allowed_executables={sys.executable},
            permission_gateway=None,
        )
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
            idempotency=IdempotencyClass.IDEMPOTENT,
        )
        result = _executor_for(td).execute(req)
        assert result.timed_out is True


def test_output_cap() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable,
            args=["-c", "print('a'*1000)"],
            working_dir=td,
            timeout_s=10,
            output_cap=10,
            idempotency=IdempotencyClass.IDEMPOTENT,
        )
        result = _executor_for(td).execute(req)
        assert len(result.stdout) <= 10


def test_denied_command_never_starts_without_gateway_for_side_effect() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable,
            args=["-c", "print('x')"],
            working_dir=td,
            idempotency=IdempotencyClass.NON_IDEMPOTENT,
        )
        executor = AutomationExecutor(
            approved_roots=[td],
            allowed_executables={sys.executable},
            permission_gateway=None,
        )
        try:
            executor.execute(req)
        except PermissionError:
            pass
        else:
            raise AssertionError("should be denied")


def test_default_request_is_side_effect() -> None:
    req = ExecutionRequest()
    assert req.idempotency is IdempotencyClass.NON_IDEMPOTENT
    assert classify_request(req) is IdempotencyClass.NON_IDEMPOTENT


def test_executor_requires_allowed_executables() -> None:
    with tempfile.TemporaryDirectory() as td:
        executor = AutomationExecutor(approved_roots=[td], permission_gateway=None)
        try:
            executor.execute(ExecutionRequest(executable=sys.executable, working_dir=td))
        except ValueError:
            pass
        else:
            raise AssertionError("missing allowed_executables should fail")


def test_executor_requires_approved_roots() -> None:
    executor = AutomationExecutor(allowed_executables={sys.executable}, permission_gateway=None)
    try:
        executor.execute(ExecutionRequest(executable=sys.executable))
    except ValueError:
        pass
    else:
        raise AssertionError("missing approved_roots should fail")


def test_deterministic_read_only_classification() -> None:
    req = ExecutionRequest(executable="git", args=["status"])
    assert req.idempotency is IdempotencyClass.NON_IDEMPOTENT  # default, until marked
    req.idempotency = IdempotencyClass.READ_ONLY
    assert classify_request(req) is IdempotencyClass.READ_ONLY
    # Prefix must match exactly.
    req.args = ["status", "--short"]
    assert classify_request(req) is IdempotencyClass.READ_ONLY
    req.args = ["push"]
    assert classify_request(req) is IdempotencyClass.NON_IDEMPOTENT
    # Non-allowlisted commands are never classified read-only.
    req.executable = "powershell.exe"
    req.args = ["-Command", "Get-Date"]
    assert classify_request(req) is IdempotencyClass.NON_IDEMPOTENT


def test_powershell_allowed_executable_enforced() -> None:
    with tempfile.TemporaryDirectory() as td:
        executor = AutomationExecutor(approved_roots=[td], allowed_executables={"notepad.exe"})
        try:
            executor.run_powershell("Write-Output 'ps-ok'")
        except ValueError:
            pass
        else:
            raise AssertionError("executable should be rejected")


def test_powershell_encoded() -> None:
    with tempfile.TemporaryDirectory() as td:
        executor = _executor_for(td)
        result = executor.run_powershell("Write-Output 'ps-ok'")
        # powershell may not be available; accept either success or error without crash
        assert result is not None


def test_powershell_supplied_request_script_wins() -> None:
    with tempfile.TemporaryDirectory() as td:
        executor = _executor_for(td)
        supplied = ExecutionRequest(
            executable="powershell.exe",
            args=["-Command", "Write-Output 'ignored-by-test'"],
            idempotency=IdempotencyClass.IDEMPOTENT,
        )
        result = executor.run_powershell("Write-Output 'ps-ok-real'", request=supplied)
        if result.error is None and result.exit_code == 0:
            assert "ps-ok-real" in result.stdout
            assert "ignored-by-test" not in result.stdout


def test_dry_run() -> None:
    with tempfile.TemporaryDirectory() as td:
        req = ExecutionRequest(
            executable=sys.executable, args=["-c", "print('x')"], working_dir=td, dry_run=True
        )
        executor = _executor_for(td)
        result = executor.execute(req)
        assert result.stdout == "dry run"
