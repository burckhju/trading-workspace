#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${repository_root}/docker/compose.yml"

cleanup() {
  docker compose -f "${compose_file}" down --volumes --remove-orphans
}
trap cleanup EXIT

cd "${repository_root}"
docker compose -f "${compose_file}" up --build --wait --wait-timeout 180
cd frontend
npm run e2e
