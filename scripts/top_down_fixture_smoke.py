#!/usr/bin/env python3
"""Run the deterministic Sprint-5 top-down smoke test without live credentials.

This is an operator convenience wrapper around the integration fixture. It proves
that provider-shaped daily data can flow through FT-006, MarketContext 1.0,
RelativeStrength 1.0 and TOP_DOWN_CANDIDATE 1.0. It does not replace the live
EODHD smoke test.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/integration/backend/test_top_down_fixture_e2e.py",
    ]
    env = os.environ.copy()
    backend = str(root / "backend")
    env["PYTHONPATH"] = backend + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return subprocess.call(command, cwd=root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
