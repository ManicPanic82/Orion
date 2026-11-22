"""Typed errors for Orion Model Manager and Model Profiles."""

from __future__ import annotations


class ModelProfileError(Exception):
    """Base class for model profile related errors."""


class ProfileValidationError(ModelProfileError):
    """Raised when a profile manifest fails schema or semantic validation."""


class ProfileIncompatibleError(ModelProfileError):
    """Raised when base model and adapter/runtime are incompatible."""


class AdapterRequiredError(ProfileIncompatibleError):
    """Raised when a required adapter is missing or unusable."""


class UnsupportedBackendError(ProfileIncompatibleError):
    """Raised when the selected backend does not support the profile."""


class ModelLoadError(ModelProfileError):
    """Raised when a profile cannot be loaded."""


class PartialLoadError(ModelLoadError):
    """Raised when a load fails partway and cleanup was required."""


class ProfileNotFoundError(ModelProfileError):
    """Raised when a requested profile cannot be found."""


class ProfileRepositoryError(ModelProfileError):
    """Raised for profile repository failures."""
