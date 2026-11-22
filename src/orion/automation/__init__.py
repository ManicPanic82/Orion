"""Windows automation for Orion."""

from orion.automation.executor import AutomationExecutor
from orion.automation.models import (
    CommandProfile,
    ExecutionRequest,
    ExecutionResult,
    IdempotencyClass,
)
from orion.automation.workspace import (
    PathEscapeError,
    ensure_within_roots,
    is_within_roots,
    redact_text,
)

__all__ = [
    "AutomationExecutor",
    "CommandProfile",
    "ExecutionRequest",
    "ExecutionResult",
    "IdempotencyClass",
    "PathEscapeError",
    "ensure_within_roots",
    "is_within_roots",
    "redact_text",
]
# Aliases
AutomationEngine = AutomationExecutor
