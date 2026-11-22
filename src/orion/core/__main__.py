"""Standalone Orion Core process entry point.

Phase 2 slice 1: the Core can run without any UI. This entry starts the Core,
serves its loopback API, and keeps running until a stop is requested (SIGTERM,
SIGINT, or an injected stop).

It deliberately owns no tray and no Qt: the Core is UI-independent by construction.
"""

from __future__ import annotations

import argparse
import signal
import threading

from orion.core.service import OrionCore

__all__ = ["main"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="orion-core", description="Orion Core background process."
    )
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    core = OrionCore(version=args.version, host=args.host, port=args.port)
    stop_event = threading.Event()

    def _request_stop(*_args: object) -> None:
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _request_stop)
        except (ValueError, OSError):  # pragma: no cover - non-main-thread hosts
            break

    core.start()
    try:
        stop_event.wait(timeout=30.0)
    finally:
        core.stop()

    return 0
