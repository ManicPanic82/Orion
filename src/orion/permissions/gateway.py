"""Permission gateway for Orion."""

from __future__ import annotations

import hashlib
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from orion.permissions.models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditRecord,
    AutonomyMode,
    PermissionDecision,
    PermissionGrant,
    PolicyDecision,
)


class PermissionGateway:
    def __init__(
        self, *, mode: AutonomyMode = AutonomyMode.SUPERVISED, paused: bool = False
    ) -> None:
        self._mode = mode
        self._paused = paused
        self._grants: dict[str, PermissionGrant] = {}
        self._approvals: dict[str, ApprovalRequest] = {}
        self._audit: list[AuditRecord] = []
        self._lock = threading.RLock()

    # -- mode / pause ----------------------------------------------------

    @property
    def mode(self) -> AutonomyMode:
        return self._mode

    def set_mode(self, mode: AutonomyMode) -> None:
        with self._lock:
            self._mode = mode

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    # -- grants ----------------------------------------------------------

    def add_grant(self, grant: PermissionGrant) -> PermissionGrant:
        with self._lock:
            self._grants[grant.grant_id] = grant
            return grant

    def revoke_grant(self, grant_id: str) -> bool:
        with self._lock:
            grant = self._grants.get(grant_id)
            if grant is None:
                return False
            grant.revoked = True
            return True

    def list_grants(self) -> list[PermissionGrant]:
        with self._lock:
            return list(self._grants.values())

    def _find_grant(
        self,
        capability_id: str,
        resource: str,
        *,
        action: str = "",
        scope: str = "",
        args: dict[str, Any] | None = None,
    ) -> PermissionGrant | None:
        now = datetime.now(UTC)
        for grant in self._grants.values():
            if grant.is_active(now) and grant.matches(
                capability_id, resource, action=action, scope=scope, args=args
            ):
                return grant
        return None

    @staticmethod
    def _approval_binding_violation(
        approval: ApprovalRequest,
        *,
        capability_id: str,
        resource: str,
        action: str,
        scope: str,
        args_hash: str,
    ) -> bool:
        """Return True when an approval is not bound to this exact request.

        An approval may be used only for the complete request it was issued
        for: same capability, resource, action, scope, and arguments.
        """
        # Every field is exact, including empty values and absent task IDs.
        # An incomplete approval is not a wildcard.
        return (
            approval.capability_id != capability_id
            or approval.resource != resource
            or approval.action != action
            or approval.scope != scope
            or approval.args_hash != args_hash
        )

    # -- approvals -------------------------------------------------------

    def request_approval(
        self,
        *,
        capability_id: str,
        action: str = "",
        resource: str = "",
        scope: str = "",
        task_id: str | None = None,
        step_id: str | None = None,
        args: dict[str, Any] | None = None,
        risk: str = "medium",
        ttl_seconds: int | None = 300,
        persistent: bool = False,
        one_time: bool = True,
    ) -> ApprovalRequest:
        args_hash = hashlib.sha256(repr(sorted((args or {}).items())).encode()).hexdigest()
        expires_at = None
        if ttl_seconds is not None:
            expires_at = (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat()
        approval = ApprovalRequest(
            capability_id=capability_id,
            action=action or capability_id,
            resource=resource,
            scope=scope,
            task_id=task_id,
            step_id=step_id,
            args_hash=args_hash,
            autonomy_mode=self._mode,
            risk=risk,
            expires_at=expires_at,
            persistent=persistent,
            one_time=one_time,
        )
        with self._lock:
            self._approvals[approval.approval_id] = approval
        self._audit_decision(
            capability_id=capability_id,
            action=action or capability_id,
            resource=resource,
            mode=self._mode.value,
            decision=PermissionDecision.REQUIRE_APPROVAL,
            rationale_code="approval_requested",
            task_id=task_id,
            step_id=step_id,
        )
        return approval

    def approve(
        self,
        approval_id: str,
        *,
        approver: str = "user",
        persistent: bool | None = None,
        ttl_seconds: int | None = None,
    ) -> ApprovalRequest:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if approval is None:
                raise KeyError(f"approval not found: {approval_id}")
            if approval.is_expired():
                approval.status = ApprovalStatus.EXPIRED
                raise ValueError("approval expired")
            approval.status = ApprovalStatus.APPROVED
            approval.approver = approver
            approval.decided_at = datetime.now(UTC).isoformat()
            if persistent is not None:
                approval.persistent = persistent
            if ttl_seconds is not None and approval.expires_at is not None:
                approval.expires_at = (
                    datetime.now(UTC) + timedelta(seconds=ttl_seconds)
                ).isoformat()
            # If approved as persistent, create a grant.
            if approval.persistent:
                grant = PermissionGrant(
                    capability_id=approval.capability_id,
                    action=approval.action,
                    resource=approval.resource,
                    scope=approval.scope,
                    persistent=True,
                    expires_at=approval.expires_at,
                )
                self._grants[grant.grant_id] = grant
            return approval

    def deny(
        self, approval_id: str, *, approver: str = "user", rationale: str = "user_denied"
    ) -> ApprovalRequest:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if approval is None:
                raise KeyError(f"approval not found: {approval_id}")
            approval.status = ApprovalStatus.DENIED
            approval.approver = approver
            approval.decided_at = datetime.now(UTC).isoformat()
            approval.rationale = rationale
            return approval

    def revoke_approval(self, approval_id: str) -> bool:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if approval is None:
                return False
            approval.status = ApprovalStatus.REVOKED
            return True

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        approval = self._approvals.get(approval_id)
        if approval is None:
            raise KeyError(f"approval not found: {approval_id}")
        return approval

    def list_approvals(self) -> list[ApprovalRequest]:
        with self._lock:
            return list(self._approvals.values())

    # -- decision --------------------------------------------------------

    def decide(
        self,
        capability_id: str,
        resource: str = "",
        *,
        action: str = "",
        scope: str = "",
        risk: str = "medium",
        task_id: str | None = None,
        step_id: str | None = None,
        args: dict[str, Any] | None = None,
        approval_id: str | None = None,
        idempotency: str = "non_idempotent",
        mode: AutonomyMode | str | None = None,
        autonomy_mode: AutonomyMode | str | None = None,
    ) -> PolicyDecision:
        with self._lock:
            effective_mode = mode if mode is not None else autonomy_mode
            if effective_mode is None:
                effective_mode = self._mode
            if isinstance(effective_mode, str):
                effective_mode = AutonomyMode(effective_mode)
            if self._paused:
                decision = PolicyDecision(
                    PermissionDecision.DENY,
                    rationale_code="emergency_paused",
                    details="emergency pause active",
                )
                self._audit_decision(
                    capability_id,
                    action or capability_id,
                    resource,
                    effective_mode.value,
                    PermissionDecision.DENY,
                    "emergency_paused",
                    task_id,
                    step_id,
                )
                return decision

            effective_action = action or capability_id
            args_hash = hashlib.sha256(repr(sorted((args or {}).items())).encode()).hexdigest()

            # Only unscoped read-only capabilities are allowed by default.
            if idempotency == "read_only" and not scope:
                grant = self._find_grant(
                    capability_id, resource, action=effective_action, scope=scope, args=args
                )
                decision = PolicyDecision(
                    PermissionDecision.ALLOW,
                    rationale_code="read_only_allowed",
                    grant_id=None if grant is None else grant.grant_id,
                )
                self._audit_decision(
                    capability_id,
                    effective_action,
                    resource,
                    effective_mode.value,
                    PermissionDecision.ALLOW,
                    "read_only_allowed",
                    task_id,
                    step_id,
                )
                return decision

            # Check grants.
            grant = self._find_grant(
                capability_id, resource, action=effective_action, scope=scope, args=args
            )
            if grant is not None:
                decision = PolicyDecision(
                    PermissionDecision.ALLOW,
                    rationale_code="grant_matched",
                    grant_id=grant.grant_id,
                )
                self._audit_decision(
                    capability_id,
                    effective_action,
                    resource,
                    effective_mode.value,
                    PermissionDecision.ALLOW,
                    "grant_matched",
                    task_id,
                    step_id,
                )
                return decision

            # Check approval.
            approval = None
            if approval_id is not None:
                approval = self._approvals.get(approval_id)
            else:
                # Find a matching approved, unexpired, unconsumed approval.
                for ap in self._approvals.values():
                    if (
                        ap.capability_id == capability_id
                        and ap.resource == resource
                        and ap.action == effective_action
                        and ap.scope == scope
                        and ap.args_hash == args_hash
                        and ap.task_id == task_id
                        and ap.step_id == step_id
                        and ap.status is ApprovalStatus.APPROVED
                        and not ap.is_expired()
                    ):
                        approval = ap
                        break

            if approval is not None:
                if approval.is_expired():
                    approval.status = ApprovalStatus.EXPIRED
                elif (
                    approval.status is ApprovalStatus.APPROVED
                    and not self._approval_binding_violation(
                        approval,
                        capability_id=capability_id,
                        resource=resource,
                        action=effective_action,
                        scope=scope,
                        args_hash=args_hash,
                    )
                    and approval.task_id == task_id
                    and approval.step_id == step_id
                ):
                    # One-time consumption.
                    if approval.one_time:
                        approval.status = ApprovalStatus.CONSUMED
                    decision = PolicyDecision(
                        PermissionDecision.ALLOW,
                        rationale_code="approval_granted",
                        approval_id=approval.approval_id,
                    )
                    self._audit_decision(
                        capability_id,
                        effective_action,
                        resource,
                        effective_mode.value,
                        PermissionDecision.ALLOW,
                        "approval_granted",
                        task_id,
                        step_id,
                    )
                    return decision

            # No grant/approval.
            if approval_id is not None:
                # Any explicitly supplied but missing, invalid, expired, or
                # mismatched approval is a hard denial, never a fresh prompt.
                decision = PolicyDecision(
                    PermissionDecision.DENY,
                    rationale_code="approval_invalid",
                    approval_id=None if approval is None else approval.approval_id,
                    details="approval not found, expired, unapproved, or not bound to this request",
                )
                self._audit_decision(
                    capability_id,
                    action or capability_id,
                    resource,
                    effective_mode.value,
                    PermissionDecision.DENY,
                    "approval_invalid",
                    task_id,
                    step_id,
                )
                return decision

            # Mode-based.
            if effective_mode is AutonomyMode.RESTRICTED:
                decision = PolicyDecision(
                    PermissionDecision.DENY,
                    rationale_code="restricted_mode",
                    details="restricted mode denies side effects",
                )
            elif effective_mode is AutonomyMode.INDEPENDENT:
                decision = PolicyDecision(
                    PermissionDecision.DENY,
                    rationale_code="missing_grant",
                    details="independent mode requires an explicit grant",
                )
            else:
                decision = PolicyDecision(
                    PermissionDecision.REQUIRE_APPROVAL,
                    rationale_code="approval_required",
                    details="approval required",
                )

            self._audit_decision(
                capability_id,
                action or capability_id,
                resource,
                effective_mode.value,
                decision.decision,
                decision.rationale_code,
                task_id,
                step_id,
            )
            return decision

    # -- audit -----------------------------------------------------------

    def audit_trail(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._audit)

    def _audit_decision(
        self,
        capability_id: str,
        action: str,
        resource: str,
        mode: str,
        decision: PermissionDecision,
        rationale_code: str,
        task_id: str | None,
        step_id: str | None,
    ) -> None:
        record = AuditRecord(
            actor="permission_gateway",
            capability_id=capability_id,
            action=action,
            resource=resource,
            mode=mode,
            decision=decision.value,
            rationale_code=rationale_code,
            task_id=task_id,
            step_id=step_id,
        )
        self._audit.append(record)
