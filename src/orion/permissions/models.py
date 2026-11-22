"""Permission and autonomy domain models for Orion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

POLICY_VERSION = "1.0"


class AutonomyMode(StrEnum):
    ASSIST = "assist"
    SUPERVISED = "supervised"
    INDEPENDENT = "independent"
    RESTRICTED = "restricted"


class PermissionDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CONSUMED = "consumed"
    REVOKED = "revoked"


@dataclass(slots=True)
class PermissionGrant:
    grant_id: str = field(default_factory=lambda: str(uuid4()))
    capability_id: str = ""
    action: str = ""
    resource: str = ""
    scope: str = ""
    persistent: bool = False
    expires_at: str | None = None
    revoked: bool = False
    constraints: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def is_active(self, now: datetime | None = None) -> bool:
        if self.revoked:
            return False
        if self.expires_at is None:
            return True
        now = now or datetime.now(UTC)
        try:
            return datetime.fromisoformat(self.expires_at) > now
        except ValueError:
            return False

    def matches(
        self,
        capability_id: str,
        resource: str,
        *,
        action: str = "",
        scope: str = "",
        args: dict[str, Any] | None = None,
    ) -> bool:
        if self.capability_id and self.capability_id != capability_id:
            return False
        if self.resource and self.resource not in ("*", ""):
            if self.resource.endswith("*"):
                prefix = self.resource[:-1]
                # A wildcard is a path-prefix grant, not a raw string-prefix
                # grant. Prevent sibling names such as TrustedEvil matching
                # an approved root named Trusted.
                if not resource.startswith(prefix):
                    return False
                if prefix and not prefix.endswith(("/", "\\")):
                    if len(resource) > len(prefix) and resource[len(prefix)] not in ("/", "\\"):
                        return False
            elif self.resource != resource:
                return False
        if self.action and self.action != action:
            return False
        if self.scope and self.scope != scope:
            return False

        # Constraints intentionally support a small, explicit schema.
        # Unknown keys or malformed values fail closed rather than silently
        # weakening a grant.
        constraints = self.constraints or {}
        if not isinstance(constraints, dict):
            return False
        if set(constraints) - {"required_args", "allowed_args"}:
            return False
        request_args = args or {}
        required = constraints.get("required_args", {})
        allowed = constraints.get("allowed_args", {})
        if not isinstance(required, dict) or not isinstance(allowed, dict):
            return False
        if any(key not in request_args or request_args[key] != value for key, value in required.items()):
            return False
        for key, values in allowed.items():
            if not isinstance(values, list) or key not in request_args or request_args[key] not in values:
                return False
        return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "capability_id": self.capability_id,
            "action": self.action,
            "resource": self.resource,
            "scope": self.scope,
            "persistent": self.persistent,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "constraints": dict(self.constraints),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class ApprovalRequest:
    approval_id: str = field(default_factory=lambda: str(uuid4()))
    capability_id: str = ""
    action: str = ""
    resource: str = ""
    scope: str = ""
    task_id: str | None = None
    step_id: str | None = None
    args_hash: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    autonomy_mode: AutonomyMode = AutonomyMode.SUPERVISED
    risk: str = "medium"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str | None = None
    persistent: bool = False
    one_time: bool = True
    approver: str | None = None
    decided_at: str | None = None
    rationale: str = ""

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        now = now or datetime.now(UTC)
        try:
            return datetime.fromisoformat(self.expires_at) <= now
        except ValueError:
            return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "capability_id": self.capability_id,
            "action": self.action,
            "resource": self.resource,
            "scope": self.scope,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "args_hash": self.args_hash,
            "status": self.status.value,
            "autonomy_mode": self.autonomy_mode.value,
            "risk": self.risk,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "persistent": self.persistent,
            "one_time": self.one_time,
            "approver": self.approver,
            "decided_at": self.decided_at,
            "rationale": self.rationale,
        }


@dataclass(slots=True)
class PolicyDecision:
    decision: PermissionDecision
    policy_version: str = POLICY_VERSION
    rationale_code: str = ""
    details: str = ""
    grant_id: str | None = None
    approval_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "policy_version": self.policy_version,
            "rationale_code": self.rationale_code,
            "details": self.details,
            "grant_id": self.grant_id,
            "approval_id": self.approval_id,
        }


@dataclass(slots=True)
class AuditRecord:
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    actor: str = "system"
    capability_id: str = ""
    action: str = ""
    resource: str = ""
    mode: str = ""
    decision: str = ""
    rationale_code: str = ""
    policy_version: str = POLICY_VERSION
    task_id: str | None = None
    step_id: str | None = None
    outcome: str = ""
    redacted_payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "capability_id": self.capability_id,
            "action": self.action,
            "resource": self.resource,
            "mode": self.mode,
            "decision": self.decision,
            "rationale_code": self.rationale_code,
            "policy_version": self.policy_version,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "outcome": self.outcome,
            "redacted_payload": dict(self.redacted_payload),
        }
