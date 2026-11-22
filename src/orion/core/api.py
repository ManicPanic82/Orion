"""Loopback-only HTTP API for Orion Core.

The API is intentionally small and strict in the first slice: a single
``GET /health`` endpoint with bearer-token authentication, an allowlist of
paths, and a request-size ceiling.

It binds to loopback only. The server is constructed with ``127.0.0.1`` and is
never configured to bind elsewhere in this phase.
"""

from __future__ import annotations

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

__all__ = ["ALLOWED_PATHS", "HEALTH_PATH", "HOST", "MAX_BODY_BYTES", "ApiError", "OrionApiServer"]


HOST = "127.0.0.1"
MAX_BODY_BYTES = 64 * 1024
ALLOWED_PATHS: frozenset[str] = frozenset({"/health"})
HEALTH_PATH = "/health"


class ApiError(Exception):
    """An error that maps onto an HTTP status code."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class OrionApiServer(ThreadingHTTPServer):
    """Threaded HTTP server bound to loopback with Orion's rules applied."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], *, token: str) -> None:
        super().__init__(address, _HealthHandler)
        self._token = token
        self._health: dict[str, Any] = {"status": "unknown", "checks": []}
        self._thread: threading.Thread | None = None
        self._listening = False

    @property
    def token(self) -> str:
        return self._token

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

    server: OrionApiServer  # type: ignore[assignment]

    def do_GET(self) -> None:  # noqa: N802 - http.server convention
        if urlsplit(self.path).path not in ALLOWED_PATHS:
            self._send_json(404, {"error": "not_found"})
            return

        if not self._authorized():
            self._send_json(401, {"error": "unauthorized"})
            return

        if self._content_length() > MAX_BODY_BYTES:
            self._send_json(413, {"error": "payload_too_large"})
            return

        body = json.dumps(self.server._health).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server convention
        self._send_json(405, {"error": "method_not_allowed"})

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

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
