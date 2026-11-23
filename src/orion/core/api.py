"""Loopback-only HTTP API for Orion Core.

The API serves the health endpoint and the objective pipeline: submit
objectives through the resident agent and run or cancel tasks. It binds to
loopback only and is authenticated with a bearer token.
"""

from __future__ import annotations

import hmac
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:  # pragma: no cover - typing only
    from orion.core.service import OrionCore

__all__ = [
    "ALLOWED_PATHS",
    "HEALTH_PATH",
    "HOST",
    "MAX_BODY_BYTES",
    "OBJECTIVES_PATH",
    "ApiError",
    "OrionApiServer",
]


HOST = "127.0.0.1"
MAX_BODY_BYTES = 64 * 1024
HEALTH_PATH = "/health"
OBJECTIVES_PATH = "/objectives"
ALLOWED_PATHS: frozenset[str] = frozenset(
    {
        HEALTH_PATH,
        OBJECTIVES_PATH,
        "/objectives/{id}/tasks",
        "/objectives/{id}/run",
        "/objectives/{id}/cancel",
    }
)

_OBJECTIVE_TASKS_RE = re.compile(r"/objectives/([^/]+)/tasks")
_OBJECTIVE_RUN_RE = re.compile(r"/objectives/([^/]+)/run")
_OBJECTIVE_CANCEL_RE = re.compile(r"/objectives/([^/]+)/cancel")


class ApiError(Exception):
    """Error that maps onto an HTTP status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class OrionApiServer(ThreadingHTTPServer):
    """Threaded HTTP server bound to loopback with Orion's rules applied."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], *, token: str, core: OrionCore | None = None):
        super().__init__(address, _HealthHandler)
        self._token = token
        self._core = core
        self._health: dict[str, Any] = {"status": "unknown", "checks": []}
        self._thread: threading.Thread | None = None
        self._listening = False

    @property
    def token(self) -> str:
        return self._token

    @property
    def core(self) -> OrionCore | None:
        return self._core

    @property
    def host(self) -> str:
        return self.server_address[0]

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    @property
    def listening(self) -> bool:
        return self._listening

    def set_health(self, payload: dict[str, Any]) -> None:
        """Publish the latest health payload to every connected client."""
        self._health = payload

    def start(self) -> None:
        """Serve requests in a background thread until :meth:`stop`."""
        self._listening = True
        self._thread = threading.Thread(
            target=self.serve_forever, name="orion-core-api", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop serving and wait briefly for in-flight requests to drain."""
        self.shutdown()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._listening = False


class _HealthHandler(BaseHTTPRequestHandler):
    """Request handler enforcing Orion API rules."""

    server: OrionApiServer

    def do_GET(self) -> None:  # noqa: N802 - http.server convention
        path = urlsplit(self.path).path
        if not self._authorized():
            self._send_json(401, {"error": "unauthorized"})
            return
        if self._content_length() > MAX_BODY_BYTES:
            self._send_json(413, {"error": "payload_too_large"})
            return
        if path == HEALTH_PATH:
            self._send_json(200, self.server._health)
            return
        match = _OBJECTIVE_TASKS_RE.fullmatch(path)
        if match is None:
            self._send_json(404, {"error": "not_found"})
            return
        core = self.server.core
        if core is None:
            self._send_json(503, {"error": "core_not_available"})
            return
        self._send_json(200, {"tasks": core.objective_tasks_payload(match.group(1))})

    def do_POST(self) -> None:  # noqa: N802 - http.server convention
        path = urlsplit(self.path).path
        allowed = (
            path == OBJECTIVES_PATH
            or _OBJECTIVE_RUN_RE.fullmatch(path) is not None
            or (_OBJECTIVE_CANCEL_RE.fullmatch(path) is not None)
        )
        if not allowed:
            self._send_json(404, {"error": "not_found"})
            return
        if not self._authorized():
            self._send_json(401, {"error": "unauthorized"})
            return
        if self._content_length() > MAX_BODY_BYTES:
            self._send_json(413, {"error": "payload_too_large"})
            return
        core = self.server.core
        if core is None:
            self._send_json(503, {"error": "core_not_available"})
            return
        body = self._read_json_body()
        if path == OBJECTIVES_PATH:
            request = body.get("request")
            if not isinstance(request, str) or not request.strip():
                self._send_json(400, {"error": "request must be a non-empty string"})
                return
            task = core.submit_objective(
                request, request_id=body.get("request_id") if isinstance(body, dict) else None
            )
            self._send_json(200, core.task_payload(task))
            return
        match = _OBJECTIVE_RUN_RE.fullmatch(path) or _OBJECTIVE_CANCEL_RE.fullmatch(path)
        assert match is not None
        action = "run" if _OBJECTIVE_RUN_RE.fullmatch(path) else "cancel"
        target = body.get("task_id") or match.group(1)
        if not isinstance(target, str) or not target:
            self._send_json(400, {"error": "task_id must be a non-empty string"})
            return
        task = core.run_task(target) if action == "run" else core.cancel_task(target)
        self._send_json(200, core.task_payload(task))

    def do_PUT(self) -> None:  # noqa: N802 - http.server convention
        self._send_json(405, {"error": "method_not_allowed"})

    def do_DELETE(self) -> None:  # noqa: N802 - http.server convention
        self._send_json(405, {"error": "method_not_allowed"})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        return

    # -- helpers ------------------------------------------------------------

    def _content_length(self) -> int:
        raw = self.headers.get("Content-Length")
        if raw is None:
            return 0
        try:
            return int(raw)
        except ValueError:
            return MAX_BODY_BYTES + 1

    def _authorized(self) -> bool:
        expected = f"Bearer {self.server.token}"
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(expected, supplied)

    def _read_json_body(self) -> dict[str, Any]:
        try:
            raw = self.rfile.read(self._content_length()) if self._content_length() else b""
            if not raw:
                return {}
            parsed = json.loads(raw.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
