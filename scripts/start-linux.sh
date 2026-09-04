#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/docker/.env"
ENV_EXAMPLE="$ROOT_DIR/docker/.env.example"
COMPOSE_FILE="$ROOT_DIR/docker/compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required and was not found in PATH" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (docker compose ...)" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE from template."
  echo "Review database password and optional EODHD/Telegram settings before enabling monitoring."
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up --build -d

echo "Trading Workspace started."
echo "Frontend: http://localhost:8080"
echo "Backend:  http://localhost:8000"
echo "Health:   http://localhost:8000/health"
echo "Status:   docker compose --env-file docker/.env -f docker/compose.yml ps"
echo "Logs:     docker compose --env-file docker/.env -f docker/compose.yml logs -f backend"
