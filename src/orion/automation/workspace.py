"""Workspace and path safety helpers for automation."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any


class PathEscapeError(ValueError):
    """Raised when a path escapes approved roots."""


def canonicalise(path: Any) -> Path:
    return Path(path).resolve(strict=False)


def is_within_roots(path: Any, roots: Iterable[Any]) -> bool:
    try:
        resolved = canonicalise(path)
    except (OSError, RuntimeError, ValueError):
        return False
    for root in roots:
        if root in ("", None):
            continue
        try:
            resolved.relative_to(canonicalise(root))
            return True
        except (ValueError, OSError, RuntimeError):
            continue
    return False


def ensure_within_roots(path: Any, roots: Iterable[Any]) -> Path:
    resolved = canonicalise(path)
    if not is_within_roots(resolved, roots):
        raise PathEscapeError(f"path {resolved} is outside approved roots")
    return resolved


def redact_text(text: str, secrets: list[str] | None = None) -> str:
    import re

    result = text
    for secret in secrets or []:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    # Common patterns.
    result = re.sub(r"(?i)(password|token|api_key)\s*[:=]\s*\S+", r"\1=[REDACTED]", result)
    return result
