"""Compatibility validation helpers for Model Profiles."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from orion.models.errors import ProfileValidationError, UnsupportedBackendError
from orion.models.profile import AdapterRequirement, ModelProfile


def _within_roots(path: Any, roots: Iterable[Any]) -> bool:
    if not roots:
        return True
    if path in ("", None):
        return True
    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    for root in roots:
        if root in ("", None):
            continue
        try:
            resolved.relative_to(Path(root).resolve())
            return True
        except (ValueError, OSError, RuntimeError):
            continue
    return False


def validate_profile(
    profile: ModelProfile | Any,
    *,
    host: Any = None,
    model_root: Any = None,
    approved_roots: Iterable[Any] | None = None,
    allowed_backends: Iterable[str] | None = None,
) -> list[str]:
    """Return a list of validation problems; empty means valid."""
    if not isinstance(profile, ModelProfile):
        try:
            profile = ModelProfile.from_manifest(profile)
        except Exception as exc:  # pragma: no cover - defensive
            return [str(exc)]

    problems: list[str] = list(profile.validate())

    roots = list(approved_roots) if approved_roots is not None else []
    if model_root is not None:
        roots.append(model_root)

    if not _within_roots(profile.base_model.path, roots):
        problems.append(f"base model path {profile.base_model.path!r} is outside approved roots")
    if not _within_roots(profile.adapter.path, roots):
        problems.append(f"adapter path {profile.adapter.path!r} is outside approved roots")
    if not _within_roots(profile.tokenizer.path, roots):
        problems.append(f"tokenizer path {profile.tokenizer.path!r} is outside approved roots")

    if host is not None:
        try:
            runtime = host.describe_runtime()
            if not getattr(runtime, "supports_backend", lambda b: True)(profile.base_model.backend):
                problems.append(f"backend {profile.base_model.backend!r} is not supported by host")
            if profile.adapter.requirement is AdapterRequirement.REQUIRED and not getattr(
                runtime, "supports_adapters", True
            ):
                problems.append("host does not support required adapters")
        except Exception as exc:
            problems.append(f"host capability check failed: {exc}")

    if allowed_backends is not None and profile.base_model.backend not in allowed_backends:
        problems.append(f"backend {profile.base_model.backend!r} is not allowed")

    # Adapter compatibility: required adapter must have a usable reference.
    if (
        profile.adapter.requirement is AdapterRequirement.REQUIRED
        and not profile.adapter.path
        and not profile.adapter.identity
    ):
        problems.append("required adapter is missing")

    return problems


def ensure_valid_profile(profile: Any, **kwargs: Any) -> ModelProfile:
    """Validate and return the profile, raising on any problem."""
    manifest = (
        ModelProfile.from_manifest(profile) if not isinstance(profile, ModelProfile) else profile
    )
    problems = validate_profile(manifest, **kwargs)
    if problems:
        # Raise a more specific error when possible.
        if any("required adapter" in p or "adapter is missing" in p for p in problems):
            from orion.models.errors import AdapterRequiredError

            raise AdapterRequiredError("; ".join(problems))
        if any("backend" in p and "not supported" in p for p in problems):
            raise UnsupportedBackendError("; ".join(problems))
        raise ProfileValidationError("; ".join(problems))
    return manifest
