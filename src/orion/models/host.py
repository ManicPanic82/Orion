"""Model host adapters and runtime interface for Orion."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from orion.core.health import HealthCheck, HealthStatus
from orion.models.errors import (
    AdapterRequiredError,
    ModelLoadError,
    UnsupportedBackendError,
)
from orion.models.profile import AdapterRequirement, ModelProfile
from orion.models.state import ModelLoadState


@dataclass(slots=True)
class RuntimeDescription:
    """Description of a model runtime/backend."""

    backend: str = "mock"
    available: bool = True
    supports_adapters: bool = True
    supports_quantisation: list[str] = field(default_factory=lambda: ["none"])
    device: str = "cpu"
    mock: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def supports_backend(self, backend: str) -> bool:
        return backend == self.backend or backend == "mock"

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "available": self.available,
            "supports_adapters": self.supports_adapters,
            "supports_quantisation": list(self.supports_quantisation),
            "device": self.device,
            "mock": self.mock,
            "details": dict(self.details),
        }


@runtime_checkable
class ModelHost(Protocol):
    """Protocol every model host adapter must satisfy."""

    is_mock: bool

    def describe_runtime(self) -> RuntimeDescription: ...
    def supports_backend(self, backend: str) -> bool: ...
    def load(self, profile: ModelProfile) -> None: ...
    def unload(self) -> None: ...
    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        cancel_event: threading.Event | None = None,
    ) -> str: ...
    def cancel_generation(self) -> None: ...
    def health_check(self) -> HealthCheck: ...
    def runtime_info(self) -> dict[str, Any]: ...
    @property
    def loaded_profile(self) -> ModelProfile | None: ...
    @property
    def state(self) -> ModelLoadState: ...


# Alias for tests/docs that use a different name.
ModelHostProtocol = ModelHost


class BaseHostAdapter:
    """Shared behaviour for host adapters."""

    def __init__(self) -> None:
        self._profile: ModelProfile | None = None
        self._state = ModelLoadState.UNLOADED
        self._cancel_event = threading.Event()
        self._generating = False

    @property
    def is_mock(self) -> bool:
        return False

    @property
    def loaded_profile(self) -> ModelProfile | None:
        return self._profile

    @property
    def state(self) -> ModelLoadState:
        return self._state

    def supports_backend(self, backend: str) -> bool:
        return self.describe_runtime().supports_backend(backend)

    def cancel_generation(self) -> None:
        self._cancel_event.set()

    def runtime_info(self) -> dict[str, Any]:
        return self.describe_runtime().as_dict()


class MockModelHost(BaseHostAdapter):
    """Explicitly labelled mock model host."""

    def __init__(
        self, *, device: str = "cpu", fail_load: bool = False, fail_health: bool = False
    ) -> None:
        super().__init__()
        self._device = device
        self._fail_load = fail_load
        self._fail_health = fail_health
        self._description = RuntimeDescription(
            backend="mock",
            available=True,
            supports_adapters=True,
            supports_quantisation=["none", "4bit", "8bit"],
            device=device,
            mock=True,
            details={"label": "MOCK"},
        )

    @property
    def is_mock(self) -> bool:  # type: ignore[override]
        return True

    def describe_runtime(self) -> RuntimeDescription:
        return self._description

    def load(self, profile: ModelProfile) -> None:
        if profile.base_model.backend not in ("mock", ""):
            raise UnsupportedBackendError(
                f"mock host does not support backend {profile.base_model.backend!r}"
            )
        if self._fail_load:
            raise ModelLoadError("mock host configured to fail load")
        if (
            profile.adapter.requirement is AdapterRequirement.REQUIRED
            and not profile.adapter.path
            and not profile.adapter.identity
        ):
            raise AdapterRequiredError("required adapter is missing")
        self._state = ModelLoadState.LOADING
        self._profile = profile
        self._state = ModelLoadState.READY

    def unload(self) -> None:
        self._state = ModelLoadState.UNLOADING
        self._profile = None
        self._state = ModelLoadState.UNLOADED

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        max_new_tokens: int | None = None,
        cancel_event: threading.Event | None = None,
        **kwargs: Any,
    ) -> str:
        if self._profile is None or self._state is not ModelLoadState.READY:
            raise ModelLoadError("mock host has no loaded profile")
        event = cancel_event or self._cancel_event
        self._cancel_event = threading.Event()
        if event.is_set():
            raise ModelLoadError("generation cancelled")
        if max_tokens is None:
            max_tokens = kwargs.get("max_tokens", kwargs.get("max_new_tokens", max_new_tokens))
        limit = max_tokens if max_tokens is not None else self._profile.generation_limit
        return (
            f"MOCK_RESPONSE[{self._profile.profile_id_or_name}]: "
            f"{prompt[:200]} (max_tokens={limit})"
        )

    def health_check(self) -> HealthCheck:
        if self._fail_health:
            return HealthCheck(
                name="model", status=HealthStatus.FAILED, detail="mock health check failed"
            )
        if self._profile is None:
            return HealthCheck(name="model", status=HealthStatus.FAILED, detail="no profile loaded")
        return HealthCheck(name="model", status=HealthStatus.OK, detail="mock ready")

    def runtime_info(self) -> dict[str, Any]:
        info = super().runtime_info()
        info["mock"] = True
        info["loaded_profile"] = None if self._profile is None else self._profile.profile_id_or_name
        return info


# Compatibility alias for tests that expect a mock host factory/name.
MockHost = MockModelHost
MockModelHostAdapter = MockModelHost
