"""Fail closed on configuration/runtime identities of the disposable learning stack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

RUN_LABEL = "org.trading-workspace.e2e.run-id"
SERVICES = {"database", "backend", "frontend"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def labels(value, project, run_id):
    require(value.get("com.docker.compose.project") == project, "Foreign Compose project")
    require(value.get(RUN_LABEL) == run_id, "Missing or foreign run label")


def disabled(environment):
    require(environment["TRADING_WORKSPACE_ENVIRONMENT"] == "test", "Not a test backend")
    for key, value in environment.items():
        if key.endswith(
            (
                "__ENABLED",
                "__AUTO_CONFIGURE",
                "__USAGE_APPROVED",
                "__CONTRACT_VERIFIED",
                "__PRIVATE_USE_CONFIRMED",
            )
        ):
            require(str(value).lower() == "false", f"Enabled external capability: {key}")
        if key.endswith(("__API_KEY", "__BOT_TOKEN", "__CHAT_ID")):
            require(not value, f"Credential present: {key}")


def configuration(config, project, run_id, source, database_url):
    require(config["name"] == project, "Unexpected project name")
    require(set(config["services"]) == SERVICES, "Unexpected service set")
    require(not config.get("secrets") and not config.get("configs"), "Inherited config/secret")
    require(set(config["volumes"]) == {"postgres-data"}, "Unexpected volumes")
    volume = config["volumes"]["postgres-data"]
    require(volume["name"] == project + "_postgres-data", "Unexpected volume name")
    require(not volume.get("external"), "External volume")
    require(volume["labels"].get(RUN_LABEL) == run_id, "Volume lacks run label")
    require(set(config["networks"]) == {"default", "ingress"}, "Unexpected networks")
    for name, internal in (("default", True), ("ingress", False)):
        network = config["networks"][name]
        require(network["name"] == project + "_" + name, "Unexpected network name")
        require(network.get("internal", False) is internal, "Incorrect network isolation")
        require(not network.get("external"), "External network")
        require(network["labels"].get(RUN_LABEL) == run_id, "Network lacks run label")
    for service, value in config["services"].items():
        expected = {"default"} if service == "backend" else {"default", "ingress"}
        require(set(value["networks"]) == expected, "Unexpected service network")
        require(not value.get("network_mode") and not value.get("privileged"), "Unsafe service")
        require(not value.get("secrets") and not value.get("configs"), "Service config/secret")
        require(value["labels"].get(RUN_LABEL) == run_id, "Service lacks run label")
    require(not config["services"]["backend"].get("ports"), "Backend must have no published port")
    for service, target, published in (("database", 5432, "25432"), ("frontend", 8080, "8080")):
        ports = config["services"][service]["ports"]
        require(len(ports) == 1, "Unexpected port count")
        port = ports[0]
        require(
            (port["host_ip"], port["target"], str(port["published"]))
            == ("127.0.0.1", target, published),
            "Noncanonical loopback port",
        )
    mounts = config["services"]["database"]["volumes"]
    require(len(mounts) == 1 and mounts[0]["type"] == "volume", "Unexpected database mount")
    require(mounts[0]["source"] == "postgres-data", "Foreign database volume")
    mounts = config["services"]["backend"]["volumes"]
    require(len(mounts) == 1 and mounts[0]["type"] == "bind", "Unexpected backend mount")
    require(
        mounts[0]["source"] == source and mounts[0]["read_only"] is True, "Foreign/writable bind"
    )
    require(not config["services"]["frontend"].get("volumes"), "Unexpected frontend mount")
    backend = config["services"]["backend"]["environment"]
    require(backend["TRADING_WORKSPACE_DATABASE_URL"] == database_url, "Foreign backend database")
    disabled(backend)
    require(
        config["services"]["frontend"]["build"]["args"]["VITE_API_BASE_URL"]
        == "http://localhost:8080/api",
        "Browser/build/proxy origin mismatch",
    )


def ownership(containers, networks, volumes, project, run_id):
    """Before cleanup, refuse any current resource with a different ownership label."""
    for container in containers:
        labels(container["Config"]["Labels"], project, run_id)
    for resource in [*networks, *volumes]:
        labels(resource["Labels"], project, run_id)


def runtime(
    containers, networks, volumes, project, run_id, source, database_url, database_only=False
):
    ownership(containers, networks, volumes, project, run_id)
    expected_services = {"database"} if database_only else SERVICES
    require(len(containers) == len(expected_services), "Unexpected running container count")
    require(len(networks) == 2 and len(volumes) == 1, "Unexpected resource count")
    require(volumes[0]["Name"] == project + "_postgres-data", "Foreign live volume")
    require(volumes[0]["Driver"] == "local", "Unexpected volume driver")
    network_map = {network["Name"]: network for network in networks}
    require(
        set(network_map) == {project + "_default", project + "_ingress"}, "Foreign live networks"
    )
    evidence = {"project": project, "run_id": run_id, "networks": {}, "services": {}}
    for name, internal in (("default", True), ("ingress", False)):
        value = network_map[project + "_" + name]
        require(
            value["Driver"] == "bridge" and value["Internal"] is internal, "Unsafe live network"
        )
        evidence["networks"][name] = {
            "id": value["Id"],
            "name": value["Name"],
            "internal": value["Internal"],
        }
    for container in containers:
        service = container["Config"]["Labels"]["com.docker.compose.service"]
        require(
            service in expected_services and service not in evidence["services"], "Wrong service"
        )
        expected = {"default"} if service == "backend" else {"default", "ingress"}
        connections = container["NetworkSettings"]["Networks"]
        require(
            set(connections) == {project + "_" + name for name in expected}, "Wrong live networks"
        )
        for name, value in connections.items():
            require(value["NetworkID"] == network_map[name]["Id"], "Network ID mismatch")
        bindings = {
            port: value for port, value in container["NetworkSettings"]["Ports"].items() if value
        }
        wanted = {
            "database": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "25432"}]},
            "frontend": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]},
            "backend": {},
        }
        require(bindings == wanted[service], "Wrong live port binding")
        require(not container["HostConfig"]["Privileged"], "Privileged container")
        require(container["State"]["Running"] is True, "Container not running")
        require(container["State"]["Health"]["Status"] == "healthy", "Container not healthy")
        mounts = container["Mounts"]
        if service == "database":
            require(
                len(mounts) == 1 and mounts[0]["Name"] == project + "_postgres-data",
                "Unexpected live database mount",
            )
        elif service == "backend":
            require(
                len(mounts) == 1
                and mounts[0]["Type"] == "bind"
                and mounts[0]["Source"] == source
                and mounts[0]["RW"] is False,
                "Unexpected live backend mount",
            )
            environment = dict(value.split("=", 1) for value in container["Config"]["Env"])
            require(
                environment["TRADING_WORKSPACE_DATABASE_URL"] == database_url,
                "Foreign running backend database",
            )
            disabled(environment)
        else:
            require(not mounts, "Unexpected live frontend mount")
        evidence["services"][service] = {
            "container_id": container["Id"],
            "image_id": container["Image"],
            "networks": sorted(connections),
            "published_ports": bindings,
            "health": "healthy",
        }
    evidence["volume"] = volumes[0]["Name"]
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("config", "runtime", "ownership"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source")
    parser.add_argument("--database-url")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--containers", type=Path)
    parser.add_argument("--networks", type=Path)
    parser.add_argument("--volumes", type=Path)
    parser.add_argument("--database-only", action="store_true")
    args = parser.parse_args()

    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))

    if args.mode == "config":
        configuration(load(args.config), args.project, args.run_id, args.source, args.database_url)
        print("Fresh Compose configuration, isolated backend and loopback ports verified")
    else:
        values = (load(args.containers), load(args.networks), load(args.volumes))
        if args.mode == "ownership":
            ownership(*values, args.project, args.run_id)
            print("Every resource belongs to the exact current run; cleanup allowed")
        else:
            evidence = runtime(
                *values,
                args.project,
                args.run_id,
                args.source,
                args.database_url,
                args.database_only,
            )
            print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
