"""Capability registry for Orion."""

from __future__ import annotations

import copy

from orion.capabilities.models import Capability


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.capability_id] = copy.deepcopy(capability)

    def unregister(self, capability_id: str) -> None:
        self._capabilities.pop(capability_id, None)

    def get(self, capability_id: str) -> Capability:
        if capability_id not in self._capabilities:
            raise KeyError(f"capability not found: {capability_id}")
        return copy.deepcopy(self._capabilities[capability_id])

    def list(self) -> list[Capability]:
        return [copy.deepcopy(capability) for capability in self._capabilities.values()]

    def list_ids(self) -> list[str]:
        return list(self._capabilities.keys())

    def is_available(self, capability_id: str) -> bool:
        cap = self._capabilities.get(capability_id)
        return cap is not None and cap.available

    def health(self) -> dict[str, bool]:
        return {cid: cap.available for cid, cap in self._capabilities.items()}
