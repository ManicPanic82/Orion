"""Tests for permission gateway and autonomy."""

from __future__ import annotations

import contextlib

from orion.permissions import (
    AutonomyMode,
    PermissionDecision,
    PermissionGateway,
    PermissionGrant,
)


def test_missing_grant_denied_in_independent_mode() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    dec = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.DENY
    assert dec.rationale_code == "missing_grant"


def test_side_effect_requires_approval_in_supervised() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    dec = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.REQUIRE_APPROVAL


def test_grant_allows() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gw.add_grant(PermissionGrant(capability_id="write_file", resource="/tmp/x"))
    dec = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.ALLOW
    assert dec.rationale_code == "grant_matched"


def test_expired_approval_rejected() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(capability_id="write_file", resource="/tmp/x", ttl_seconds=-1)
    # Force expired
    ap.expires_at = "2000-01-01T00:00:00+00:00"
    with contextlib.suppress(ValueError):
        gw.approve(ap.approval_id)
    dec = gw.decide(
        "write_file", "/tmp/x", approval_id=ap.approval_id, idempotency="non_idempotent"
    )
    assert dec.decision is PermissionDecision.DENY


def test_wrong_scope_approval_not_matched() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(capability_id="write_file", resource="/tmp/x", ttl_seconds=300)
    gw.approve(ap.approval_id)
    dec = gw.decide("write_file", "/tmp/y", idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.REQUIRE_APPROVAL


def test_emergency_pause_blocks() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gw.add_grant(PermissionGrant(capability_id="write_file", resource="/tmp/x"))
    gw.pause()
    dec = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.DENY
    assert dec.rationale_code == "emergency_paused"


def test_revocation_takes_effect() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    grant = gw.add_grant(PermissionGrant(capability_id="write_file", resource="/tmp/x"))
    gw.revoke_grant(grant.grant_id)
    dec = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.DENY


def test_read_only_allowed() -> None:
    gw = PermissionGateway(mode=AutonomyMode.RESTRICTED)
    dec = gw.decide("echo", "/tmp/x", idempotency="read_only")
    assert dec.decision is PermissionDecision.ALLOW


def test_gateway_outage_blocks_side_effect() -> None:
    # Executor with no gateway
    from orion.capabilities import CapabilityRegistry, register_mock_capabilities
    from orion.capabilities.executor import CapabilityExecutor
    from orion.tasks.models import TaskStep

    reg = CapabilityRegistry()
    register_mock_capabilities(reg)
    executor = CapabilityExecutor(reg, permission_gateway=None)
    step = TaskStep(capability_id="write_file", input={"path": "/tmp/x"})
    result = executor.execute(step)
    assert result["success"] is False
    assert result["error_code"] == "permission_unavailable"


def test_policy_version_present() -> None:
    gw = PermissionGateway()
    dec = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec.policy_version == "1.0"


def test_approval_one_time_consumption() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(capability_id="write_file", resource="/tmp/x", ttl_seconds=300)
    gw.approve(ap.approval_id)
    dec1 = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec1.decision is PermissionDecision.ALLOW
    dec2 = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec2.decision is PermissionDecision.REQUIRE_APPROVAL


def test_restricted_denies_side_effect() -> None:
    gw = PermissionGateway(mode=AutonomyMode.RESTRICTED)
    dec = gw.decide("write_file", "/tmp/x", idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.DENY
    assert dec.rationale_code == "restricted_mode"


def test_approval_binding_rejects_wrong_capability() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(capability_id="write_file", resource="/tmp/x", ttl_seconds=300)
    gw.approve(ap.approval_id)
    dec = gw.decide("read_file", "/tmp/x", approval_id=ap.approval_id, idempotency="non_idempotent")
    assert dec.decision is PermissionDecision.DENY


def test_approval_binding_rejects_wrong_resource() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(capability_id="write_file", resource="/tmp/x", ttl_seconds=300)
    gw.approve(ap.approval_id)
    dec = gw.decide(
        "write_file", "/tmp/y", approval_id=ap.approval_id, idempotency="non_idempotent"
    )
    assert dec.decision is PermissionDecision.DENY


def test_approval_binding_rejects_wrong_action() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(
        capability_id="write_file", action="execute", resource="/tmp/x", ttl_seconds=300
    )
    gw.approve(ap.approval_id)
    dec = gw.decide(
        "write_file",
        "/tmp/x",
        action="delete",
        approval_id=ap.approval_id,
        idempotency="non_idempotent",
    )
    assert dec.decision is PermissionDecision.DENY


def test_approval_binding_rejects_wrong_args() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(
        capability_id="write_file", resource="/tmp/x", args={"path": "a"}, ttl_seconds=300
    )
    gw.approve(ap.approval_id)
    dec = gw.decide(
        "write_file",
        "/tmp/x",
        args={"path": "b"},
        approval_id=ap.approval_id,
        idempotency="non_idempotent",
    )
    assert dec.decision is PermissionDecision.DENY


def test_approval_binding_accepts_matching_request() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    ap = gw.request_approval(
        capability_id="write_file",
        action="execute",
        resource="/tmp/x",
        args={"path": "a"},
        ttl_seconds=300,
    )
    gw.approve(ap.approval_id)
    dec = gw.decide(
        "write_file",
        "/tmp/x",
        action="execute",
        args={"path": "a"},
        approval_id=ap.approval_id,
        idempotency="non_idempotent",
    )
    assert dec.decision is PermissionDecision.ALLOW


def test_grant_enforces_action_constraint() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gw.add_grant(PermissionGrant(capability_id="write_file", resource="/tmp/x", action="execute"))
    dec_ok = gw.decide("write_file", "/tmp/x", action="execute", idempotency="non_idempotent")
    assert dec_ok.decision is PermissionDecision.ALLOW
    dec_bad = gw.decide("write_file", "/tmp/x", action="read", idempotency="non_idempotent")
    assert dec_bad.decision is PermissionDecision.DENY


def test_grant_enforces_scope_constraint() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gw.add_grant(PermissionGrant(capability_id="write_file", resource="/tmp/x", scope="global"))
    dec_ok = gw.decide("write_file", "/tmp/x", scope="global", idempotency="non_idempotent")
    assert dec_ok.decision is PermissionDecision.ALLOW
    dec_bad = gw.decide("write_file", "/tmp/x", scope="project", idempotency="non_idempotent")
    assert dec_bad.decision is PermissionDecision.DENY

def test_grant_constraints_require_exact_arguments() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gw.add_grant(
        PermissionGrant(
            capability_id="write_file",
            resource="/workspace/*",
            constraints={"required_args": {"mode": "safe"}, "allowed_args": {"format": ["txt", "md"]}},
        )
    )
    allowed = gw.decide(
        "write_file",
        "/workspace/a.txt",
        args={"mode": "safe", "format": "txt"},
        idempotency="non_idempotent",
    )
    denied = gw.decide(
        "write_file",
        "/workspace/a.txt",
        args={"mode": "unsafe", "format": "txt"},
        idempotency="non_idempotent",
    )
    assert allowed.decision is PermissionDecision.ALLOW
    assert denied.decision is PermissionDecision.DENY


def test_unknown_grant_constraint_fails_closed() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gw.add_grant(
        PermissionGrant(
            capability_id="write_file",
            resource="/workspace/a.txt",
            constraints={"allow_anything": True},
        )
    )
    result = gw.decide("write_file", "/workspace/a.txt", idempotency="non_idempotent")
    assert result.decision is PermissionDecision.DENY


def test_path_wildcard_does_not_match_sibling_prefix() -> None:
    gw = PermissionGateway(mode=AutonomyMode.INDEPENDENT)
    gw.add_grant(
        PermissionGrant(capability_id="write_file", resource=r"C:\\Projects\\Trusted*")
    )
    allowed = gw.decide(
        "write_file", r"C:\\Projects\\Trusted\\file.txt", idempotency="non_idempotent"
    )
    denied = gw.decide(
        "write_file", r"C:\\Projects\\TrustedEvil\\file.txt", idempotency="non_idempotent"
    )
    assert allowed.decision is PermissionDecision.ALLOW
    assert denied.decision is PermissionDecision.DENY


def test_approval_is_bound_to_task_and_step() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    approval = gw.request_approval(
        capability_id="write_file",
        resource="/workspace/a.txt",
        task_id="task-1",
        step_id="step-1",
        args={"path": "/workspace/a.txt"},
    )
    gw.approve(approval.approval_id)
    wrong_task = gw.decide(
        "write_file", "/workspace/a.txt",
        task_id="task-2", step_id="step-1",
        args={"path": "/workspace/a.txt"},
        approval_id=approval.approval_id,
        idempotency="non_idempotent",
    )
    assert wrong_task.decision is PermissionDecision.DENY


def test_approval_with_empty_context_is_not_a_wildcard() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    approval = gw.request_approval(capability_id="write_file", resource="/workspace/a.txt")
    gw.approve(approval.approval_id)
    result = gw.decide(
        "write_file", "/workspace/a.txt",
        task_id="task-1", step_id="step-1",
        approval_id=approval.approval_id,
        idempotency="non_idempotent",
    )
    assert result.decision is PermissionDecision.DENY

def test_approval_is_bound_to_exact_step() -> None:
    gw = PermissionGateway(mode=AutonomyMode.SUPERVISED)
    approval = gw.request_approval(
        capability_id="write_file",
        resource="/workspace/a.txt",
        task_id="task-1",
        step_id="step-1",
        args={"path": "/workspace/a.txt"},
    )
    gw.approve(approval.approval_id)
    wrong_step = gw.decide(
        "write_file",
        "/workspace/a.txt",
        task_id="task-1",
        step_id="step-2",
        args={"path": "/workspace/a.txt"},
        approval_id=approval.approval_id,
        idempotency="non_idempotent",
    )
    assert wrong_step.decision is PermissionDecision.DENY
