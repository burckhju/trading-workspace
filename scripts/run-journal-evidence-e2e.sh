#!/usr/bin/env bash
set -euo pipefail

# This writer qualification only creates its own stack on an actual CI checkout.
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${CI:-}" != true || "${GITHUB_ACTIONS:-}" != true \
   || "${GITHUB_WORKSPACE:-}" != "${repository_root}" \
   || ! "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ ]]; then
  echo 'This runner requires its disposable GitHub Actions checkout.' >&2
  exit 1
fi
for required in docker python3 node npm curl; do
  command -v "${required}" >/dev/null || { echo "Missing command: ${required}" >&2; exit 1; }
done
test -S /var/run/docker.sock
git -C "${repository_root}" diff --quiet
git -C "${repository_root}" diff --cached --quiet
python_bin="$(command -v python3)"
docker_bin="$(command -v docker)"
run_id="$("${python_bin}" -I -c 'import uuid; print(uuid.uuid4())')"
run_hex="${run_id//-/}"
compose_project="tw-journal-evidence-e2e-${run_hex}"
database_name="trading_workspace_test_journal_${run_hex}"
postgres_user=tw_journal_e2e
postgres_password=synthetic-journal-ci-only
host_database_url="postgresql+asyncpg://${postgres_user}:${postgres_password}@127.0.0.1:25432/${database_name}"
container_database_url="postgresql+asyncpg://${postgres_user}:${postgres_password}@database:5432/${database_name}"
artifact_root="${repository_root}/frontend/test-results"
artifact_dir="${artifact_root}/journal-evidence-${run_hex}"
mkdir -p "${artifact_root}"
mkdir "${artifact_dir}"
runtime_dir="$(mktemp -d "${artifact_root}/journal-runtime.XXXXXXXX")"
mkdir "${runtime_dir}/source" "${runtime_dir}/docker-config"
chmod 0755 "${runtime_dir}/source"
: > "${runtime_dir}/empty.env"
cat > "${runtime_dir}/compose.yml" <<'YAML'
services:
  database:
    labels:
      org.trading-workspace.e2e.run-id: ${JOURNAL_E2E_RUN_ID}
    networks: [default, ingress]
  backend:
    labels:
      org.trading-workspace.e2e.run-id: ${JOURNAL_E2E_RUN_ID}
    networks: [default]
    ports: !reset []
  frontend:
    labels:
      org.trading-workspace.e2e.run-id: ${JOURNAL_E2E_RUN_ID}
    networks: [default, ingress]
networks:
  default:
    internal: true
    labels:
      org.trading-workspace.e2e.run-id: ${JOURNAL_E2E_RUN_ID}
  ingress:
    internal: false
    labels:
      org.trading-workspace.e2e.run-id: ${JOURNAL_E2E_RUN_ID}
volumes:
  postgres-data:
    labels:
      org.trading-workspace.e2e.run-id: ${JOURNAL_E2E_RUN_ID}
YAML

# No inherited app configuration, provider credentials or remote Docker endpoint.
clean_environment=(env -i "PATH=${PATH}" "HOME=${HOME}"
  "LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" LANG=C.UTF-8 CI=true GITHUB_ACTIONS=true)
docker() {
  "${clean_environment[@]}" "DOCKER_CONFIG=${runtime_dir}/docker-config" \
    "${docker_bin}" --host unix:///var/run/docker.sock "$@"
}
compose() {
  "${clean_environment[@]}" "DOCKER_CONFIG=${runtime_dir}/docker-config" \
    "JOURNAL_E2E_RUN_ID=${run_id}" \
    "POSTGRES_DB=${database_name}" "POSTGRES_USER=${postgres_user}" \
    "POSTGRES_PASSWORD=${postgres_password}" POSTGRES_PORT=127.0.0.1:25432 \
    FRONTEND_PORT=127.0.0.1:8080 \
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
    VITE_API_BASE_URL=http://localhost:8080/api \
    "${docker_bin}" --host unix:///var/run/docker.sock compose \
      --project-name "${compose_project}" --env-file "${runtime_dir}/empty.env" \
      -f "${repository_root}/docker/compose.yml" -f "${runtime_dir}/compose.yml" "$@"
}
contract="${repository_root}/tests/e2e/support/journal_stack_contract.py"
contract_args=(--project "${compose_project}" --run-id "${run_id}"
  --source "${runtime_dir}/source" --database-url "${container_database_url}")
inspect_resources() {
  local ids
  local -a resource_ids
  ids="$(docker ps -aq --filter "label=com.docker.compose.project=${compose_project}")" || return 1
  if [[ -n "${ids}" ]]; then
    mapfile -t resource_ids <<< "${ids}"
    docker inspect "${resource_ids[@]}" > "${runtime_dir}/containers.json" || return 1
  else
    printf '[]\n' > "${runtime_dir}/containers.json"
  fi
  ids="$(docker network ls -q --filter "label=com.docker.compose.project=${compose_project}")" || return 1
  if [[ -n "${ids}" ]]; then
    mapfile -t resource_ids <<< "${ids}"
    docker network inspect "${resource_ids[@]}" > "${runtime_dir}/networks.json" || return 1
  else
    printf '[]\n' > "${runtime_dir}/networks.json"
  fi
  ids="$(docker volume ls -q --filter "label=com.docker.compose.project=${compose_project}")" || return 1
  if [[ -n "${ids}" ]]; then
    mapfile -t resource_ids <<< "${ids}"
    docker volume inspect "${resource_ids[@]}" > "${runtime_dir}/volumes.json" || return 1
  else
    printf '[]\n' > "${runtime_dir}/volumes.json"
  fi
}
resource_args=(--containers "${runtime_dir}/containers.json"
  --networks "${runtime_dir}/networks.json" --volumes "${runtime_dir}/volumes.json")
stack_started=false
cleanup() {
  local result=$?
  local cleanup_result=0
  trap - EXIT
  if [[ "${stack_started}" == true ]]; then
    if inspect_resources && "${clean_environment[@]}" "${python_bin}" -I "${contract}" \
      ownership "${contract_args[@]}" "${resource_args[@]}" > "${artifact_dir}/cleanup.log" 2>&1; then
      compose logs --no-color > "${artifact_dir}/compose.log" 2>&1 || result=1
      compose down --volumes >> "${artifact_dir}/cleanup.log" 2>&1 || cleanup_result=1
      inspect_resources || cleanup_result=1
      "${clean_environment[@]}" "${python_bin}" -I - "${runtime_dir}" \
        "${compose_project}" "${run_id}" > "${artifact_dir}/cleanup.json" <<'PY' || cleanup_result=1
import json
import sys
from pathlib import Path
root, project, run_id = sys.argv[1:]
remaining = {kind: json.loads((Path(root) / (kind + ".json")).read_text())
             for kind in ("containers", "networks", "volumes")}
clean = all(not values for values in remaining.values())
print(json.dumps({"project": project, "run_id": run_id, "removed": clean,
                  "remaining_counts": {kind: len(values) for kind, values in remaining.items()}}, indent=2))
if not clean:
    raise SystemExit("Disposable journal resources remain after cleanup")
PY
    else
      echo 'Ownership could not be verified; refusing cleanup of unidentified resources.' >&2
      cleanup_result=1
    fi
  fi
  if [[ "${cleanup_result}" != 0 ]]; then result=1; fi
  printf 'exit_status=%s\ncleanup_status=%s\n' "${result}" "${cleanup_result}" \
    > "${artifact_dir}/outcome.txt"
  "${clean_environment[@]}" "${python_bin}" -I - "${artifact_dir}" <<'PY' || result=1
import hashlib
import sys
from pathlib import Path
root = Path(sys.argv[1])
lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root)}"
         for path in sorted(root.rglob("*")) if path.is_file() and path.name != "SHA256SUMS"]
(root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  rm -rf -- "${runtime_dir}"
  exit "${result}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

test "$(docker info --format '{{.OSType}}')" = linux
# A found project/name is a collision, never a target to adopt and later delete.
for kind in container volume network; do
  case "${kind}" in
    container) existing="$(docker ps -aq --filter "name=${compose_project}")" ;;
    volume) existing="$(docker volume ls -q --filter "name=${compose_project}")" ;;
    network) existing="$(docker network ls -q --filter "name=${compose_project}")" ;;
  esac
  if [[ -n "${existing}" ]]; then
    echo "Generated journal ${kind} name unexpectedly exists; refusing to adopt it." >&2
    exit 1
  fi
done
inspect_resources
"${python_bin}" -I - "${runtime_dir}" <<'PY'
import json
import sys
from pathlib import Path
for kind in ("containers", "networks", "volumes"):
    if json.loads((Path(sys.argv[1]) / (kind + ".json")).read_text()):
        raise SystemExit("Generated project label already exists; refusing to adopt it")
PY
compose config --format json > "${runtime_dir}/compose.json"
"${clean_environment[@]}" "${python_bin}" -I "${contract}" config \
  "${contract_args[@]}" --config "${runtime_dir}/compose.json" > "${artifact_dir}/configuration-check.txt"
printf 'checkout=%s\ntree=%s\nworkflow_sha=%s\nworkflow_run=%s\nproject=%s\ndatabase=%s\nrun_id=%s\n' \
  "$(git -C "${repository_root}" rev-parse HEAD)" \
  "$(git -C "${repository_root}" rev-parse HEAD^{tree})" "${GITHUB_SHA:-}" \
  "${GITHUB_RUN_ID}" "${compose_project}" "${database_name}" "${run_id}" \
  > "${artifact_dir}/code-and-stack.txt"
cd "${repository_root}/frontend"
test_files=(post-trade-journal-postgres.spec.ts post-trade-evidence-history-postgres.spec.ts)
"${clean_environment[@]}" "NODE_PATH=${repository_root}/frontend/node_modules" \
  "PLAYWRIGHT_JSON_OUTPUT_FILE=${artifact_dir}/discovery.json" \
  ./node_modules/.bin/playwright test "${test_files[@]}" --project=chromium \
  --workers=1 --retries=0 --list --reporter=json
"${python_bin}" -I "${repository_root}/scripts/check-journal-e2e-report.py" discover \
  "${artifact_dir}/discovery.json" "${artifact_dir}/expected-tests.json"

compose build backend frontend > "${artifact_dir}/build.log" 2>&1
stack_started=true
compose up -d --wait --wait-timeout 180 database
inspect_resources
"${clean_environment[@]}" "${python_bin}" -I "${contract}" runtime \
  "${contract_args[@]}" "${resource_args[@]}" --database-only \
  > "${artifact_dir}/database-before-migration.json"
actual_database="$(compose exec -T database psql --username "${postgres_user}" \
  --dbname "${database_name}" --set=ON_ERROR_STOP=1 -Atc 'SELECT current_database()')"
test "${actual_database}" = "${database_name}"
compose exec -T database psql --username "${postgres_user}" --dbname "${database_name}" \
  --set=ON_ERROR_STOP=1 --set="database_name=${database_name}" \
  --set="marker=synthetic journal-evidence browser ${run_id}" <<'SQL'
COMMENT ON DATABASE :"database_name" IS :'marker';
SQL
compose run --rm --no-deps -T backend python -m alembic upgrade head \
  > "${artifact_dir}/migration.log" 2>&1
compose up -d --wait --wait-timeout 180 backend frontend
inspect_resources
"${clean_environment[@]}" "${python_bin}" -I "${contract}" runtime \
  "${contract_args[@]}" "${resource_args[@]}" > "${artifact_dir}/network-and-ports.json"
"${clean_environment[@]}" curl --noproxy '*' --fail --silent --show-error \
  http://localhost:8080/api/health/ready > "${artifact_dir}/host-api-readiness.json"

# Only now enable the two guarded test writers. The independent DB guard must
# connect from the host, inspect the exact marker/migration/workspace, then read.
journal_environment=("${clean_environment[@]}" JOURNAL_E2E_WRITES_ALLOWED=1 FT011_E2E_WRITES_ALLOWED=1
  "JOURNAL_E2E_RUN_ID=${run_id}" "JOURNAL_E2E_PYTHON=${python_bin}"
  JOURNAL_E2E_WORKSPACE_ID=00000000-0000-4000-8000-000000000001
  TRADING_WORKSPACE_ENVIRONMENT=test "TRADING_WORKSPACE_DATABASE_URL=${host_database_url}"
  "TRADING_WORKSPACE_TEST_DATABASE_URL=${host_database_url}")
"${journal_environment[@]}" "${python_bin}" \
  "${repository_root}/tests/e2e/support/journal_database_guard.py" > "${artifact_dir}/initial-database.json"
"${python_bin}" -I - "${artifact_dir}/initial-database.json" <<'PY'
import json
import sys
state = json.loads(open(sys.argv[1], encoding="utf-8").read())
for table in ("trades", "execution_records", "trade_journals", "learning_evidence", "lessons"):
    if state["tables"][table]["count"] != 0:
        raise SystemExit("Fresh qualification database unexpectedly contains business data")
PY
test_result=0
"${journal_environment[@]}" "NODE_PATH=${repository_root}/frontend/node_modules" \
  PLAYWRIGHT_BASE_URL=http://localhost:8080 \
  "PLAYWRIGHT_JSON_OUTPUT_FILE=${artifact_dir}/results.json" \
  ./node_modules/.bin/playwright test "${test_files[@]}" --project=chromium \
  --workers=1 --retries=0 --trace=on --reporter=list,json \
  --output="${artifact_dir}/playwright" | tee "${artifact_dir}/playwright.log" || test_result=$?
"${python_bin}" -I "${repository_root}/scripts/check-journal-e2e-report.py" verify \
  "${artifact_dir}/results.json" "${artifact_dir}/expected-tests.json" \
  > "${artifact_dir}/report-verification.txt"
exit "${test_result}"
