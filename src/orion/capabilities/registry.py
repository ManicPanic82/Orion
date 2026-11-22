"""Capability registry for Orion."""

from __future__ import annotations

import copy

from orion.capabilities.models import Capability


def _capability_snapshot(capability: Capability) -> Capability:
    """Copy mutable policy metadata while retaining the trusted handler callable."""
    snapshot = copy.copy(capability)
    snapshot.input_schema = copy.deepcopy(capability.input_schema)
    snapshot.output_schema = copy.deepcopy(capability.output_schema)
    snapshot.required_scopes = list(capability.required_scopes)
    return snapshot


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.capability_id] = _capability_snapshot(capability)

    def unregister(self, capability_id: str) -> None:
        self._capabilities.pop(capability_id, None)

    def get(self, capability_id: str) -> Capability:
        if capability_id not in self._capabilities:
            raise KeyError(f"capability not found: {capability_id}")
        return _capability_snapshot(self._capabilities[capability_id])

    def list(self) -> list[Capability]:
        return [_capability_snapshot(capability) for capability in self._capabilities.values()]

    def list_ids(self) -> list[str]:
        return list(self._capabilities.keys())

    def is_available(self, capability_id: str) -> bool:
        cap = self._capabilities.get(capability_id)
        return cap is not None and cap.available

    def health(self) -> dict[str, bool]:
        return {cid: cap.available for cid, cap in self._capabilities.items()}
