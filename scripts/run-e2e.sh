#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${repository_root}/docker/compose.yml"

# Keep local E2E disposable resources isolated from the persistent runtime stack.
compose_project="trading-workspace-e2e"
postgres_port="${E2E_POSTGRES_PORT:-15432}"
backend_port="${E2E_BACKEND_PORT:-18000}"
frontend_port="${E2E_FRONTEND_PORT:-18080}"
playwright_base_url="${E2E_PLAYWRIGHT_BASE_URL:-http://127.0.0.1:${frontend_port}}"
vite_api_base_url="${E2E_VITE_API_BASE_URL:-http://localhost:${frontend_port}/api}"

compose() {
  POSTGRES_PORT="${postgres_port}" \
  BACKEND_PORT="${backend_port}" \
  FRONTEND_PORT="${frontend_port}" \
  VITE_API_BASE_URL="${vite_api_base_url}" \
    docker compose \
      --project-name "${compose_project}" \
      -f "${compose_file}" \
      "$@"
}

cleanup() {
  compose down --volumes --remove-orphans
}
trap cleanup EXIT

cd "${repository_root}"
compose up --build --wait --wait-timeout 180

PLAYWRIGHT_BASE_URL="${playwright_base_url}" \
NODE_PATH="${repository_root}/frontend/node_modules" \
  npm --prefix "${repository_root}/frontend" run e2e
