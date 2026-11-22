"""Tests for delegation."""

from __future__ import annotations

from orion.delegation import DelegationManager, DelegationPayload, DelegationStatus


def test_mock_delegation_lifecycle() -> None:
    mgr = DelegationManager()
    payload = DelegationPayload(objective="do thing", constraints=["no secrets"])
    task = mgr.submit(payload)
    assert task.task_id
    assert mgr.get(task.task_id).status is DelegationStatus.COMPLETED


def test_parent_child_linkage() -> None:
    mgr = DelegationManager()
    parent = mgr.submit(DelegationPayload(objective="parent"), parent_task_id="parent-task")
    child = mgr.submit(DelegationPayload(objective="child"), parent_task_id=parent.task_id)
    assert child.parent_task_id == parent.task_id


def test_provider_timeout_handled() -> None:
    from orion.delegation import MockDelegationProvider

    provider = MockDelegationProvider(timeout=True)
    mgr = DelegationManager(provider)
    task = mgr.submit(DelegationPayload(objective="x"))
    assert task.status is DelegationStatus.TIMED_OUT


def test_provider_failure_handled() -> None:
    from orion.delegation import MockDelegationProvider

    provider = MockDelegationProvider(fail=True)
    mgr = DelegationManager(provider)
    task = mgr.submit(DelegationPayload(objective="x"))
    assert task.status is DelegationStatus.FAILED


def test_result_verification() -> None:
    mgr = DelegationManager()
    task = mgr.submit(DelegationPayload(objective="x"))
    assert mgr.verify_result(task.task_id) is True
