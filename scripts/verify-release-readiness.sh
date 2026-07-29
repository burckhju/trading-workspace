#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repository_root}"

failed=0

require_file() {
  if [[ ! -f "$1" ]]; then
    printf 'FEHLT: %s\n' "$1" >&2
    failed=1
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'FEHLT IM PATH: %s\n' "$1" >&2
    failed=1
  fi
}

require_file backend/requirements.txt
require_file backend/requirements-dev.txt
require_file frontend/package-lock.json
require_file frontend/.nvmrc
require_file backend/.python-version

require_command docker
require_command node
require_command npm
require_command python

if [[ "${failed}" -ne 0 ]]; then
  printf '\nRelease-Bereitschaft ist nicht erfüllt.\n' >&2
  exit 1
fi

printf 'Release-Bereitschaft der lokalen Voraussetzungen ist erfüllt.\n'
