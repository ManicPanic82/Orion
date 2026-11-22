"""Launch the real Orion Workstation window, capture evidence, and exit.

This is a development aid for Phase 1 acceptance evidence: it proves the window
constructs and paints, and produces a screenshot for the handoff. It is not part
of the application runtime and is never imported by ``orion``.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\smoke_launch.py
    .\\.venv\\Scripts\\python.exe scripts\\smoke_launch.py --offscreen
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="Render with the offscreen Qt platform (no visible window).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "artifacts" / "phase1-launch.png",
        help="Screenshot destination.",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=700,
        help="Time to let the window paint before capture.",
    )
    parser.add_argument(
        "--page",
        default=None,
        help="Navigate to a destination id before capture (for example: settings).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    if os.environ.get("ORION_DATA_DIR"):
        # Honour an explicit data directory so a prepared state (for example a
        # registered startup entry) can be captured as evidence.
        data_dir = Path(os.environ["ORION_DATA_DIR"])
    else:
        data_dir = Path(tempfile.mkdtemp(prefix="orion-smoke-"))
        os.environ["ORION_DATA_DIR"] = str(data_dir)

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from orion.app import create_application

    app, window, _store, _startup = create_application([])
    window.show()

    if args.page:
        window.show_page(args.page)

    result = {"exit_code": 1}

    def capture() -> None:
        pixmap = window.grab()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        saved = pixmap.save(str(args.output), "PNG")

        print(f"platform          : {app.platformName()}")
        print(f"data_dir          : {data_dir}")
        print(f"window_visible    : {window.isVisible()}")
        print(f"window_size       : {window.width()}x{window.height()}")
        print(f"pixmap_size       : {pixmap.width()}x{pixmap.height()}")
        print(f"screenshot_saved  : {saved}")
        print(f"screenshot_path   : {args.output}")
        print(f"screenshot_bytes  : {args.output.stat().st_size if args.output.exists() else 0}")
        result["exit_code"] = 0 if saved else 2
        QApplication.instance().quit()

    QTimer.singleShot(max(args.delay_ms, 50), capture)
    app.exec()
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
