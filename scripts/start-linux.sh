#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/docker/.env"
ENV_EXAMPLE="$ROOT_DIR/docker/.env.example"
COMPOSE_FILE="$ROOT_DIR/docker/compose.yml"
DEFAULT_STUTTGART_DATA_DIR="$ROOT_DIR/docker/stuttgart-data"

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
  echo "Edit docker/.env before starting: replace the database password and configure optional EODHD/Telegram settings."
  echo "Then run: bash scripts/start-linux.sh"
  exit 2
fi

if grep -q '^POSTGRES_PASSWORD=change-me$' "$ENV_FILE"; then
  echo "Refusing to start with the example PostgreSQL password." >&2
  echo "Edit docker/.env and keep POSTGRES_PASSWORD synchronized with TRADING_WORKSPACE_DATABASE_URL." >&2
  exit 2
fi

RUNTIME_DATABASE_URL="$(grep -m1 '^TRADING_WORKSPACE_DATABASE_URL=' "$ENV_FILE" | cut -d= -f2-)"
if [[ -z "$RUNTIME_DATABASE_URL" ]]; then
  echo "TRADING_WORKSPACE_DATABASE_URL must be set in docker/.env." >&2
  exit 2
fi

compose() {
  TRADING_WORKSPACE_DATABASE_URL="$RUNTIME_DATABASE_URL" \
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

mkdir -p "$DEFAULT_STUTTGART_DATA_DIR"

if grep -qi '^TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=true$' "$ENV_FILE" && \
   grep -qi '^TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__SOURCE_MODE=local_directory$' "$ENV_FILE"; then
  echo "Refreshing Börse Stuttgart delayed market-data cache..."
  if ! python3 "$ROOT_DIR/scripts/sync-stuttgart-delayed.py" \
    --directory "$DEFAULT_STUTTGART_DATA_DIR"; then
    echo "Warning: Stuttgart delayed refresh failed; existing cache is preserved." >&2
  fi
fi

compose config >/dev/null

echo "Building backend and frontend images..."
compose build backend frontend

echo "Starting PostgreSQL..."
compose up -d database

for _ in {1..30}; do
  if compose exec -T database \
    sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! compose exec -T database \
  sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
  echo "PostgreSQL did not become ready in time." >&2
  exit 1
fi

echo "Applying Alembic migrations..."
compose run --rm backend python -m alembic upgrade head

echo "Starting backend and frontend..."
compose up -d backend frontend

echo "Trading Workspace started."
echo "Frontend:  http://localhost:8080"
echo "Backend:   http://localhost:8000"
echo "Liveness:  http://localhost:8000/health"
echo "Readiness: http://localhost:8000/health/ready"
echo "Quote data: http://localhost:8000/api/v1/position-monitoring/quote-sources/stuttgart-delayed/health"
echo "Stuttgart local data directory: $DEFAULT_STUTTGART_DATA_DIR"
echo "Manual Stuttgart refresh: python3 scripts/sync-stuttgart-delayed.py"
echo "Status:    docker compose --env-file docker/.env -f docker/compose.yml ps"
echo "Logs:      docker compose --env-file docker/.env -f docker/compose.yml logs -f backend"
