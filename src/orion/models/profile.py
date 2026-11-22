"""Versioned Model Profile schema for Orion.

A Model Profile is one atomic user-facing configuration: base model, adapter
state, tokenizer, backend, device preference, quantisation, and limits.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from orion.models.errors import ProfileValidationError

SCHEMA_VERSION = 1


class AdapterRequirement(StrEnum):
    """Whether a profile uses an adapter and whether it is mandatory."""

    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


# Aliases for callers/tests that use different vocabulary.
AdapterState = AdapterRequirement
AdapterMode = AdapterRequirement
AdapterStatus = AdapterRequirement


def _normalise_adapter_requirement(value: Any) -> AdapterRequirement:
    if isinstance(value, AdapterRequirement):
        return value
    if isinstance(value, bool):
        return AdapterRequirement.REQUIRED if value else AdapterRequirement.NONE
    if value is None:
        return AdapterRequirement.NONE
    text = str(value).strip().lower()
    if text in {"", "none", "no", "false", "0", "disabled"}:
        return AdapterRequirement.NONE
    if text in {"optional", "opt", "maybe"}:
        return AdapterRequirement.OPTIONAL
    if text in {"required", "mandatory", "yes", "true", "1", "enabled"}:
        return AdapterRequirement.REQUIRED
    try:
        return AdapterRequirement(text)
    except ValueError as exc:
        raise ProfileValidationError(f"unknown adapter requirement: {value!r}") from exc


@dataclass(slots=True)
class BaseModelRef:
    """Reference to an immutable base model artifact."""

    identity: str = ""
    revision: str = ""
    path: str | Path = ""
    backend: str = "mock"

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "revision": self.revision,
            "path": str(self.path) if self.path != "" else "",
            "backend": self.backend,
        }

    @classmethod
    def from_value(
        cls, value: Any, *, revision: str = "", path: Any = "", backend: str = "mock"
    ) -> BaseModelRef:
        if isinstance(value, BaseModelRef):
            if revision and not value.revision:
                value.revision = revision
            if path not in ("", None) and not value.path:
                value.path = path
            if backend and value.backend == "mock" and backend != "mock":
                value.backend = backend
            return value
        if isinstance(value, Mapping):
            return cls(
                identity=str(value.get("identity") or value.get("id") or value.get("name") or ""),
                revision=str(value.get("revision") or value.get("rev") or revision or ""),
                path=value.get("path") or value.get("root") or path or "",
                backend=str(value.get("backend") or value.get("runtime") or backend or "mock"),
            )
        if isinstance(value, str):
            return cls(identity=value, revision=revision, path=path, backend=backend)
        if value is None:
            return cls(identity="", revision=revision, path=path, backend=backend)
        return cls(identity=str(value), revision=revision, path=path, backend=backend)


@dataclass(slots=True)
class AdapterRef:
    """Reference to an optional/required adapter artifact."""

    requirement: AdapterRequirement = AdapterRequirement.NONE
    identity: str = ""
    revision: str = ""
    path: str | Path = ""
    type: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "requirement": self.requirement.value,
            "identity": self.identity,
            "revision": self.revision,
            "path": str(self.path) if self.path != "" else "",
            "type": self.type,
        }

    @classmethod
    def from_value(
        cls,
        value: Any,
        *,
        requirement: Any = None,
        path: Any = "",
        type: str = "",
        revision: str = "",
        identity: str = "",
    ) -> AdapterRef:
        if isinstance(value, AdapterRef):
            if requirement is not None:
                value.requirement = _normalise_adapter_requirement(requirement)
            if path not in ("", None) and not value.path:
                value.path = path
            if type and not value.type:
                value.type = type
            if revision and not value.revision:
                value.revision = revision
            if identity and not value.identity:
                value.identity = identity
            return value
        if isinstance(value, Mapping):
            return cls(
                requirement=_normalise_adapter_requirement(
                    value.get("requirement", value.get("state", value.get("mode", requirement)))
                ),
                identity=str(
                    value.get("identity") or value.get("id") or value.get("name") or identity or ""
                ),
                revision=str(value.get("revision") or value.get("rev") or revision or ""),
                path=value.get("path") or value.get("root") or path or "",
                type=str(value.get("type") or value.get("format") or type or ""),
            )
        if isinstance(value, bool):
            return cls(
                requirement=_normalise_adapter_requirement(value),
                path=path,
                type=type,
                revision=revision,
                identity=identity,
            )
        if isinstance(value, str):
            # A bare string is treated as a path when a requirement is supplied,
            # otherwise as an adapter identity/state token.
            if requirement is not None or path not in ("", None):
                return cls(
                    requirement=_normalise_adapter_requirement(requirement),
                    path=value or path,
                    type=type,
                    revision=revision,
                    identity=identity,
                )
            return cls(
                requirement=_normalise_adapter_requirement(value),
                path=path,
                type=type,
                revision=revision,
                identity=identity,
            )
        if value is None:
            return cls(
                requirement=_normalise_adapter_requirement(requirement),
                path=path,
                type=type,
                revision=revision,
                identity=identity,
            )
        return cls(
            requirement=_normalise_adapter_requirement(requirement),
            path=path,
            type=type,
            revision=revision,
            identity=str(value),
        )


@dataclass(slots=True)
class TokenizerRef:
    """Reference to a tokenizer."""

    identity: str = ""
    revision: str = ""
    path: str | Path = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "revision": self.revision,
            "path": str(self.path) if self.path != "" else "",
        }

    @classmethod
    def from_value(
        cls, value: Any, *, revision: str = "", path: Any = "", identity: str = ""
    ) -> TokenizerRef:
        if isinstance(value, TokenizerRef):
            if revision and not value.revision:
                value.revision = revision
            if path not in ("", None) and not value.path:
                value.path = path
            if identity and not value.identity:
                value.identity = identity
            return value
        if isinstance(value, Mapping):
            return cls(
                identity=str(
                    value.get("identity") or value.get("id") or value.get("name") or identity or ""
                ),
                revision=str(value.get("revision") or value.get("rev") or revision or ""),
                path=value.get("path") or value.get("root") or path or "",
            )
        if isinstance(value, str):
            return cls(identity=value, revision=revision, path=path)
        if value is None:
            return cls(identity=identity, revision=revision, path=path)
        return cls(identity=str(value), revision=revision, path=path)


class ModelProfile:
    """A versioned, validated Model Profile manifest.

    The constructor accepts a broad set of alias keyword arguments so that
    callers using either flat or nested manifest styles can construct a profile.
    """

    def __init__(self, **kwargs: Any) -> None:
        # Collect aliases.
        data = dict(kwargs)

        self.schema_version = int(
            data.pop("schema_version", data.pop("manifest_version", SCHEMA_VERSION))
            or SCHEMA_VERSION
        )

        self.profile_id = str(
            data.pop(
                "profile_id", data.pop("id", data.pop("profile", data.pop("profile_name", "")))
            )
            or ""
        )
        self.name = str(data.pop("name", data.pop("title", data.pop("profile_name", ""))) or "")
        if not self.name and self.profile_id:
            self.name = self.profile_id

        self.version = str(
            data.pop("version", data.pop("profile_version", data.pop("version_id", "1"))) or "1"
        )
        self.description = str(data.pop("description", "") or "")

        base_revision = str(
            data.pop("base_revision", data.pop("base_model_revision", data.pop("base_rev", "")))
            or ""
        )
        base_path = data.pop(
            "base_path",
            data.pop(
                "base_model_path",
                data.pop("model_path", data.pop("base_root", data.pop("path", ""))),
            ),
        )
        base_backend = str(
            data.pop("backend", data.pop("runtime", data.pop("backend_id", "mock"))) or "mock"
        )
        base_value = data.pop("base_model", data.pop("base", data.pop("base_model_ref", None)))
        if base_value is None:
            # Allow flat construction where identity is passed separately.
            base_identity = str(
                data.pop(
                    "base_identity",
                    data.pop(
                        "base_model_id", data.pop("base_model_identity", data.pop("base_name", ""))
                    ),
                )
                or ""
            )
            base_value = base_identity
        else:
            # If identity also provided flat, keep it for revision/path merging.
            flat_identity = data.pop(
                "base_identity",
                data.pop(
                    "base_model_id", data.pop("base_model_identity", data.pop("base_name", None))
                ),
            )
            if flat_identity is not None and isinstance(base_value, str) and not base_value:
                base_value = flat_identity
        self.base_model = BaseModelRef.from_value(
            base_value, revision=base_revision, path=base_path, backend=base_backend
        )

        # If backend explicitly provided at profile level, propagate.
        if "backend" in kwargs or "runtime" in kwargs:
            self.base_model.backend = base_backend

        adapter_requirement_value = None
        adapter_value = data.pop("adapter_ref", None)
        if adapter_value is None:
            adapter_value = data.pop("adapter_model", None)

        if "adapter" in data and isinstance(data.get("adapter"), Mapping):
            adapter_value = data.pop("adapter")
        else:
            for key in (
                "adapter_requirement",
                "adapter_state",
                "adapter",
                "adapter_mode",
                "adapter_kind",
                "required_adapter",
            ):
                if key in data:
                    adapter_requirement_value = data.pop(key)
                    break

        adapter_path = data.pop("adapter_path", None)
        if adapter_path is None:
            adapter_path = data.pop("adapter_model_path", None)
        if adapter_path is None:
            adapter_path = data.pop("adapter_root", "")
        adapter_type = str(data.pop("adapter_type", data.pop("adapter_format", "")) or "")
        adapter_revision = str(data.pop("adapter_revision", "") or "")
        adapter_identity = data.pop("adapter_identity", None)
        if adapter_identity is None:
            adapter_identity = data.pop("adapter_id", None)
        if adapter_identity is None:
            adapter_identity = data.pop("adapter_name", "")
        adapter_identity = str(adapter_identity or "")
        if adapter_value is not None:
            # already popped
            pass
        if adapter_value is not None:
            self.adapter = AdapterRef.from_value(
                adapter_value,
                requirement=adapter_requirement_value,
                path=adapter_path,
                type=adapter_type,
                revision=adapter_revision,
                identity=adapter_identity,
            )
        else:
            self.adapter = AdapterRef.from_value(
                None,
                requirement=adapter_requirement_value,
                path=adapter_path,
                type=adapter_type,
                revision=adapter_revision,
                identity=adapter_identity,
            )

        # Ensure requirement reflects explicit required_adapter bool if given.
        if "required_adapter" in kwargs and isinstance(kwargs.get("required_adapter"), bool):
            self.adapter.requirement = (
                AdapterRequirement.REQUIRED
                if kwargs["required_adapter"]
                else AdapterRequirement.NONE
            )

        tokenizer_revision = str(data.pop("tokenizer_revision", "") or "")
        tokenizer_path = data.pop("tokenizer_path", data.pop("tokenizer_root", ""))
        tokenizer_value = data.pop(
            "tokenizer", data.pop("tokenizer_ref", data.pop("tokenizer_id", None))
        )
        if tokenizer_value is None:
            tokenizer_identity = str(
                data.pop("tokenizer_name", data.pop("tokenizer_identity", "")) or ""
            )
            tokenizer_value = tokenizer_identity
        self.tokenizer = TokenizerRef.from_value(
            tokenizer_value, revision=tokenizer_revision, path=tokenizer_path
        )

        self.device_preference = str(
            data.pop("device_preference", data.pop("device", data.pop("device_target", "auto")))
            or "auto"
        )
        self.quantisation = str(
            data.pop("quantisation", data.pop("quantization", "none")) or "none"
        )
        self.context_limit = int(
            data.pop(
                "context_limit",
                data.pop("context", data.pop("context_length", data.pop("max_context", 4096))),
            )
            or 4096
        )
        self.generation_limit = int(
            data.pop(
                "generation_limit",
                data.pop("max_tokens", data.pop("max_new_tokens", data.pop("generation", 512))),
            )
            or 512
        )

        compatibility = data.pop("compatibility", data.pop("compatibility_metadata", {}))
        self.compatibility = (
            dict(compatibility)
            if isinstance(compatibility, Mapping)
            else ({} if compatibility is None else {"value": compatibility})
        )

        self.created_at = str(data.pop("created_at", "") or "")
        self.updated_at = str(data.pop("updated_at", "") or "")
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()

        self.metadata = dict(data.pop("metadata", {}) or {})
        # Preserve any unexpected fields rather than dropping them.
        for key, value in data.items():
            setattr(self, key, value)

        # Convenience aliases.
        self.adapter_state = self.adapter.requirement
        self.adapter_path = self.adapter.path
        self.adapter_type = self.adapter.type
        self.adapter_revision = self.adapter.revision
        self.base_identity = self.base_model.identity
        self.base_revision = self.base_model.revision
        self.base_path = self.base_model.path
        self.backend = self.base_model.backend

    # -- derived ---------------------------------------------------------

    @property
    def adapter_required(self) -> bool:
        return self.adapter.requirement is AdapterRequirement.REQUIRED

    @property
    def adapter_optional(self) -> bool:
        return self.adapter.requirement is AdapterRequirement.OPTIONAL

    @property
    def has_adapter(self) -> bool:
        return self.adapter.requirement is not AdapterRequirement.NONE

    @property
    def profile_id_or_name(self) -> str:
        return self.profile_id or self.name

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "base_model": self.base_model.as_dict(),
            "adapter": self.adapter.as_dict(),
            "tokenizer": self.tokenizer.as_dict(),
            "device_preference": self.device_preference,
            "quantisation": self.quantisation,
            "context_limit": self.context_limit,
            "generation_limit": self.generation_limit,
            "compatibility": dict(self.compatibility),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    def to_manifest(self) -> dict[str, Any]:
        return self.to_dict()

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModelProfile:
        if not isinstance(data, Mapping):
            raise ProfileValidationError("profile manifest must be a mapping")
        return cls(**dict(data))

    @classmethod
    def from_json(cls, text: str) -> ModelProfile:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProfileValidationError(f"invalid profile JSON: {exc}") from exc
        if not isinstance(data, Mapping):
            raise ProfileValidationError("profile JSON must contain an object")
        return cls.from_dict(data)

    @classmethod
    def from_manifest(cls, manifest: Any) -> ModelProfile:
        if isinstance(manifest, ModelProfile):
            return manifest
        if isinstance(manifest, Mapping):
            return cls.from_dict(manifest)
        if isinstance(manifest, str):
            return cls.from_json(manifest)
        raise ProfileValidationError(f"unsupported manifest type: {type(manifest)!r}")

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.profile_id and not self.name:
            problems.append("profile_id or name is required")
        if self.schema_version != SCHEMA_VERSION:
            problems.append(f"schema_version {self.schema_version} != {SCHEMA_VERSION}")
        if self.context_limit <= 0:
            problems.append("context_limit must be positive")
        if self.generation_limit <= 0:
            problems.append("generation_limit must be positive")
        if (
            self.adapter.requirement is AdapterRequirement.REQUIRED
            and not self.adapter.path
            and not self.adapter.identity
        ):
            problems.append("required adapter is missing path/identity")
        return problems

    def __repr__(self) -> str:
        return (
            f"ModelProfile(profile_id={self.profile_id!r}, name={self.name!r}, "
            f"backend={self.base_model.backend!r}, adapter={self.adapter.requirement.value!r})"
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ModelProfile):
            return False
        return self.to_dict() == other.to_dict()
