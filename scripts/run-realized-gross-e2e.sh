#!/usr/bin/env bash
set -euo pipefail

# CI-only writer qualification. It never adopts a configured application stack.
if [[ $# -gt 1 ]]; then
  echo 'Choose exactly one known native performance qualification.' >&2
  exit 2
fi
qualification="${1:-realized-gross}"
case "${qualification}" in
  realized-gross) spec_file=realized-gross-report-postgres.spec.ts ;;
  closed-trades) spec_file=closed-trades-report-postgres.spec.ts ;;
  *) echo 'Unknown native performance qualification.' >&2; exit 2 ;;
esac
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
artifact_dir="${artifact_root}/realized-gross-${qualification}-${run_hex}"
mkdir -p "${artifact_dir}"
runtime_dir="$(mktemp -d "${artifact_root}/report-runtime.XXXXXXXX")"
mkdir -p "${runtime_dir}/source" "${runtime_dir}/docker-config"
chmod 0755 "${runtime_dir}/source"
: > "${runtime_dir}/empty.env"
cat > "${runtime_dir}/compose.yml" <<'YAML'
services:
  database:
    networks: [default, ingress]
  backend:
    networks: [default]
    ports: !reset []
  frontend:
    networks: [default, ingress]
networks:
  default:
    internal: true
  ingress:
    internal: false
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
    FRONTEND_PORT=127.0.0.1:38080 \
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
  "${clean_environment[@]}" "${python_bin}" -I - "${artifact_dir}" "${result}" \
    "${compose_project}" "${database_name}" "${run_id}" "${qualification}" \
    "${remaining_containers}" "${remaining_volumes}" "${remaining_networks}" \
    "${stack_started}" <<'PY' || result=1
import hashlib
import json
import pathlib
import sys

root, result, project, database, run_id, qualification, containers, volumes, networks, started = sys.argv[1:]
directory = pathlib.Path(root)
cleanup = {
    "qualification": qualification,
    "project": project,
    "database": database,
    "run_id": run_id,
    "stack_started": started == "true",
    "exit_code": int(result),
    "remaining_containers": containers.split(),
    "remaining_volumes": volumes.split(),
    "remaining_networks": networks.split(),
}
(directory / "cleanup.json").write_text(json.dumps(cleanup, indent=2) + "\n")
manifest = {}
for path in sorted(directory.rglob("*")):
    if path.is_symlink():
        raise RuntimeError("Evidence must not include a symlink")
    if path.is_file() and path != directory / "manifest.json":
        manifest[str(path.relative_to(directory))] = {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
(directory / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(json.dumps(cleanup, sort_keys=True))
PY
  rm -rf -- "${runtime_dir}"
  exit "${result}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# UUID names must still be fresh; never clean up an adopted stack or volume.
existing_containers="$(docker ps -aq --filter "label=com.docker.compose.project=${compose_project}")"
existing_volumes="$(docker volume ls -q --filter "name=^${compose_project}_postgres-data$")"
existing_default_network="$(docker network ls -q --filter "name=^${compose_project}_default$")"
existing_ingress_network="$(docker network ls -q --filter "name=^${compose_project}_ingress$")"
if [[ -n "${existing_containers}" || -n "${existing_volumes}" \
   || -n "${existing_default_network}" || -n "${existing_ingress_network}" ]]; then
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
assert set(config["networks"]) == {"default", "ingress"}
for name, internal in (("default", True), ("ingress", False)):
    network = config["networks"][name]
    assert network["name"] == project + "_" + name
    assert network.get("internal", False) is internal and not network.get("external")
for service in ("database", "backend", "frontend"):
    value = config["services"][service]
    expected = {"default"} if service == "backend" else {"default", "ingress"}
    assert set(value["networks"]) == expected and not value.get("network_mode")
    assert not value.get("privileged")
assert not config["services"]["backend"].get("ports")
for service, target, published in (("database", 5432, "35432"),
                                   ("frontend", 8080, "38080")):
    value = config["services"][service]
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
print("Fresh project, volume, loopback ingress, isolated backend and disabled providers verified")
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
docker network inspect "${compose_project}_default" "${compose_project}_ingress" \
  > "${runtime_dir}/networks.json"
container_ids="$(compose ps -q)"
mapfile -t actual_container_ids <<< "${container_ids}"
docker inspect "${actual_container_ids[@]}" > "${runtime_dir}/containers.json"
"${clean_environment[@]}" "${python_bin}" -I - "${runtime_dir}/networks.json" \
  "${runtime_dir}/containers.json" "${compose_project}" \
  > "${artifact_dir}/network-and-ports.json" <<'PY'
import json
import sys

network_path, container_path, project = sys.argv[1:]
with open(network_path, encoding="utf-8") as stream:
    actual_networks = json.load(stream)
with open(container_path, encoding="utf-8") as stream:
    actual_containers = json.load(stream)
assert len(actual_networks) == 2 and len(actual_containers) == 3
networks = {network["Name"]: network for network in actual_networks}
assert set(networks) == {project + "_default", project + "_ingress"}
evidence = {"project": project, "networks": {}, "services": {}}
for name, internal in (("default", True), ("ingress", False)):
    network = networks[project + "_" + name]
    assert network["Driver"] == "bridge" and network["Internal"] is internal
    assert network["Labels"]["com.docker.compose.project"] == project
    evidence["networks"][name] = {
        "id": network["Id"], "name": network["Name"],
        "internal": network["Internal"], "driver": network["Driver"],
    }
for container in actual_containers:
    labels = container["Config"]["Labels"]
    assert labels["com.docker.compose.project"] == project
    service = labels["com.docker.compose.service"]
    assert service in {"database", "backend", "frontend"}
    assert service not in evidence["services"]
    connections = container["NetworkSettings"]["Networks"]
    expected = {"default"} if service == "backend" else {"default", "ingress"}
    assert set(connections) == {project + "_" + name for name in expected}
    for name, connection in connections.items():
        assert connection["NetworkID"] == networks[name]["Id"]
    bindings = {
        port: bound for port, bound in (container["NetworkSettings"].get("Ports") or {}).items()
        if bound
    }
    expected_bindings = {
        "database": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "35432"}]},
        "frontend": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "38080"}]},
        "backend": {},
    }
    assert bindings == expected_bindings[service], (service, bindings)
    assert container["State"]["Running"] is True
    assert container["State"]["Health"]["Status"] == "healthy"
    evidence["services"][service] = {
        "container_id": container["Id"], "image_id": container["Image"],
        "networks": sorted(connections), "published_ports": bindings,
        "health": container["State"]["Health"]["Status"],
    }
print(json.dumps(evidence, indent=2, sort_keys=True))
PY
printf 'commit=%s\nproject=%s\ndatabase=%s\nrun_id=%s\nqualification=%s\nspec=%s\n' \
  "$(git -C "${repository_root}" rev-parse HEAD)" "${compose_project}" \
  "${database_name}" "${run_id}" "${qualification}" "${spec_file}" \
  > "${artifact_dir}/code-and-stack.txt"

cd "${repository_root}/frontend"
"${clean_environment[@]}" "NODE_PATH=${repository_root}/frontend/node_modules" \
  PLAYWRIGHT_BASE_URL=http://127.0.0.1:38080 REPORT_E2E_WRITES_ALLOWED=1 \
  "REPORT_E2E_RUN_ID=${run_id}" "REPORT_E2E_PYTHON=${python_bin}" \
  TRADING_WORKSPACE_ENVIRONMENT=test \
  "TRADING_WORKSPACE_DATABASE_URL=${host_database_url}" \
  "TRADING_WORKSPACE_TEST_DATABASE_URL=${host_database_url}" \
  "PLAYWRIGHT_JSON_OUTPUT_FILE=${artifact_dir}/results.json" \
  ./node_modules/.bin/playwright test "${spec_file}" \
    --project=chromium --workers=1 --retries=0 --reporter=list,json \
    --trace=on \
    --output="${artifact_dir}/playwright" | tee "${artifact_dir}/playwright.log"
"${clean_environment[@]}" "${python_bin}" -I \
  "${repository_root}/scripts/check-performance-e2e-report.py" \
  "${artifact_dir}/results.json" "${qualification}" \
  | tee "${artifact_dir}/verified-native-journey.json"
