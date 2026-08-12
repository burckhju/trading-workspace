#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repository_root}/backend"

if [[ -x .venv/bin/python ]]; then
  python_bin=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  python_bin="python3"
elif command -v python >/dev/null 2>&1; then
  python_bin="python"
else
  echo "Fehler: Weder python3 noch python wurde gefunden." >&2
  exit 127
fi

if ! "${python_bin}" -c 'import ruff, black, mypy, pytest' >/dev/null 2>&1; then
  if [[ "${python_bin}" != ".venv/bin/python" ]]; then
    echo "Entwicklungsabhängigkeiten fehlen; erstelle backend/.venv ..."
    "${python_bin}" -m venv .venv
    python_bin=".venv/bin/python"
  fi
  "${python_bin}" -m pip install --disable-pip-version-check --requirement requirements-dev.txt
fi

"${python_bin}" -m ruff check app ../tests/unit/backend ../tests/integration/backend
"${python_bin}" -m black --check app ../tests/unit/backend ../tests/integration/backend
"${python_bin}" -m mypy app
PYTHONPATH="${repository_root}/backend:${repository_root}" \
"${python_bin}" -m pytest ../tests/unit/backend ../tests/integration/backend \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-fail-under=85
