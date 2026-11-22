"""The Orion Core must stay free of any Qt dependency."""

from __future__ import annotations

import subprocess
import sys
import textwrap

_CORE_SOURCE_FILES = [
    "orion.core",
    "orion.core.api",
    "orion.core.events",
    "orion.core.health",
    "orion.core.lifecycle",
    "orion.core.service",
    "orion.core.supervisor",
]


def test_core_subpackage_does_not_import_pyside6() -> None:
    code = textwrap.dedent(
        """
        import importlib
        import sys

        for module in [
            "orion.core",
            "orion.core.api",
            "orion.core.events",
            "orion.core.health",
            "orion.core.lifecycle",
            "orion.core.service",
            "orion.core.supervisor",
        ]:
            importlib.import_module(module)
        print("pyside6" in sys.modules)
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "False"
