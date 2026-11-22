"""Command Centre view-model behaviour, including its Qt-free guarantee."""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime

from orion.config.settings import Severity
from orion.mock.state_provider import MockStateProvider
from orion.ui.viewmodels.command_centre_vm import COMMAND_MAX_LENGTH, CommandCentreViewModel
from orion.ui.viewmodels.console_vm import ConsoleViewModel

FIXED_NOW = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)


def _view_model() -> CommandCentreViewModel:
    provider = MockStateProvider(clock=lambda: FIXED_NOW)
    console = ConsoleViewModel(clock=lambda: FIXED_NOW)
    return CommandCentreViewModel(
        provider=provider,
        console=console,
        request_id_factory=lambda: "req-fixed",
    )


def test_can_submit_rejects_blank_and_overlong_input() -> None:
    vm = _view_model()

    assert vm.can_submit("") is False
    assert vm.can_submit("   \n ") is False
    assert vm.can_submit("do the thing") is True
    assert vm.can_submit("x" * COMMAND_MAX_LENGTH) is True
    assert vm.can_submit("x" * (COMMAND_MAX_LENGTH + 1)) is False


def test_blank_submission_is_rejected_without_calling_the_provider() -> None:
    vm = _view_model()
    result = vm.submit("   ")

    assert result.accepted is False
    assert result.request_id == "req-fixed"
    assert vm.snapshot().tasks == ()


def test_successful_submission_creates_a_simulated_task() -> None:
    vm = _view_model()
    result = vm.submit("Review the roadmap")

    assert result.accepted is True
    assert result.simulated is True
    assert len(vm.snapshot().tasks) == 1
    assert vm.last_result == result


def test_submission_is_mirrored_into_the_console() -> None:
    provider = MockStateProvider(clock=lambda: FIXED_NOW)
    console = ConsoleViewModel(clock=lambda: FIXED_NOW)
    vm = CommandCentreViewModel(provider, console, request_id_factory=lambda: "req-1")

    vm.submit("Review the roadmap")

    entries = console.entries()
    assert entries[-1].source == "composer"
    assert "sim-0001" in entries[-1].message


def test_rejection_is_logged_as_a_warning() -> None:
    provider = MockStateProvider(clock=lambda: FIXED_NOW)
    console = ConsoleViewModel(clock=lambda: FIXED_NOW)
    vm = CommandCentreViewModel(provider, console, request_id_factory=lambda: "req-1")

    vm.submit("")

    entries = console.entries()
    assert entries[-1].severity is Severity.WARNING


def test_overlong_submission_is_rejected() -> None:
    vm = _view_model()
    result = vm.submit("x" * (COMMAND_MAX_LENGTH + 1))

    assert result.accepted is False
    assert "exceeds" in result.message
    assert vm.snapshot().tasks == ()


def test_view_models_import_no_qt() -> None:
    """The view models must stay testable without a QApplication."""
    code = (
        "import sys;"
        "import orion.ui.viewmodels.command_centre_vm;"
        "import orion.ui.viewmodels.console_vm;"
        "assert not any(m.startswith('PySide6') for m in sys.modules), 'Qt imported';"
        "print('clean')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "clean"
