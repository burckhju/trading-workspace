#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repository_root}/backend"

python -m ruff check app ../tests/unit/backend ../tests/integration/backend
python -m black --check app ../tests/unit/backend ../tests/integration/backend
python -m mypy app
python -m pytest ../tests/unit/backend ../tests/integration/backend \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-fail-under=85
