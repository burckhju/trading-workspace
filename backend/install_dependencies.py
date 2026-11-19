"""Install the complete production requirements with bounded download retries."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--no-cache-dir",
        "--index-url",
        "https://pypi.org/simple",
        "--timeout",
        "120",
        "--retries",
        "5",
        "--requirement",
        str(Path(__file__).resolve().with_name("requirements.txt")),
    ]
    attempt = 1
    while True:
        # Keep pip's actual diagnostics visible in the private build log.
        result = subprocess.run(command, check=False)
        if result.returncode <= 0 or attempt == MAX_ATTEMPTS:
            # A terminated pip process must stop the build, not trigger another attempt.
            return 128 - result.returncode if result.returncode < 0 else result.returncode
        print(
            f"Dependency installation attempt {attempt}/{MAX_ATTEMPTS} failed "
            f"with exit code {result.returncode}; retrying in {RETRY_DELAY_SECONDS}s.",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(RETRY_DELAY_SECONDS)
        attempt += 1


if __name__ == "__main__":
    raise SystemExit(main())
