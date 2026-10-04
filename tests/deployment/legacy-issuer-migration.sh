#!/usr/bin/env bash
# Destructive only to disposable CI resources; never run against an operator host.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${CI:-}" == true ]] || { echo 'GitHub CI only' >&2; exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -z "$(docker ps -aq --filter label=com.docker.compose.project=trading-workspace)" ]] || { echo 'Existing project detected' >&2; exit 2; }
for volume in trading-workspace_postgres-data trading-workspace_issuer-consent-state; do
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    echo 'Existing project volume detected' >&2; exit 2
  fi
done
fixture="$(mktemp -d)"
data_directory="$fixture/data with spaces/\$literal"
mkdir -p "$fixture/legacy/docker" "$data_directory"
cp "$ROOT/docker/compose.yml" "$fixture/legacy/docker/compose.yml"
export ISSUER_RENDERER_SECCOMP_PATH="$ROOT/docker/issuer-renderer/seccomp_profile.json"
cat > "$fixture/legacy/docker/.env" <<EOF
POSTGRES_DB=migration_test
POSTGRES_USER=migration_test
POSTGRES_PASSWORD=ci-only-value
TRADING_WORKSPACE_DATABASE_URL=postgresql+asyncpg://migration_test:ci-only-value@database/migration_test
TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=true
STUTTGART_DELAYED_SOURCE_DIRECTORY='$data_directory'
EOF
cat > "$fixture/old.yml" <<'EOF'
services:
  backend:
    image: legacy-backend:test
    environment:
      TRADING_WORKSPACE_MARKET_DATA__JPMORGAN__ENABLED: "false"
      TRADING_WORKSPACE_MARKET_DATA__JPMORGAN__CACHE_SECONDS: "60"
      TRADING_WORKSPACE_MARKET_DATA__JPMORGAN__TIMEOUT_SECONDS: "40"
      TRADING_WORKSPACE_MARKET_DATA__MORGANSTANLEY__ENABLED: "false"
      TRADING_WORKSPACE_MARKET_DATA__MORGANSTANLEY__CACHE_SECONDS: "60"
      TRADING_WORKSPACE_MARKET_DATA__MORGANSTANLEY__TIMEOUT_SECONDS: "40"
      TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED: "false"
      TRADING_WORKSPACE_MARKET_DATA__REFRESH__AUTO_DISCOVER_ISSUER_ROUTES: "false"
      TRADING_WORKSPACE_MARKET_DATA__REFRESH__AUTO_SELECT_POSITION_SOURCES: "false"
      TRADING_WORKSPACE_MARKET_DATA__REFRESH__ISSUER_RENDERER_ENABLED: "false"
      TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED: "false"
      TRADING_WORKSPACE_POSITION_MONITORING__PARALLEL_POSITIONS: "4"
  frontend:
    image: legacy-frontend:test
  issuer-renderer:
    image: issuer-renderer:test
EOF
old() {
  docker compose --project-name trading-workspace --env-file "$fixture/legacy/docker/.env" \
    -f "$ROOT/docker/compose.yml" -f "$ROOT/docker/compose.issuer-monitoring.yml" -f "$fixture/old.yml" "$@"
}
cleanup() {
  for state in private upgrade; do
    if [[ -f "$fixture/$state/operation.log" ]]; then cat "$fixture/$state/operation.log"; fi
  done
  # This entire runner and these volumes are synthetic, created above in this job.
  old down --volumes || true
}
trap cleanup EXIT
old build backend frontend
old up -d --no-deps --wait --wait-timeout 120 database issuer-renderer
old run --rm --no-deps backend python -m alembic upgrade head
old up -d --no-deps --wait --wait-timeout 120 backend frontend
docker exec trading-workspace-database-1 psql -U migration_test -d migration_test \
  -c "CREATE TABLE deployment_probe (marker text); INSERT INTO deployment_probe VALUES ('retained');"
docker exec trading-workspace-issuer-renderer-1 python -c 'from pathlib import Path; Path("/state/ci-marker").write_text("retained")'
bash "$ROOT/scripts/migrate-legacy-issuer.sh" prepare "$fixture/legacy" "$fixture/private"
# Reproduce serialization-only drift without changing any sealed input. All
# Docker operations still reach the real daemon; only rendered JSON is reformatted.
export TW_REAL_DOCKER="$(command -v docker)"
mkdir "$fixture/bin"
cat > "$fixture/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == compose && " $* " == *' config --format json '* ]]; then
  "$TW_REAL_DOCKER" "$@" | python3 -c 'import json, sys; print(json.dumps(json.load(sys.stdin), sort_keys=True, indent=4))'
else
  exec "$TW_REAL_DOCKER" "$@"
fi
EOF
chmod 700 "$fixture/bin/docker"
export PATH="$fixture/bin:$PATH"
# Deliberate preservation overlay must keep false activation flags despite canonical opt-in.
bash "$ROOT/scripts/migrate-legacy-issuer.sh" apply "$fixture/private"
if cmp -s "$fixture/private/candidate.json" "$fixture/private/current-config.json"; then
  echo 'Fixture did not reproduce serialization-only drift' >&2; exit 1
fi
test -f "$fixture/private/deployed"
test -s "$fixture/private/database.dump"
grep -q deployment_probe "$fixture/private/database.contents"
grep -q ci-marker "$fixture/private/consent.contents"
test "$(docker exec trading-workspace-database-1 psql -At -U migration_test -d migration_test -c 'SELECT marker FROM deployment_probe')" = retained
test "$(docker exec trading-workspace-issuer-renderer-1 cat /state/ci-marker)" = retained
# Inspect only approved values; do not output a full deployment environment.
docker exec trading-workspace-backend-1 python -c 'import os; assert os.environ["TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED"] == "false"; assert os.environ["TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED"] == "false"'
# New tooling must inspect the original sealed checkout, without rebuilding or
# changing its release, configuration, services or persistent state.
git -C "$ROOT" worktree add --detach "$fixture/diagnostic-tool" HEAD
docker ps -aq --filter label=com.docker.compose.project=trading-workspace | sort > "$fixture/before.ids"
bash "$fixture/diagnostic-tool/scripts/migrate-legacy-issuer.sh" compose "$fixture/private" ps
bash "$fixture/diagnostic-tool/scripts/migrate-legacy-issuer.sh" compose "$fixture/private" \
  exec -T backend python -c 'print("Existing deployment diagnostics succeeded")' </dev/null
if BACKEND_PORT=9001 bash "$fixture/diagnostic-tool/scripts/migrate-legacy-issuer.sh" \
  compose "$fixture/private" ps; then
  echo 'Actual environment drift was not rejected' >&2; exit 1
fi
docker ps -aq --filter label=com.docker.compose.project=trading-workspace | sort > "$fixture/after.ids"
cmp "$fixture/before.ids" "$fixture/after.ids"
# Qualify the documented next-release update of this already canonical deployment.
# A distinct disposable commit supplies a new revision/image tag without changing
# production code or any prepared state from the first deployment.
git -C "$fixture/diagnostic-tool" -c user.name=CI -c user.email=ci@example.invalid \
  commit --allow-empty -m 'CI next-release deployment fixture'
bash "$fixture/diagnostic-tool/scripts/migrate-legacy-issuer.sh" \
  prepare "$fixture/legacy" "$fixture/upgrade"
bash "$fixture/diagnostic-tool/scripts/migrate-legacy-issuer.sh" apply "$fixture/upgrade"
test -f "$fixture/upgrade/deployed"
test "$(cat "$fixture/private/database-container")" = "$(cat "$fixture/upgrade/database-container")"
test "$(docker exec trading-workspace-database-1 psql -At -U migration_test -d migration_test -c 'SELECT marker FROM deployment_probe')" = retained
test "$(docker exec trading-workspace-issuer-renderer-1 cat /state/ci-marker)" = retained
bash "$fixture/diagnostic-tool/scripts/migrate-legacy-issuer.sh" compose "$fixture/upgrade" ps
echo 'Synthetic migration passed: data, state, settings, sandbox, schema and images retained/verified.'
