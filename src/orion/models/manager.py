"""Model Manager: atomic profile validation and load/unload lifecycle."""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from typing import Any

from orion.models.compatibility import validate_profile
from orion.models.errors import ModelLoadError, ProfileNotFoundError
from orion.models.host import MockModelHost, ModelHost
from orion.models.profile import ModelProfile
from orion.models.repository import InMemoryProfileRepository, ProfileRepository
from orion.models.state import ModelLoadState, ModelManagerStatus


class ModelManager:
    """Owns profile registration, validation, and atomic load/unload state."""

    def __init__(
        self,
        *,
        host: ModelHost | None = None,
        repository: ProfileRepository | None = None,
        model_root: Any = None,
        approved_roots: Iterable[Any] | None = None,
    ) -> None:
        self._host: ModelHost = host if host is not None else MockModelHost()
        self._repository: ProfileRepository = (
            repository if repository is not None else InMemoryProfileRepository()
        )
        self._model_root = model_root
        self._approved_roots = (
            list(approved_roots)
            if approved_roots is not None
            else ([model_root] if model_root is not None else [])
        )
        self._profiles: dict[str, ModelProfile] = {}
        self._active_profile: ModelProfile | None = None
        self._state = ModelLoadState.UNLOADED
        self._last_error: str | None = None

    # -- properties ------------------------------------------------------

    @property
    def host(self) -> ModelHost:
        return self._host

    @property
    def repository(self) -> ProfileRepository:
        return self._repository

    @property
    def state(self) -> ModelLoadState:
        return self._state

    @property
    def active_profile(self) -> ModelProfile | None:
        return self._active_profile

    @property
    def active(self) -> ModelProfile | None:
        return self._active_profile

    @property
    def loaded_profile(self) -> ModelProfile | None:
        return self._active_profile

    @property
    def is_loaded(self) -> bool:
        return self._active_profile is not None

    @property
    def active_profile_id(self) -> str | None:
        return None if self._active_profile is None else self._active_profile.profile_id_or_name

    @property
    def is_ready(self) -> bool:
        return self._state is ModelLoadState.READY and self._active_profile is not None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def is_mock(self) -> bool:
        return bool(getattr(self._host, "is_mock", False))

    @property
    def status(self) -> ModelManagerStatus:
        return ModelManagerStatus(
            state=self._state,
            active_profile_id=self.active_profile_id,
            is_mock=self.is_mock,
            last_error=self._last_error,
        )

    # -- profile registration --------------------------------------------

    def register(self, profile: Any) -> ModelProfile:
        manifest = (
            profile if isinstance(profile, ModelProfile) else ModelProfile.from_manifest(profile)
        )
        self._profiles[manifest.profile_id_or_name] = manifest
        with contextlib.suppress(Exception):
            self._repository.save(manifest)
        return manifest

    def register_profile(self, profile: Any) -> ModelProfile:
        return self.register(profile)

    def load(self, profile: Any) -> ModelProfile:
        return self.load_profile(profile)

    def unload_profile(self) -> None:
        self.unload()

    def unregister(self, profile_id: str) -> None:
        self._profiles.pop(profile_id, None)
        with contextlib.suppress(Exception):
            self._repository.delete(profile_id)

    def get_profile(self, profile_id: str) -> ModelProfile:
        if profile_id in self._profiles:
            return self._profiles[profile_id]
        try:
            profile = self._repository.get(profile_id)
            self._profiles[profile.profile_id_or_name] = profile
            return profile
        except Exception as exc:
            raise ProfileNotFoundError(f"profile not found: {profile_id!r}") from exc

    def list_profiles(self) -> list[ModelProfile]:
        # Merge repository contents.
        for profile in self._repository.list():
            self._profiles.setdefault(profile.profile_id_or_name, profile)
        return list(self._profiles.values())

    # -- validation ------------------------------------------------------

    def validate(self, profile: Any) -> list[str]:
        manifest = (
            profile if isinstance(profile, ModelProfile) else ModelProfile.from_manifest(profile)
        )
        return validate_profile(
            manifest,
            host=self._host,
            model_root=self._model_root,
            approved_roots=self._approved_roots,
        )

    # -- lifecycle -------------------------------------------------------

    def load_profile(self, profile: Any) -> ModelProfile:
        """Validate and atomically load a profile. Raises on failure."""
        manifest = (
            profile if isinstance(profile, ModelProfile) else ModelProfile.from_manifest(profile)
        )

        problems = self.validate(manifest)
        if problems:
            self._state = ModelLoadState.FAILED
            self._last_error = "; ".join(problems)
            # Specific error types.
            if any("required adapter" in p or "adapter is missing" in p for p in problems):
                from orion.models.errors import AdapterRequiredError

                raise AdapterRequiredError(self._last_error)
            if any("backend" in p and "not supported" in p for p in problems):
                from orion.models.errors import UnsupportedBackendError

                raise UnsupportedBackendError(self._last_error)
            from orion.models.errors import ProfileValidationError

            raise ProfileValidationError(self._last_error)

        # Register if not already.
        self._profiles.setdefault(manifest.profile_id_or_name, manifest)

        previous_profile = self._active_profile
        previous_state = self._state
        self._state = ModelLoadState.LOADING
        self._last_error = None

        try:
            # Unload current host resources first.
            if self._host.loaded_profile is not None:
                self._host.unload()

            self._host.load(manifest)

            # Health-check inference.
            check = self._host.health_check()
            status_value = getattr(check, "status", None)
            from orion.core.health import HealthStatus

            if status_value is not None and status_value is not HealthStatus.OK:
                raise ModelLoadError(f"health check failed: {getattr(check, 'detail', '')}")

            # Some hosts expose a generate method; run a tiny health prompt if possible.
            try:
                self._host.generate("health check", max_tokens=4)
            except Exception as exc:
                raise ModelLoadError(f"health-check inference failed: {exc}") from exc

            self._active_profile = manifest
            self._state = ModelLoadState.READY
            return manifest
        except Exception as exc:
            # Cleanup partial allocations.
            with contextlib.suppress(Exception):
                self._host.unload()
            self._active_profile = None
            self._state = ModelLoadState.FAILED
            self._last_error = str(exc)
            # Attempt to restore previous profile if load failed after unload.
            if previous_profile is not None and previous_state is ModelLoadState.READY:
                try:
                    self._host.load(previous_profile)
                    check = self._host.health_check()
                    from orion.core.health import HealthStatus

                    if getattr(check, "status", HealthStatus.OK) is HealthStatus.OK:
                        self._active_profile = previous_profile
                        self._state = ModelLoadState.READY
                        self._last_error = str(exc)
                except Exception:
                    self._active_profile = None
                    self._state = ModelLoadState.FAILED
            if isinstance(exc, ModelLoadError):
                raise
            from orion.models.errors import ModelLoadError as _MLE

            raise _MLE(str(exc)) from exc

    def unload(self) -> None:
        self._state = ModelLoadState.UNLOADING
        try:
            self._host.unload()
        finally:
            self._active_profile = None
            self._state = ModelLoadState.UNLOADED
            self._last_error = None

    def reload(self) -> ModelProfile | None:
        if self._active_profile is None:
            return None
        profile = self._active_profile
        self.unload()
        return self.load_profile(profile)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not self.is_ready:
            raise ModelLoadError("model is not ready")
        return self._host.generate(prompt, **kwargs)

    def health_check(self) -> Any:
        return self._host.health_check()

    def runtime_info(self) -> dict[str, Any]:
        return self._host.runtime_info()
