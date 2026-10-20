#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/docker/.env"
ENV_EXAMPLE="$ROOT_DIR/docker/.env.example"
COMPOSE_FILE="$ROOT_DIR/docker/compose.yml"
DEFAULT_STUTTGART_DATA_DIR="$ROOT_DIR/docker/stuttgart-data"
FRANKFURT_ENV_FILE="$ROOT_DIR/docker/frankfurt.env"
COMPOSE_FILES=(-f "$COMPOSE_FILE")
REQUIRE_FRANKFURT=false
ISSUER_MONITORING=false
CHECK_ONLY=false
EXTRA_OVERLAYS=()

while (( $# )); do
  case "$1" in
    --frankfurt) REQUIRE_FRANKFURT=true ;;
    --issuer-monitoring) ISSUER_MONITORING=true ;;
    --check) CHECK_ONLY=true ;;
    --overlay)
      if (( $# < 2 )) || [[ "$2" == --* ]]; then
        echo "--overlay requires an existing Compose file." >&2
        exit 2
      fi
      overlay="$2"
      [[ "$overlay" == /* ]] || overlay="$ROOT_DIR/$overlay"
      if [[ ! -f "$overlay" ]]; then
        echo "Compose overlay does not exist: $overlay" >&2
        exit 2
      fi
      EXTRA_OVERLAYS+=("$(realpath -- "$overlay")")
      shift ;;
    --help|-h)
      echo "Usage: bash scripts/start-linux.sh [--frankfurt] [--overlay FILE ...] [--issuer-monitoring] [--check]"
      echo "Existing docker/frankfurt.env is included automatically, without changing its activation flags."
      echo "--frankfurt requires that configuration to exist; no account or subscription is created."
      echo "--overlay preserves additional Compose files in argument order (relative to the repository)."
      echo "--issuer-monitoring explicitly opts into the canonical issuer overlay, appended last."
      echo "--check validates configuration and existing container provenance without changing the stack."
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ -f "$FRANKFURT_ENV_FILE" ]]; then
  COMPOSE_FILES+=(-f "$ROOT_DIR/docker/compose.frankfurt.yml")
  echo "Including existing Frankfurt configuration (activation flags are preserved)."
elif [[ "$REQUIRE_FRANKFURT" == true ]]; then
  echo "docker/frankfurt.env is missing. Configure it using docs/frankfurt-quotes.md first." >&2
  exit 2
fi

for overlay in "${EXTRA_OVERLAYS[@]}"; do
  if [[ "$overlay" == "$ROOT_DIR/docker/compose.issuer-monitoring.yml" ]]; then
    echo "Use --issuer-monitoring for the canonical issuer overlay." >&2
    exit 2
  fi
  COMPOSE_FILES+=(-f "$overlay")
done
if [[ "$ISSUER_MONITORING" == true ]]; then
  COMPOSE_FILES+=(-f "$ROOT_DIR/docker/compose.issuer-monitoring.yml")
  export ISSUER_RENDERER_SECCOMP_PATH="${ISSUER_RENDERER_SECCOMP_PATH:-$ROOT_DIR/docker/issuer-renderer/seccomp_profile.json}"
  if [[ "$ISSUER_RENDERER_SECCOMP_PATH" != /* || ! -r "$ISSUER_RENDERER_SECCOMP_PATH" ]]; then
    echo "ISSUER_RENDERER_SECCOMP_PATH must identify an existing readable absolute profile path." >&2
    exit 2
  fi
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required and was not found in PATH" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (docker compose ...)" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ "$CHECK_ONLY" == true ]]; then
    echo "docker/.env is missing; --check does not create configuration." >&2
    exit 2
  fi
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

RUNTIME_DATABASE_URL="$(grep -m1 '^TRADING_WORKSPACE_DATABASE_URL=' "$ENV_FILE" | cut -d= -f2- || true)"
if [[ -z "$RUNTIME_DATABASE_URL" ]]; then
  echo "TRADING_WORKSPACE_DATABASE_URL must be set in docker/.env." >&2
  exit 2
fi

compose() {
  TRADING_WORKSPACE_DATABASE_URL="$RUNTIME_DATABASE_URL" \
    docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" "$@"
}

# Container labels retain the Compose chain even when a service is stopped.
# Refuse accidental configuration loss; obsolete/relocated overlays need a reviewed
# manual migration, not an inferred replacement or an automatic activation.
compose config --quiet
existing_containers="$(compose ps --all --quiet)"
for container in $existing_containers; do
  previous_files="$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$container")"
  if [[ -z "$previous_files" || "$previous_files" == '<no value>' ]]; then
    echo "Cannot verify existing container Compose provenance; review the deployment manually." >&2
    exit 2
  fi
  IFS=',' read -r -a previous_chain <<< "$previous_files"
  next_index=1
  for previous_file in "${previous_chain[@]}"; do
    matched=false
    while (( next_index < ${#COMPOSE_FILES[@]} )); do
      current_file="${COMPOSE_FILES[$next_index]}"
      next_index=$((next_index + 2))
      if [[ "$(realpath -m -- "$previous_file")" == "$(realpath -m -- "$current_file")" ]]; then
        matched=true
        break
      fi
    done
    if [[ "$matched" != true ]]; then
      echo "Requested Compose chain omits or reorders an existing file: $previous_file" >&2
      echo "Keep the full chain using --overlay / --issuer-monitoring, or review a manual deployment." >&2
      exit 2
    fi
  done
done

if [[ "$CHECK_ONLY" == true ]]; then
  echo "Compose configuration and existing file order verified. No deployment performed."
  exit 0
fi

mkdir -p "$DEFAULT_STUTTGART_DATA_DIR"

if grep -qi '^TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=true$' "$ENV_FILE" && \
   grep -qi '^TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__SOURCE_MODE=local_directory$' "$ENV_FILE"; then
  echo "Refreshing Börse Stuttgart delayed market-data cache..."
  if ! python3 "$ROOT_DIR/scripts/sync-stuttgart-delayed.py" \
    --directory "$DEFAULT_STUTTGART_DATA_DIR"; then
    echo "Warning: Stuttgart delayed refresh failed; existing cache is preserved." >&2
  fi
fi

BUILD_SERVICES=(backend frontend)
if [[ "$ISSUER_MONITORING" == true ]]; then
  BUILD_SERVICES+=(issuer-renderer)
fi
echo "Building ${BUILD_SERVICES[*]} images..."
compose build "${BUILD_SERVICES[@]}"

if [[ "$ISSUER_MONITORING" == true ]]; then
  echo "Starting issuer renderer and waiting for sandbox health..."
  compose up -d --no-deps --wait --wait-timeout 120 issuer-renderer
fi

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
compose run --rm --no-deps backend python -m alembic upgrade head

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
printf -v COMPOSE_HINT '%q ' docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}"
if [[ "$ISSUER_MONITORING" == true ]]; then
  printf -v SECCOMP_HINT 'ISSUER_RENDERER_SECCOMP_PATH=%q ' "$ISSUER_RENDERER_SECCOMP_PATH"
  COMPOSE_HINT="$SECCOMP_HINT$COMPOSE_HINT"
fi
if [[ -f "$FRANKFURT_ENV_FILE" ]]; then
  echo "Frankfurt health: http://localhost:8000/api/v1/position-monitoring/quote-sources/frankfurt/health"
fi
echo "Status:    ${COMPOSE_HINT}ps"
echo "Logs:      ${COMPOSE_HINT}logs -f backend"
