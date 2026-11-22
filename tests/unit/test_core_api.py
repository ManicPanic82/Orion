"""Loopback-only Orion Core API behaviour."""

from __future__ import annotations

import json

import pytest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from orion.core.api import HOST, MAX_BODY_BYTES, OrionApiServer

TOKEN = "orion-test-token"


@pytest.fixture()
def server() -> OrionApiServer:
    instance = OrionApiServer(("127.0.0.1", 0), token=TOKEN)
    instance.start()
    yield instance
    instance.stop()


def _get(
    server: OrionApiServer, path: str = "/health", token: str = TOKEN
) -> tuple[int, dict[str, object]]:
    headers = {"Accept": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"http://{server.host}:{server.port}{path}", headers=headers, method="GET")
    try:
        with urlopen(request, timeout=5.0) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return int(error.code), json.loads(error.read().decode("utf-8"))


def test_server_binds_to_loopback(server: OrionApiServer) -> None:
    assert server.host == HOST
    assert server.port > 0


def test_health_without_token_is_unauthorized(server: OrionApiServer) -> None:
    status, payload = _get(server, token=None)

    assert status == 401
    assert payload.get("error") == "unauthorized"


def test_health_with_wrong_token_is_unauthorized(server: OrionApiServer) -> None:
    status, _payload = _get(server, token="wrong-token")

    assert status == 401


def test_health_with_token_returns_the_published_payload(server: OrionApiServer) -> None:
    server.set_health(
        {"status": "ok", "checks": [{"name": "process", "status": "ok"}], "state": "ready"}
    )
    status, payload = _get(server)

    assert status == 200
    assert payload["status"] == "ok"


def test_unknown_path_is_not_found(server: OrionApiServer) -> None:
    status, payload = _get(server, path="/nope")

    assert status == 404
    assert payload.get("error") == "not_found"


def test_max_body_bytes_is_bounded() -> None:
    assert MAX_BODY_BYTES > 0
