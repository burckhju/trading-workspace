#!/usr/bin/env bash
# Deliberate migration of the reviewed four-service legacy issuer topology.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL_ROOT="$ROOT"
MODE="${1:-help}"
shift || true
fail() { echo "$*" >&2; exit 2; }
if [[ "$MODE" == help || "$MODE" == --help ]]; then
  echo 'Usage: migrate-legacy-issuer.sh prepare LEGACY_CHECKOUT PRIVATE_STATE_DIR'
  echo '       migrate-legacy-issuer.sh apply PRIVATE_STATE_DIR'
  echo '       migrate-legacy-issuer.sh compose PRIVATE_STATE_DIR ps|logs|exec ...'
  echo 'Run from a separate, clean, pinned release checkout. prepare builds only; apply stops services.'
  echo 'compose can inspect older prepared releases; it retains their pinned checkout and full chain.'
  exit 0
fi
[[ "$MODE" == prepare || "$MODE" == apply || "$MODE" == compose ]] || fail 'Unknown mode'
[[ $# -ge 1 ]] || fail 'Missing arguments'
if [[ "$MODE" == prepare ]]; then
  [[ $# == 2 ]] || fail 'prepare requires legacy checkout and new private directory'
  LEGACY="$(realpath -- "$1")"
  STATE="$(realpath -m -- "$2")"
  [[ "$LEGACY" != "$ROOT" && -f "$LEGACY/docker/.env" ]] || fail 'Use a separate release checkout and existing configuration'
  [[ ! -e "$STATE" ]] || fail 'Private directory already exists; use a new directory'
  [[ -d "$(dirname "$STATE")" ]] || fail 'Private directory parent must exist'
  if git -C "$(dirname "$STATE")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail 'Private state must be outside every Git checkout'
  fi
  mkdir -m 700 -- "$STATE"
else
  STATE="$(realpath -- "$1")"
  shift
  [[ -d "$STATE" && -O "$STATE" && "$(stat -c %a "$STATE")" == 700 ]] || fail 'Private state must be owned by you with mode 700'
fi
LOG="$STATE/operation.log"
trap 'echo "Stopped in phase ${PHASE:-preflight}. Private details: $LOG. No automatic rollback." >&2' ERR
PHASE=preflight
git -C "$TOOL_ROOT" rev-parse --verify HEAD >/dev/null
[[ -z "$(git -C "$TOOL_ROOT" status --porcelain --untracked-files=all)" ]] || fail 'Tool checkout must be clean, including untracked files'
if [[ "$MODE" == compose ]]; then
  [[ $# -ge 1 && ( "$1" == ps || "$1" == logs || "$1" == exec ) ]] || fail 'compose permits only ps, logs or exec'
  (cd "$STATE" && sha256sum --check --status inputs.sha256) || fail 'Prepared inputs changed; inspect private state'
  ROOT="$(cat "$STATE/release-root")"
fi
REVISION="$(git -C "$ROOT" rev-parse HEAD)"
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)" ]] || fail 'Release checkout must be clean, including untracked files'
export ISSUER_RENDERER_SECCOMP_PATH="$ROOT/docker/issuer-renderer/seccomp_profile.json"
compose() {
  docker compose --project-name trading-workspace --env-file "$STATE/environment.env" \
    -f "$ROOT/docker/compose.yml" -f "$ROOT/docker/compose.issuer-monitoring.yml" \
    -f "$STATE/preserve.json" "$@"
}
inspect() {
  [[ "$(docker ps --all --quiet --filter label=com.docker.compose.project=trading-workspace | wc -l)" -eq 4 ]] || fail 'Expected exactly four project containers, including stopped containers'
  docker inspect trading-workspace-backend-1 trading-workspace-issuer-renderer-1 \
    trading-workspace-database-1 trading-workspace-frontend-1
}
helper() {
  docker run --rm -i --network none --read-only --cap-drop ALL \
    --security-opt no-new-privileges:true --memory 128m --cpus 1 --pids-limit 64 \
    --entrypoint python "$(cat "$STATE/helper-image")" \
    -c "$(cat "$TOOL_ROOT/backend/app/tools/legacy_issuer_deployment.py")" "$@"
}
pair() { printf '['; cat "$1"; printf ','; cat "$2"; printf ']'; }
seal() {
  (cd "$STATE" && sha256sum environment.env preserve.json baseline.json helper-image revision release-root candidate.json)
}
if [[ "$MODE" == prepare ]]; then
  printf '%s\n' "$REVISION" > "$STATE/revision"
  printf '%s\n' "$ROOT" > "$STATE/release-root"
  cp -- "$LEGACY/docker/.env" "$STATE/environment.env"
  chmod 600 "$STATE/environment.env"
  inspect > "$STATE/baseline.json" 2>> "$LOG"
  docker inspect --format '{{.Image}}' trading-workspace-backend-1 > "$STATE/helper-image"
  # Base remains an independently rendered reference; no legacy package is executed.
  docker compose --project-name trading-workspace --env-file "$STATE/environment.env" \
    -f "$LEGACY/docker/compose.yml" config --format json > "$STATE/base.json" 2>> "$LOG"
  pair "$STATE/baseline.json" "$STATE/base.json" | helper overlay "$REVISION" > "$STATE/preserve.json" 2>> "$LOG"
  compose config --format json > "$STATE/candidate.json" 2>> "$LOG"
  pair "$STATE/baseline.json" "$STATE/candidate.json" | helper validate >> "$LOG" 2>&1
  docker volume inspect trading-workspace_postgres-data trading-workspace_issuer-consent-state > "$STATE/volumes.json" 2>> "$LOG"
  PHASE=build
  echo 'Configuration and data bindings verified. Building isolated release image tags; services stay running.'
  compose build backend frontend issuer-renderer >> "$LOG" 2>&1
  for service in backend frontend issuer-renderer; do
    image="trading-workspace-$service:migration-$REVISION"
    [[ "$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$image")" == "$REVISION" ]] || fail 'Built image revision differs'
    docker image inspect --format '{{.Id}}' "$image" > "$STATE/$service.image"
  done
  docker inspect --format '{{.Id}}' trading-workspace-database-1 > "$STATE/database-container"
  seal > "$STATE/inputs.sha256"
  (cd "$STATE" && sha256sum backend.image frontend.image issuer-renderer.image database-container) >> "$STATE/inputs.sha256"
  touch "$STATE/prepared"
  echo "Prepared commit $REVISION. No deployment performed. Private state: $STATE"
  printf 'Apply in a maintenance window: bash %q apply %q\n' "$ROOT/scripts/migrate-legacy-issuer.sh" "$STATE"
  exit 0
fi
[[ -f "$STATE/prepared" && "$(cat "$STATE/revision")" == "$REVISION" && "$(cat "$STATE/release-root")" == "$ROOT" ]] || fail 'Prepared release checkout differs'
(cd "$STATE" && sha256sum --check --status inputs.sha256) || fail 'Prepared inputs changed; prepare again in a new directory'
compose config --format json > "$STATE/current-config.json" 2>> "$LOG"
# Ambient interpolation must not change values, types or ordered arrays. Object
# key order and whitespace from Compose serialization are not configuration drift.
pair "$STATE/candidate.json" "$STATE/current-config.json" | helper config >> "$LOG" 2>&1 || fail 'Effective Compose configuration changed or comparison failed; inspect private operation.log'
if [[ "$MODE" == compose ]]; then
  compose "$@"
  exit 0
fi
[[ $# == 0 ]] || fail 'Unexpected apply arguments'
[[ ! -e "$STATE/apply-started" ]] || fail 'An apply was already started; inspect state and recover deliberately'
inspect > "$STATE/current.json" 2>> "$LOG"
pair "$STATE/baseline.json" "$STATE/current.json" | helper identity >> "$LOG" 2>&1
pair "$STATE/current.json" "$STATE/current-config.json" | helper validate >> "$LOG" 2>&1
for service in backend frontend issuer-renderer; do
  image="trading-workspace-$service:migration-$REVISION"
  [[ "$(docker image inspect --format '{{.Id}}' "$image")" == "$(cat "$STATE/$service.image")" ]] || fail 'Prepared image changed'
done
docker exec trading-workspace-database-1 sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >> "$LOG" 2>&1
PHASE=stop-and-backup
touch "$STATE/apply-started"
echo 'Stopping backend and renderer for consistent backups. Database stays running.'
docker stop --time 60 trading-workspace-backend-1 trading-workspace-issuer-renderer-1 >> "$LOG" 2>&1
docker exec trading-workspace-database-1 sh -c 'pg_dump --no-password --format=custom -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$STATE/database.dump" 2>> "$LOG"
[[ -s "$STATE/database.dump" ]] || fail 'Empty database backup'
docker exec -i trading-workspace-database-1 pg_restore --list < "$STATE/database.dump" > "$STATE/database.contents" 2>> "$LOG"
docker cp trading-workspace-issuer-renderer-1:/state/. - > "$STATE/consent-state.tar" 2>> "$LOG"
tar -tf "$STATE/consent-state.tar" > "$STATE/consent.contents"
[[ -s "$STATE/consent-state.tar" ]] || fail 'Empty consent archive'
touch "$STATE/backups-verified"
PHASE=renderer
echo 'Starting release renderer; waiting for sandbox health.'
compose up -d --no-deps --wait --wait-timeout 120 issuer-renderer >> "$LOG" 2>&1
PHASE=migration
touch "$STATE/migration-started"
compose run --rm --no-deps backend python -m alembic upgrade head >> "$LOG" 2>&1
PHASE=application
compose up -d --no-deps --wait --wait-timeout 180 backend frontend >> "$LOG" 2>&1
PHASE=verification
inspect > "$STATE/deployed.json" 2>> "$LOG"
pair "$STATE/deployed.json" "$STATE/current-config.json" | helper validate >> "$LOG" 2>&1
[[ "$(docker inspect --format '{{.Id}}' trading-workspace-database-1)" == "$(cat "$STATE/database-container")" ]] || fail 'Database container unexpectedly changed'
for service in backend frontend issuer-renderer; do
  [[ "$(docker inspect --format '{{.Image}}' "trading-workspace-$service-1")" == "$(cat "$STATE/$service.image")" ]] || fail 'Deployed image differs'
done
compose exec -T backend python -m alembic current >> "$LOG" 2>&1
touch "$STATE/deployed"
echo "Deployed commit $REVISION; readiness, renderer sandbox and Alembic command succeeded."
echo 'Provider access, consent reuse, monitoring cycles and Telegram delivery require separate evidence.'
printf 'Status: bash %q compose %q ps\n' "$ROOT/scripts/migrate-legacy-issuer.sh" "$STATE"
