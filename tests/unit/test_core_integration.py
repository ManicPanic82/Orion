"""End-to-end integration: Orion Core services through the API and agent.

Covers the user milestone: Objective -> plan -> execute through the permission
gateway -> durable task/experience records, plus durability across restart.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from orion.core.api import HOST
from orion.core.service import OrionCore
from orion.core.services import build_default_services
from orion.permissions.models import AutonomyMode, PermissionDecision

_TOKEN = "e2e-token"


def _request(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_TOKEN}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_core_services_health_and_objective_flow(tmp_path: Path) -> None:
    db = tmp_path / "orion.db"
    services = build_default_services(db_path=db, autonomy=AutonomyMode.INDEPENDENT)
    core = OrionCore(token=_TOKEN, host=HOST, port=0, services=services)
    core.start()
    try:
        status, health = _request("GET", f"http://{HOST}:{core.api.port}/health", _TOKEN)
        assert status == 200
        assert health["status"] == "ok"
        names = {check["name"] for check in health["checks"]}
        assert {"agent", "tasks", "permissions", "experience", "model"} <= names

        # Permission gateway is wired and denies a write_file without an
        # approval or grant in INDEPENDENT mode.
        decision = services.permission_gateway.decide(
            "write_file", "vault/item", idempotency="non_idempotent"
        )
        assert decision.decision is PermissionDecision.DENY

        # Objective flow through the API: the resident agent creates and runs
        # the task; the read-only echo capability runs through the executor.
        status, payload = _request(
            "POST", f"http://{HOST}:{core.api.port}/objectives", {"request": "echo hello"}
        )
        assert status == 200
        assert payload["state"] in {"created", "planned", "running", "completed"}
        task = services.task_manager.get_task(payload["task_id"])
        finished = core.run_task(task.task_id)
        assert finished.state.value == "completed"
        assert any(step.outcome == "success" for step in finished.steps)

        # The experience recorder captured the episode (Phase 7).
        assert len(services.experience_recorder.list_experiences()) >= 1

        # Task listing via the API works.
        status, tasks_payload = _request(
            "GET",
            f"http://{HOST}:{core.api.port}/objectives/{payload['task_id']}/tasks",
        )
        assert status == 200
        assert any(t["task_id"] == payload["task_id"] for t in tasks_payload["tasks"])

        # Restart: the durable task engine and experience recorder survive.
        core.stop()
        core2 = OrionCore(
            token=_TOKEN,
            host=HOST,
            port=0,
            services=build_default_services(db_path=db, autonomy=AutonomyMode.INDEPENDENT),
        )
        core2.start()
        try:
            assert payload["task_id"] in {
                t.task_id for t in core2.services.task_manager.list_tasks()
            }
            assert len(core2.services.experience_recorder.list_experiences()) >= 1
            status, _ = _request("GET", f"http://{HOST}:{core2.api.port}/health", _TOKEN)
            assert status == 200
        finally:
            core2.stop()
    finally:
        core.stop()
