#!/usr/bin/env bash
# Destructive only to disposable CI resources; never run against an operator host.
set -euo pipefail
umask 077
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
# Reproduce the v1.5.47/v1.5.48 configuration boundary: the old containers really
# lack both new keys. A fixture rendered entirely from current Compose would
# miss the absent-to-disabled upgrade contract.
python3 - "$fixture/legacy/docker/compose.yml" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text().splitlines(keepends=True)
for key in (
    "TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_SCOPE",
    "TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_NOTIFICATIONS_ENABLED",
):
    selected = [line for line in lines if line.lstrip().startswith(key + ":")]
    assert len(selected) == 1, "The bounded old-release fixture no longer matches"
    lines.remove(selected[0])
path.write_text("".join(lines))
PY
export ISSUER_RENDERER_SECCOMP_PATH="$ROOT/docker/issuer-renderer/seccomp_profile.json"
cat > "$fixture/legacy/docker/.env" <<EOF
POSTGRES_DB=migration_test
POSTGRES_USER=migration_test
POSTGRES_PASSWORD=ci-only-value
TRADING_WORKSPACE_DATABASE_URL=postgresql+asyncpg://migration_test:ci-only-value@database/migration_test
TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=true
TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false
TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY=ci-only-eodhd-key
TRADING_WORKSPACE_MARKET_DATA__EODHD__BASE_URL=https://eodhd.invalid/api
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
  docker compose --project-name trading-workspace --project-directory "$ROOT/docker" \
    --env-file "$fixture/legacy/docker/.env" \
    -f "$fixture/legacy/docker/compose.yml" -f "$ROOT/docker/compose.issuer-monitoring.yml" -f "$fixture/old.yml" "$@"
}
ci_egress_chain=TW_REVIEW_CI_EGRESS
ci_egress_created=false
isolate_runtime_egress() {
  # Only these freshly created disposable networks are intercepted. Build and
  # host traffic use other networks; application/provider/Telegram calls cannot
  # leave either runtime subnet even if a background job is unexpectedly queued.
  docker network inspect trading-workspace_default trading-workspace_issuer-discovery \
    > "$fixture/runtime-networks.json"
  python3 - "$fixture/runtime-networks.json" > "$fixture/runtime-subnets" <<'PY'
import ipaddress
import json
import sys
from pathlib import Path

networks = json.loads(Path(sys.argv[1]).read_text())
assert len(networks) == 2
subnets = set()
for network in networks:
    assert network["Labels"]["com.docker.compose.project"] == "trading-workspace"
    assert network["EnableIPv6"] is False, "The fixture must not have unguarded IPv6"
    for config in network["IPAM"]["Config"]:
        subnet = ipaddress.ip_network(config["Subnet"], strict=True)
        assert subnet.version == 4 and subnet.prefixlen >= 16
        subnets.add(str(subnet))
assert len(subnets) == 2
print("\n".join(sorted(subnets)))
PY
  sudo iptables --wait -N "$ci_egress_chain"
  ci_egress_created=true
  while IFS= read -r subnet; do
    sudo iptables --wait -A "$ci_egress_chain" -d "$subnet" -j RETURN
  done < "$fixture/runtime-subnets"
  sudo iptables --wait -A "$ci_egress_chain" -j REJECT
  while IFS= read -r subnet; do
    sudo iptables --wait -I DOCKER-USER 1 -s "$subnet" -j "$ci_egress_chain"
    printf '%s\n' "$subnet" >> "$fixture/guarded-runtime-subnets"
  done < "$fixture/runtime-subnets"
}
cleanup() {
  for state in "$fixture/private" "$fixture"/trading-workspace-state/runs/*/deployment \
    "$fixture/future-state/deployment"; do
    if [[ -f "$state/operation.log" ]]; then cat "$state/operation.log"; fi
  done
  # This entire runner and these volumes are synthetic, created above in this job.
  old down --volumes || true
  if [[ "$ci_egress_created" == true ]]; then
    if [[ -f "$fixture/guarded-runtime-subnets" ]]; then
      while IFS= read -r subnet; do
        sudo iptables --wait -D DOCKER-USER -s "$subnet" -j "$ci_egress_chain" || true
      done < "$fixture/guarded-runtime-subnets"
    fi
    sudo iptables --wait -F "$ci_egress_chain" || true
    sudo iptables --wait -X "$ci_egress_chain" || true
  fi
}
trap cleanup EXIT
old build backend frontend
old up -d --no-deps --wait --wait-timeout 120 database issuer-renderer
isolate_runtime_egress
old run --rm --no-deps backend python -m alembic upgrade head
old up -d --no-deps --wait --wait-timeout 120 backend frontend
docker exec -i trading-workspace-backend-1 python - <<'PY'
import socket

try:
    socket.create_connection(("198.51.100.1", 443), timeout=3)
except OSError:
    print("Synthetic external destination was intercepted")
else:
    raise AssertionError("Runtime egress was not blocked")
PY
sudo iptables --wait -vnxL "$ci_egress_chain" > "$fixture/egress-guard-counters"
python3 - "$fixture/egress-guard-counters" <<'PY'
import sys
from pathlib import Path

rows = [line.split() for line in Path(sys.argv[1]).read_text().splitlines()]
assert any(len(row) > 2 and row[2] == "REJECT" and int(row[0]) > 0 for row in rows), (
    "An actual runtime connection must reach the dedicated rejection rule"
)
PY
docker exec trading-workspace-backend-1 python -c \
  'import os; assert "TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_SCOPE" not in os.environ; assert "TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_NOTIFICATIONS_ENABLED" not in os.environ'
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
docker exec trading-workspace-backend-1 python -c \
  'import os; assert os.environ["TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_SCOPE"] == "DISABLED"; assert os.environ["TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_NOTIFICATIONS_ENABLED"] == "false"'
# New tooling must inspect the original sealed checkout, without rebuilding or
# changing its release, configuration, services or persistent state.
git -C "$ROOT" worktree add --detach "$fixture/trading-workspace-app" HEAD
docker ps -aq --filter label=com.docker.compose.project=trading-workspace | sort > "$fixture/before.ids"
bash "$fixture/trading-workspace-app/scripts/migrate-legacy-issuer.sh" compose "$fixture/private" ps
bash "$fixture/trading-workspace-app/scripts/migrate-legacy-issuer.sh" compose "$fixture/private" \
  exec -T backend python -c 'print("Existing deployment diagnostics succeeded")' </dev/null
if BACKEND_PORT=9001 bash "$fixture/trading-workspace-app/scripts/migrate-legacy-issuer.sh" \
  compose "$fixture/private" ps; then
  echo 'Actual environment drift was not rejected' >&2; exit 1
fi
docker ps -aq --filter label=com.docker.compose.project=trading-workspace | sort > "$fixture/after.ids"
cmp "$fixture/before.ids" "$fixture/after.ids"
# Qualify the documented next-release update of this already canonical deployment.
# A distinct disposable commit supplies a new revision/image tag without changing
# production code or any prepared state from the first deployment.
printf '%s\n' '0.0.491' > "$fixture/trading-workspace-app/VERSION"
git -C "$fixture/trading-workspace-app" -c user.name=CI -c user.email=ci@example.invalid \
  commit -am 'CI synthetic tagged release for bounded activation'
git -C "$fixture/trading-workspace-app" tag v0.0.491
mkdir -m 700 "$fixture/trading-workspace-state"
mkdir -p "$fixture/trading-workspace-state/runs/ci"
mkdir -p "$fixture/current-configuration/docker"
cp "$ROOT/docker/compose.yml" "$fixture/current-configuration/docker/compose.yml"
cp "$fixture/private/environment.env" "$fixture/current-configuration/docker/.env"
bash "$fixture/trading-workspace-app/scripts/migrate-legacy-issuer.sh" \
  prepare "$fixture/current-configuration" "$fixture/trading-workspace-state/runs/ci/deployment"
bash "$fixture/trading-workspace-app/scripts/migrate-legacy-issuer.sh" apply "$fixture/trading-workspace-state/runs/ci/deployment"
test -f "$fixture/trading-workspace-state/runs/ci/deployment/deployed"
test "$(cat "$fixture/private/database-container")" = "$(cat "$fixture/trading-workspace-state/runs/ci/deployment/database-container")"
test "$(docker exec trading-workspace-database-1 psql -At -U migration_test -d migration_test -c 'SELECT marker FROM deployment_probe')" = retained
test "$(docker exec trading-workspace-issuer-renderer-1 cat /state/ci-marker)" = retained
bash "$fixture/trading-workspace-app/scripts/migrate-legacy-issuer.sh" compose "$fixture/trading-workspace-state/runs/ci/deployment" ps
echo 'Synthetic migration passed: data, state, settings, sandbox, schema and images retained/verified.'

# Daily controls must keep the migrated containers, images and persistent data.
# The database intentionally still has the original Compose-file provenance.
launcher_state="$fixture/trading-workspace-state/runs/ci/deployment"
printf '%s\n' "$launcher_state" > "$fixture/trading-workspace-state/current-state"
launcher() {
  TRADING_WORKSPACE_BASE="$fixture" DISPLAY= WAYLAND_DISPLAY= \
    bash "$ROOT/scripts/trading-workspace.sh" "$@"
}
docker inspect --format '{{.Id}} {{.Image}}' trading-workspace-database-1 \
  trading-workspace-issuer-renderer-1 trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/launcher-before"
launcher status
launcher start
launcher stop
launcher start
launcher status
docker inspect --format '{{.Id}} {{.Image}}' trading-workspace-database-1 \
  trading-workspace-issuer-renderer-1 trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/launcher-after"
cmp "$fixture/launcher-before" "$fixture/launcher-after"
(cd "$launcher_state" && sha256sum --check --status inputs.sha256)
test "$(docker exec trading-workspace-database-1 psql -At -U migration_test -d migration_test -c 'SELECT marker FROM deployment_probe')" = retained
test "$(docker exec trading-workspace-issuer-renderer-1 cat /state/ci-marker)" = retained
echo 'Daily launcher passed: repeated start and stop/start kept containers, images, data and configuration.'

# Qualify a separately reviewed provider activation without replacing this release,
# enabling mapping discovery or using any real provider/account/Telegram service.
# The database contains only synthetic deployment probes, no monitored positions.
export TRADING_WORKSPACE_BIN_DIR="$fixture/launcher-bin"
export XDG_DATA_HOME="$fixture/launcher-data"
TRADING_WORKSPACE_BASE="$fixture" bash "$ROOT/scripts/trading-workspace.sh" install
activation_launcher() {
  TRADING_WORKSPACE_BASE="$fixture" DISPLAY= WAYLAND_DISPLAY= \
    "$TRADING_WORKSPACE_BIN_DIR/trading-workspace" "$@"
}
# Qualify the real review activation first, then the independent EODHD transition
# from its additional sealed metadata. The database has no monitored positions;
# every provider and every external notification remains disabled at this stage.
python3 - "$fixture/trading-workspace-state/runs" > "$fixture/review-old-generations.json" <<'PY'
import json
import sys
from pathlib import Path

print(json.dumps(sorted(str(path) for path in Path(sys.argv[1]).glob("*/deployment"))))
PY
python3 "$fixture/trading-workspace-app/scripts/activate-indicative-monitoring.py" prepare --base "$fixture"
review_state="$(python3 - "$fixture/trading-workspace-state/runs" "$fixture/review-old-generations.json" <<'PY'
import json
import sys
from pathlib import Path

previous = set(json.loads(Path(sys.argv[2]).read_text()))
current = {str(path) for path in Path(sys.argv[1]).glob("*/deployment")}
created = current - previous
assert len(created) == 1, "Expected one prepared review activation"
print(created.pop())
PY
)"
python3 "$review_state/activation-tool.py" apply "$review_state" --base "$fixture"
test "$(cat "$fixture/trading-workspace-state/current-state")" = "$review_state"
test -f "$review_state/deployed"
(cd "$review_state" && sha256sum --check --status inputs.sha256)
activation_launcher status
docker exec trading-workspace-backend-1 python -c \
  'import json, urllib.request; s=json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/position-monitoring/runtime/status", timeout=10)); assert s["review_scope"] == "INDICATIVE_ENTRY_V2" and s["review_rule_version"] == "indicative-entry-review-v2" and s["review_notifications_enabled"] is False and s["running"] is True; assert s["hebeltrader_scope"] == "DISABLED"; print("Synthetic indicative scope active; strict scope and review delivery remain disabled")'
launcher_state="$review_state"
cp "$launcher_state/inputs.sha256" "$fixture/activation-old-inputs.sha256"
cp "$fixture/trading-workspace-state/current-state" "$fixture/activation-old-pointer"
docker inspect trading-workspace-database-1 trading-workspace-issuer-renderer-1 \
  trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/activation-before.json"
python3 - "$fixture/trading-workspace-state/runs" > "$fixture/activation-old-generations.json" <<'PY'
import json
import sys
from pathlib import Path

print(json.dumps(sorted(str(path) for path in Path(sys.argv[1]).glob("*/deployment"))))
PY
python3 "$ROOT/scripts/enable-eodhd-linux.py" prepare --base "$fixture"
activation_state="$(python3 - "$fixture/trading-workspace-state/runs" "$fixture/activation-old-generations.json" <<'PY'
import json
import sys
from pathlib import Path

previous = set(json.loads(Path(sys.argv[2]).read_text()))
current = {str(path) for path in Path(sys.argv[1]).glob("*/deployment")}
created = current - previous
assert len(created) == 1, "Expected one new, privately prepared activation generation"
print(created.pop())
PY
)"
test -f "$activation_state/prepared"
python3 - "$activation_state/transition.json" <<'PY'
import json
import sys
from pathlib import Path

transition = json.loads(Path(sys.argv[1]).read_text())
assert transition["schema"] == 2 and transition["old_activation"] is True
PY
if python3 "$ROOT/scripts/enable-eodhd-linux.py" apply "$activation_state" --base "$fixture" \
  > "$fixture/activation-unacknowledged.log" 2>&1; then
  echo 'Unacknowledged active monitoring was not rejected' >&2
  exit 1
fi
grep -q -- 'allow-existing-automation' "$fixture/activation-unacknowledged.log"
test ! -e "$fixture/trading-workspace-state/pending"
test ! -e "$activation_state/apply-started"
cmp "$fixture/activation-old-pointer" "$fixture/trading-workspace-state/current-state"
cmp "$fixture/activation-old-inputs.sha256" "$launcher_state/inputs.sha256"
(cd "$launcher_state" && sha256sum --check --status inputs.sha256)
docker inspect trading-workspace-database-1 trading-workspace-issuer-renderer-1 \
  trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/activation-prepared.json"
python3 - "$fixture/activation-before.json" "$fixture/activation-prepared.json" <<'PY'
import json
import sys
from pathlib import Path

before, after = [json.loads(Path(path).read_text()) for path in sys.argv[1:]]
fields = ("Id", "Image", "Config", "HostConfig", "Mounts")
assert len(before) == len(after) == 4
assert all(all(old[field] == new[field] for field in fields) for old, new in zip(before, after))
PY

python3 "$ROOT/scripts/enable-eodhd-linux.py" apply "$activation_state" --base "$fixture" \
  --allow-existing-automation
test "$(cat "$fixture/trading-workspace-state/current-state")" = "$activation_state"
test -f "$activation_state/deployed"
test ! -e "$fixture/trading-workspace-state/pending"
cmp "$fixture/activation-old-inputs.sha256" "$launcher_state/inputs.sha256"
(cd "$launcher_state" && sha256sum --check --status inputs.sha256)
(cd "$activation_state" && sha256sum --check --status inputs.sha256)
docker inspect trading-workspace-database-1 trading-workspace-issuer-renderer-1 \
  trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/activation-after.json"
python3 - "$fixture/activation-before.json" "$fixture/activation-after.json" \
  "$fixture/trading-workspace-app" "$activation_state" <<'PY'
import json
import sys
from pathlib import Path

before, after = [json.loads(Path(path).read_text()) for path in sys.argv[1:3]]
app, state = sys.argv[3:]
expected_chain = f"{app}/docker/compose.yml,{app}/docker/compose.issuer-monitoring.yml,{state}/preserve.json"
flag = "TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED"
assert len(before) == len(after) == 4
for old, new in zip(before, after):
    assert old["Name"] == new["Name"]
    assert old["Image"] == new["Image"], "Activation must retain the exact installed image"
    assert old["Mounts"] == new["Mounts"], "Data and consent mounts must stay unchanged"
    old_env = dict(entry.split("=", 1) for entry in old["Config"]["Env"])
    new_env = dict(entry.split("=", 1) for entry in new["Config"]["Env"])
    service = new["Config"]["Labels"]["com.docker.compose.service"]
    if service == "backend":
        assert old_env[flag] == "false" and new_env[flag] == "true"
        old_env[flag] = "true"
    assert old_env == new_env, "Only EODHD activation may change the environment"
    if service == "database":
        assert old["Id"] == new["Id"]
        assert old["Config"] == new["Config"]
    else:
        assert old["Id"] != new["Id"], "All application labels must reference the new generation"
        assert new["Config"]["Labels"]["com.docker.compose.project.config_files"] == expected_chain
PY
docker exec trading-workspace-backend-1 python -c \
  'import json, urllib.request; s=json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/market-data/providers/status", timeout=10)); assert s["enabled"] is True and s["configured"] is True and s["used_today"] == 0; print("Synthetic EODHD activation: enabled/configured, zero provider calls")'
test "$(docker exec trading-workspace-database-1 psql -At -U migration_test -d migration_test -c 'SELECT marker FROM deployment_probe')" = retained
test "$(docker exec trading-workspace-issuer-renderer-1 cat /state/ci-marker)" = retained
docker inspect --format '{{.Id}} {{.Image}}' trading-workspace-database-1 \
  trading-workspace-issuer-renderer-1 trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/activation-launcher-before"
activation_launcher status
activation_launcher start
activation_launcher stop
activation_launcher start
activation_launcher status
docker inspect --format '{{.Id}} {{.Image}}' trading-workspace-database-1 \
  trading-workspace-issuer-renderer-1 trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/activation-launcher-after"
cmp "$fixture/activation-launcher-before" "$fixture/activation-launcher-after"
docker exec trading-workspace-backend-1 python -c \
  'import json, urllib.request; s=json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/market-data/providers/status", timeout=10)); assert s["enabled"] is True and s["configured"] is True and s["used_today"] == 0'

# Exercise the original next-release preparation against the newly activated
# environment. A separate synthetic commit isolates build tags; no third apply
# or migration is needed to prove that the original preservation guards accept it.
git -C "$fixture/trading-workspace-app" worktree add --detach "$fixture/future-release" HEAD
git -C "$fixture/future-release" -c user.name=CI -c user.email=ci@example.invalid \
  commit --allow-empty -m 'CI next release after explicit provider activation'
mkdir -p "$fixture/future-configuration/docker" "$fixture/future-state"
cp "$fixture/trading-workspace-app/docker/compose.yml" "$fixture/future-configuration/docker/compose.yml"
cp "$activation_state/environment.env" "$fixture/future-configuration/docker/.env"
bash "$fixture/future-release/scripts/migrate-legacy-issuer.sh" prepare \
  "$fixture/future-configuration" "$fixture/future-state/deployment"
test -f "$fixture/future-state/deployment/prepared"
python3 - "$fixture/future-state/deployment/candidate.json" <<'PY'
import json
import sys
from pathlib import Path

environment = json.loads(Path(sys.argv[1]).read_text())["services"]["backend"]["environment"]
assert environment["TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_SCOPE"] == "INDICATIVE_ENTRY_V2"
assert environment["TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_NOTIFICATIONS_ENABLED"] == "false"
assert environment["TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED"] == "true"
PY
test "$(cat "$fixture/trading-workspace-state/current-state")" = "$activation_state"
docker inspect --format '{{.Id}} {{.Image}}' trading-workspace-database-1 \
  trading-workspace-issuer-renderer-1 trading-workspace-backend-1 trading-workspace-frontend-1 > "$fixture/activation-after-future-prepare"
cmp "$fixture/activation-launcher-after" "$fixture/activation-after-future-prepare"
activation_launcher status
echo 'Bounded review defaults and review-to-EODHD activation passed: approved deltas, preserved data/images/seals, working launcher and next-release preparation.'
