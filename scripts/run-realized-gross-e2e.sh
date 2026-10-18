#!/usr/bin/env bash
set -euo pipefail

# CI-only writer qualification. It never adopts a configured application stack.
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${CI:-}" != true || "${GITHUB_ACTIONS:-}" != true \
   || "${GITHUB_WORKSPACE:-}" != "${repository_root}" ]]; then
  echo 'This runner requires its disposable GitHub Actions checkout.' >&2
  exit 1
fi
for required in docker python3 node npm; do
  command -v "${required}" >/dev/null || { echo "Missing command: ${required}" >&2; exit 1; }
done
git -C "${repository_root}" diff --quiet
git -C "${repository_root}" diff --cached --quiet
python_bin="$(command -v python3)"
docker_bin="$(command -v docker)"
run_id="$("${python_bin}" -I -c 'import uuid; print(uuid.uuid4())')"
run_hex="${run_id//-/}"
compose_project="tw-realized-report-e2e-${run_hex}"
database_name="tw_realized_report_e2e_${run_hex}"
postgres_user=tw_report_e2e
postgres_password=synthetic-report-ci-only
host_database_url="postgresql+asyncpg://${postgres_user}:${postgres_password}@127.0.0.1:35432/${database_name}"
container_database_url="postgresql+asyncpg://${postgres_user}:${postgres_password}@database:5432/${database_name}"
artifact_root="${repository_root}/frontend/test-results"
artifact_dir="${artifact_root}/realized-gross-${run_hex}"
mkdir -p "${artifact_dir}"
runtime_dir="$(mktemp -d "${artifact_root}/report-runtime.XXXXXXXX")"
mkdir -p "${runtime_dir}/source" "${runtime_dir}/docker-config"
chmod 0755 "${runtime_dir}/source"
: > "${runtime_dir}/empty.env"
cat > "${runtime_dir}/compose.yml" <<'YAML'
networks:
  default:
    internal: true
YAML

# Retain only executable/cache locations. Inherited application credentials,
# Compose settings and remote Docker contexts cannot select the test target.
clean_environment=(env -i "PATH=${PATH}" "HOME=${HOME}"
  "LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" LANG=C.UTF-8 CI=true)
docker() {
  "${clean_environment[@]}" "DOCKER_CONFIG=${runtime_dir}/docker-config" \
    "${docker_bin}" --host unix:///var/run/docker.sock "$@"
}
compose() {
  "${clean_environment[@]}" "DOCKER_CONFIG=${runtime_dir}/docker-config" \
    "POSTGRES_DB=${database_name}" "POSTGRES_USER=${postgres_user}" \
    "POSTGRES_PASSWORD=${postgres_password}" POSTGRES_PORT=127.0.0.1:35432 \
    BACKEND_PORT=127.0.0.1:38000 FRONTEND_PORT=127.0.0.1:38080 \
    "TRADING_WORKSPACE_DOCKER_DATABASE_URL=${container_database_url}" \
    TRADING_WORKSPACE_ENVIRONMENT=test TRADING_WORKSPACE_DEBUG=false \
    TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false \
    TRADING_WORKSPACE_MARKET_DATA__VONTOBEL_MARKETS__ENABLED=false \
    TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=false \
    TRADING_WORKSPACE_MARKET_DATA__GETTEX_DELAYED__ENABLED=false \
    TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__ENABLED=false \
    TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED=false \
    TRADING_WORKSPACE_MARKET_DATA__REFRESH__AUTO_CONFIGURE=false \
    TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=false \
    TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false \
    "STUTTGART_DELAYED_SOURCE_DIRECTORY=${runtime_dir}/source" \
    VITE_API_BASE_URL=http://127.0.0.1:38080/api \
    "${docker_bin}" --host unix:///var/run/docker.sock compose \
      --project-name "${compose_project}" --env-file "${runtime_dir}/empty.env" \
      -f "${repository_root}/docker/compose.yml" -f "${runtime_dir}/compose.yml" "$@"
}
stack_started=false
cleanup() {
  local result=$?
  local remaining_containers='' remaining_volumes='' remaining_networks=''
  trap - EXIT
  if [[ "${stack_started}" == true ]]; then
    compose logs --no-color > "${artifact_dir}/compose.log" 2>&1 || result=1
    compose down --volumes --remove-orphans > "${artifact_dir}/cleanup.log" 2>&1 || result=1
    remaining_containers="$(docker ps -aq --filter "label=com.docker.compose.project=${compose_project}")" || result=1
    remaining_volumes="$(docker volume ls -q --filter "label=com.docker.compose.project=${compose_project}")" || result=1
    remaining_networks="$(docker network ls -q --filter "label=com.docker.compose.project=${compose_project}")" || result=1
    if [[ -n "${remaining_containers}" || -n "${remaining_volumes}" || -n "${remaining_networks}" ]]; then
      echo 'Disposable report resources remain after cleanup.' >&2
      result=1
    fi
  fi
  rm -rf -- "${runtime_dir}"
  exit "${result}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# UUID names must still be fresh; never clean up an adopted stack or volume.
existing_containers="$(docker ps -aq --filter "label=com.docker.compose.project=${compose_project}")"
existing_volumes="$(docker volume ls -q --filter "name=^${compose_project}_postgres-data$")"
existing_networks="$(docker network ls -q --filter "name=^${compose_project}_default$")"
if [[ -n "${existing_containers}" || -n "${existing_volumes}" || -n "${existing_networks}" ]]; then
  echo 'Generated report project unexpectedly exists; refusing to adopt it.' >&2
  exit 1
fi
compose config --format json > "${runtime_dir}/compose.json"
"${clean_environment[@]}" "${python_bin}" -I - "${runtime_dir}/compose.json" "${compose_project}" \
  "${runtime_dir}/source" "${container_database_url}" <<'PY'
import json
import sys

path, project, source, database = sys.argv[1:]
with open(path, encoding="utf-8") as stream:
    config = json.load(stream)
assert config["name"] == project
assert set(config["services"]) == {"database", "backend", "frontend"}
assert set(config["volumes"]) == {"postgres-data"}
volume = config["volumes"]["postgres-data"]
assert volume["name"] == project + "_postgres-data" and not volume.get("external")
assert set(config["networks"]) == {"default"}
network = config["networks"]["default"]
assert network["name"] == project + "_default" and network["internal"] is True
assert not network.get("external")
for service, target, published in (("database", 5432, "35432"),
                                   ("backend", 8000, "38000"),
                                   ("frontend", 8080, "38080")):
    value = config["services"][service]
    assert set(value["networks"]) == {"default"} and not value.get("network_mode")
    assert not value.get("privileged")
    ports = value["ports"]
    assert len(ports) == 1
    assert (ports[0]["host_ip"], ports[0]["target"], str(ports[0]["published"])) == (
        "127.0.0.1", target, published
    )
mount = config["services"]["database"]["volumes"]
assert len(mount) == 1 and mount[0]["type"] == "volume"
assert mount[0]["source"] == "postgres-data"
mount = config["services"]["backend"]["volumes"]
assert len(mount) == 1 and mount[0]["type"] == "bind"
assert mount[0]["source"] == source and mount[0]["read_only"] is True
assert not config["services"]["frontend"].get("volumes")
environment = config["services"]["backend"]["environment"]
assert environment["TRADING_WORKSPACE_DATABASE_URL"] == database
assert environment["TRADING_WORKSPACE_ENVIRONMENT"] == "test"
for key, value in environment.items():
    if key.endswith(("__ENABLED", "__AUTO_CONFIGURE", "__USAGE_APPROVED",
                     "__CONTRACT_VERIFIED", "__PRIVATE_USE_CONFIRMED")):
        assert str(value).lower() == "false", key
    if key.endswith(("__API_KEY", "__BOT_TOKEN", "__CHAT_ID")):
        assert not value, key
print("Fresh project, volume, loopback ports, internal network and disabled providers verified")
PY

compose build backend frontend > "${artifact_dir}/build.log" 2>&1
stack_started=true
compose up -d --wait --wait-timeout 180 database
test "$(docker network inspect "${compose_project}_default" --format '{{.Internal}}')" = true
compose run --rm --no-deps -T backend python -m alembic upgrade head \
  > "${artifact_dir}/migration.log" 2>&1
compose exec -T database psql --username "${postgres_user}" --dbname "${database_name}" \
  --set=ON_ERROR_STOP=1 --set="database_name=${database_name}" \
  --set="marker=synthetic realized-gross browser ${run_id}" <<'SQL'
COMMENT ON DATABASE :"database_name" IS :'marker';
SQL
compose up -d --wait --wait-timeout 180 backend frontend
printf 'commit=%s\nproject=%s\ndatabase=%s\nrun_id=%s\n' \
  "$(git -C "${repository_root}" rev-parse HEAD)" "${compose_project}" \
  "${database_name}" "${run_id}" > "${artifact_dir}/code-and-stack.txt"

cd "${repository_root}/frontend"
"${clean_environment[@]}" "NODE_PATH=${repository_root}/frontend/node_modules" \
  PLAYWRIGHT_BASE_URL=http://127.0.0.1:38080 REPORT_E2E_WRITES_ALLOWED=1 \
  "REPORT_E2E_RUN_ID=${run_id}" "REPORT_E2E_PYTHON=${python_bin}" \
  TRADING_WORKSPACE_ENVIRONMENT=test \
  "TRADING_WORKSPACE_DATABASE_URL=${host_database_url}" \
  "TRADING_WORKSPACE_TEST_DATABASE_URL=${host_database_url}" \
  "PLAYWRIGHT_JSON_OUTPUT_FILE=${artifact_dir}/results.json" \
  ./node_modules/.bin/playwright test realized-gross-report-postgres.spec.ts \
    --project=chromium --workers=1 --retries=0 --reporter=list,json \
    --output="${artifact_dir}/playwright" | tee "${artifact_dir}/playwright.log"
"${clean_environment[@]}" "${python_bin}" -I - "${artifact_dir}/results.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    result = json.load(stream)
stats = result["stats"]
assert (stats["expected"], stats["unexpected"], stats["skipped"], stats["flaky"]) == (1, 0, 0, 0)
assert not result.get("errors")
tests = []
def collect(suites):
    for suite in suites:
        for spec in suite.get("specs", []):
            tests.extend(spec["tests"])
        collect(suite.get("suites", []))
collect(result["suites"])
assert len(tests) == 1
assert tests[0]["status"] == "expected"
assert len(tests[0]["results"]) == 1
assert tests[0]["results"][0]["status"] == "passed"
assert tests[0]["results"][0]["retry"] == 0
print("Real report browser: exactly one pass, zero skipped/flaky tests, zero retries")
PY
