"""Allow ``python -m orion`` to launch Orion Workstation."""

from __future__ import annotations

import sys

from orion.app import main

if __name__ == "__main__":
    sys.exit(main())
