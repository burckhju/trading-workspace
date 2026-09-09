#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/docker/.env"
COMPOSE_FILE="$ROOT_DIR/docker/compose.yml"
BACKEND_URL="${TRADING_WORKSPACE_VALIDATION_BACKEND_URL:-http://localhost:8000}"

TRADE_ID=""
SEED_PRICE=""
SEED_QUANTITY="1"
RUN_MONITOR=false
ALLOW_TELEGRAM=false
REQUIRE_STUTTGART=false

usage() {
  cat <<'EOF'
Usage: bash scripts/validate-daily-position-loop.sh [options]

Validates the deployed daily open-position operating loop without changing trading rules.

Options:
  --trade-id UUID          Validate monitoring and product valuation for an existing trade.
  --seed-price PRICE       Create/reuse a reproducible open XSTU position at PRICE and use it.
  --seed-quantity N        Quantity for --seed-price (default: 1).
  --run-monitor            Run one controlled position-monitoring cycle.
  --allow-telegram         Explicitly allow live Telegram delivery during --run-monitor.
  --require-stuttgart      Fail unless the Stuttgart delayed source reports READY.
  -h, --help               Show this help.

Examples:
  bash scripts/validate-daily-position-loop.sh --require-stuttgart
  bash scripts/validate-daily-position-loop.sh --seed-price 2.42 --require-stuttgart
  bash scripts/validate-daily-position-loop.sh --trade-id <uuid> --run-monitor
  bash scripts/validate-daily-position-loop.sh --trade-id <uuid> --run-monitor --allow-telegram
EOF
}

while (($#)); do
  case "$1" in
    --trade-id)
      TRADE_ID="${2:-}"
      shift 2
      ;;
    --seed-price)
      SEED_PRICE="${2:-}"
      shift 2
      ;;
    --seed-quantity)
      SEED_QUANTITY="${2:-}"
      shift 2
      ;;
    --run-monitor)
      RUN_MONITOR=true
      shift
      ;;
    --allow-telegram)
      ALLOW_TELEGRAM=true
      shift
      ;;
    --require-stuttgart)
      REQUIRE_STUTTGART=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -n "$TRADE_ID" && -n "$SEED_PRICE" ]]; then
  echo "Use either --trade-id or --seed-price, not both." >&2
  exit 2
fi

if $ALLOW_TELEGRAM && ! $RUN_MONITOR; then
  echo "--allow-telegram requires --run-monitor." >&2
  exit 2
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing docker/.env. Run bash scripts/start-linux.sh and configure the deployment first." >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker with Compose v2 is required." >&2
  exit 1
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

fetch() {
  local path="$1"
  curl -fsS "$BACKEND_URL$path"
}

pretty_json() {
  compose exec -T backend python -c \
    'import json,sys; print(json.dumps(json.load(sys.stdin), indent=2, sort_keys=True, default=str))'
}

json_count() {
  local key="$1"
  compose exec -T backend python -c \
    "import json,sys; value=json.load(sys.stdin).get('$key', []); print(len(value))"
}

echo "== Daily Position Loop Operational Validation =="
echo "Backend: $BACKEND_URL"

echo
printf '1/7 Deployment containers... '
compose ps --status running >/dev/null
printf 'OK\n'

echo
printf '2/7 Backend liveness/readiness... '
fetch /health >/dev/null
fetch /health/ready >/dev/null
printf 'OK\n'

echo
printf '3/7 Database migration head... '
ALEMBIC_HEAD="$(compose exec -T backend python -m alembic heads | awk 'NF {print $1}' | tail -n 1)"
ALEMBIC_CURRENT="$(compose exec -T backend python -m alembic current)"
if [[ -z "$ALEMBIC_HEAD" ]] || ! grep -q "$ALEMBIC_HEAD" <<<"$ALEMBIC_CURRENT"; then
  echo "FAILED" >&2
  echo "Repository head: ${ALEMBIC_HEAD:-unknown}" >&2
  echo "Database current: $ALEMBIC_CURRENT" >&2
  exit 1
fi
printf 'OK (%s)\n' "$ALEMBIC_HEAD"

echo
printf '4/7 Stuttgart delayed source health...\n'
STUTTGART_HEALTH="$(fetch /api/v1/position-monitoring/quote-sources/stuttgart-delayed/health)"
printf '%s' "$STUTTGART_HEALTH" | pretty_json
if $REQUIRE_STUTTGART && ! grep -Eq '"status"[[:space:]]*:[[:space:]]*"READY"' <<<"$STUTTGART_HEALTH"; then
  echo "Stuttgart delayed source is not READY." >&2
  exit 1
fi

if [[ -n "$SEED_PRICE" ]]; then
  echo
  echo "Creating/reusing controlled XSTU open position..."
  SEED_OUTPUT="$(compose exec -T backend python -m app.tools.seed_xstu_open_position \
    --price "$SEED_PRICE" --quantity "$SEED_QUANTITY")"
  echo "$SEED_OUTPUT"
  TRADE_ID="$(sed -n 's/.*"trade_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' <<<"$SEED_OUTPUT" | tail -n 1)"
  if [[ -z "$TRADE_ID" ]]; then
    echo "Could not read trade_id from XSTU seed output." >&2
    exit 1
  fi
  echo "Validation trade: $TRADE_ID"
fi

echo
printf '5/7 Operational workspace open-position snapshot...\n'
POSITIONS="$(fetch /api/v1/operational-workspace/positions)"
printf '%s' "$POSITIONS" | pretty_json
POSITION_COUNT="$(printf '%s' "$POSITIONS" | json_count positions)"
echo "Open position snapshot count: $POSITION_COUNT"

if [[ -n "$TRADE_ID" ]]; then
  echo
  printf '6/7 Trade monitoring and held-product valuation...\n'
  MONITORING_HEALTH="$(fetch "/api/v1/position-monitoring/trades/$TRADE_ID/health")"
  PRODUCT_VALUATION="$(fetch "/api/v1/position-monitoring/trades/$TRADE_ID/product-valuation")"
  echo "Monitoring health:"
  printf '%s' "$MONITORING_HEALTH" | pretty_json
  echo "Product valuation:"
  printf '%s' "$PRODUCT_VALUATION" | pretty_json
else
  echo
  echo "6/7 Trade monitoring and held-product valuation... SKIPPED (use --trade-id or --seed-price)"
fi

if $RUN_MONITOR; then
  echo
  echo "7/7 Controlled monitoring cycle..."
  MONITOR_ARGS=()
  if $ALLOW_TELEGRAM; then
    MONITOR_ARGS+=(--allow-telegram)
    echo "Live Telegram delivery explicitly authorized for this cycle."
  else
    echo "Telegram delivery is not authorized; the CLI will remain fail-safe."
  fi
  compose exec -T backend python -m app.features.position_monitoring.cli "${MONITOR_ARGS[@]}"
else
  echo
  echo "7/7 Controlled monitoring cycle... SKIPPED (use --run-monitor)"
fi

echo
echo "Validation completed."
echo "Review the Operational Workspace at http://localhost:8080 and, for a controlled position,"
echo "open Trade Management to verify alert/attention, timeline, then record an already executed"
echo "partial sale or full close through the existing sales workflow."
echo "This script does not fabricate broker executions or auto-close positions."
