"""Pure, offline validation for the bounded legacy-issuer deployment runbook.

Invoked through a network-isolated Python image by the shell entry point. Private
inspect/config JSON arrives on stdin; only the overlay is ever returned to stdout.
No provider, database, consent or notification operation belongs in this module.
"""

from __future__ import annotations

import json
import sys
from typing import Any

PROJECT = "trading-workspace"
SERVICES = ("backend", "issuer-renderer", "database", "frontend")
PREFIX = "TRADING_WORKSPACE_"
PRESERVED_KEYS = {
    *(
        f"{PREFIX}MARKET_DATA__{provider}__{key}"
        for provider in ("JPMORGAN", "MORGANSTANLEY")
        for key in ("ENABLED", "CACHE_SECONDS", "TIMEOUT_SECONDS")
    ),
    *(
        f"{PREFIX}MARKET_DATA__REFRESH__{key}"
        for key in (
            "ENABLED",
            "AUTO_DISCOVER_ISSUER_ROUTES",
            "AUTO_SELECT_POSITION_SOURCES",
            "ISSUER_RENDERER_ENABLED",
        )
    ),
    f"{PREFIX}NOTIFICATION__TELEGRAM__ENABLED",
    f"{PREFIX}POSITION_MONITORING__PARALLEL_POSITIONS",
}


class DeploymentError(ValueError):
    """A diagnostic containing only field names and static descriptions."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeploymentError(message)


def environment(container: dict[str, Any]) -> dict[str, str]:
    return dict(entry.split("=", 1) for entry in container["Config"]["Env"])


def relevant(values: dict[str, Any], service: str) -> dict[str, str]:
    prefixes = (PREFIX, "POSTGRES_") if service == "database" else (PREFIX,)
    return {key: str(value) for key, value in values.items() if key.startswith(prefixes)}


def containers_by_service(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in items:
        labels = item["Config"]["Labels"]
        service = labels["com.docker.compose.service"]
        require(labels["com.docker.compose.project"] == PROJECT, "Unexpected Compose project")
        require(service in SERVICES and service not in result, "Unexpected/duplicate service")
        require(item["Name"] == f"/{PROJECT}-{service}-1", "Unexpected container name")
        require(item["State"]["Running"], f"Service is not running: {service}")
        result[service] = item
    require(set(result) == set(SERVICES), "Expected exactly four existing services")
    return result


def mount(container: dict[str, Any], kind: str, target: str, writable: bool) -> dict[str, Any]:
    mounts = container["Mounts"]
    require(len(mounts) == 1, "Unexpected number of data mounts")
    value: dict[str, Any] = mounts[0]
    require(
        value["Type"] == kind and value["Destination"] == target and value["RW"] == writable,
        "Unexpected data mount or permissions",
    )
    return value


def validate_runtime(containers: dict[str, dict[str, Any]]) -> None:
    for service, container in containers.items():
        host = container["HostConfig"]
        renderer = service == "issuer-renderer"
        require(not host["Privileged"], f"Privileged service: {service}")
        require(not host.get("CapAdd") and not host.get("Devices"), "Unexpected extra privileges")
        require(host["ReadonlyRootfs"] == renderer, f"Unexpected root filesystem: {service}")
        require(set(host.get("CapDrop") or []) == ({"ALL"} if renderer else set()), "CapDrop drift")
        for key, expected in {
            "Memory": 1073741824 if renderer else 0,
            "NanoCpus": 1000000000 if renderer else 0,
            "PidsLimit": 256 if renderer else 0,
            "ShmSize": 268435456 if renderer else 67108864,
        }.items():
            require((host.get(key) or 0) == expected, f"Resource drift: {service}/{key}")
        security = host.get("SecurityOpt") or []
        require(not any("unconfined" in entry for entry in security), "Unconfined security profile")
        if renderer:
            require(
                any(entry in ("no-new-privileges", "no-new-privileges:true") for entry in security),
                "Renderer must retain no-new-privileges",
            )
            require(any(entry.startswith("seccomp=") for entry in security), "Missing seccomp")
            require(container["Config"]["User"] == "pwuser", "Unexpected renderer user")
        else:
            require(not security, f"Unreviewed security options: {service}")
    require(containers["backend"]["Config"]["User"] == "app", "Unexpected backend user")
    require(not containers["frontend"]["Mounts"], "Unexpected frontend mounts")
    mount(containers["backend"], "bind", "/var/lib/trading-workspace/xstu", False)
    for service, volume, target in (
        ("database", "postgres-data", "/var/lib/postgresql/data"),
        ("issuer-renderer", "issuer-consent-state", "/state"),
    ):
        value = mount(containers[service], "volume", target, True)
        require(value["Name"] == f"{PROJECT}_{volume}", "Unexpected persistent volume")


def compose_literal(value: Any) -> Any:
    """JSON quoting does not escape Compose interpolation; double dollars as well."""
    if isinstance(value, str):
        return value.replace("$", "$$")
    if isinstance(value, dict):
        return {key: compose_literal(item) for key, item in value.items()}
    if isinstance(value, list):
        return [compose_literal(item) for item in value]
    return value


def compose_runtime(value: Any) -> Any:
    """Decode the one escaping layer added by `docker compose config` serialization.

    Docker's cmd/compose/config.go runConfig doubles every dollar after resolving
    the model, including JSON output. Inspect values have no such encoding.
    """
    if isinstance(value, str):
        return value.replace("$$", "$")
    if isinstance(value, dict):
        return {key: compose_runtime(item) for key, item in value.items()}
    if isinstance(value, list):
        return [compose_runtime(item) for item in value]
    return value


def make_overlay(
    items: list[dict[str, Any]], base: dict[str, Any], revision: str
) -> dict[str, Any]:
    containers = containers_by_service(items)
    validate_runtime(containers)
    require(
        len(revision) == 40 and all(c in "0123456789abcdef" for c in revision), "Invalid commit"
    )
    current = relevant(environment(containers["backend"]), "backend")
    configured = relevant(compose_runtime(base)["services"]["backend"]["environment"], "backend")
    differences = {
        key for key in current.keys() | configured.keys() if current.get(key) != configured.get(key)
    }
    require(
        differences <= PRESERVED_KEYS,
        "Unreviewed backend settings differ from base: "
        + ", ".join(sorted(differences - PRESERVED_KEYS)),
    )
    require(current.keys() >= PRESERVED_KEYS, "Missing legacy settings")
    stuttgart = containers["backend"]["Mounts"][0]["Source"]
    require(stuttgart.startswith("/"), "Stuttgart source must be absolute")
    services: dict[str, Any] = {
        service: {
            "image": f"{PROJECT}-{service}:migration-{revision}",
            "build": {"labels": {"org.opencontainers.image.revision": revision}},
        }
        for service in ("backend", "frontend", "issuer-renderer")
    }
    services["backend"].update(
        {
            "environment": {key: current[key] for key in sorted(PRESERVED_KEYS)},
            "volumes": [
                {
                    "type": "bind",
                    "source": stuttgart,
                    "target": "/var/lib/trading-workspace/xstu",
                    "read_only": True,
                    "bind": {"create_host_path": False},
                }
            ],
        }
    )
    overlay = {
        "services": services,
        "volumes": {
            name: {"external": True, "name": f"{PROJECT}_{name}"}
            for name in ("postgres-data", "issuer-consent-state")
        },
    }
    return {key: compose_literal(value) for key, value in overlay.items()}


def validate_candidate(items: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    candidate = compose_runtime(candidate)
    containers = containers_by_service(items)
    validate_runtime(containers)
    require(candidate["name"] == PROJECT, "Target project differs")
    require(set(candidate["services"]) == set(SERVICES), "Unexpected target services")
    for service, container in containers.items():
        target = candidate["services"][service]
        host = container["HostConfig"]
        require(
            target.get("read_only", False) == host["ReadonlyRootfs"],
            "Target root filesystem differs",
        )
        require(
            not target.get("privileged")
            and not target.get("cap_add")
            and not target.get("devices"),
            "Target adds privileges",
        )
        require(
            set(target.get("cap_drop", [])) == set(host.get("CapDrop") or []),
            "Target capabilities differ",
        )
        for key, actual, default in (
            ("mem_limit", host["Memory"], 0),
            ("pids_limit", host.get("PidsLimit") or 0, 0),
            ("shm_size", host["ShmSize"], 67108864),
        ):
            require(
                int(target.get(key, default)) == actual, f"Target resource differs: {service}/{key}"
            )
        require(
            float(target.get("cpus", 0)) * 1000000000 == host["NanoCpus"],
            "Target CPU limit differs",
        )
        current = relevant(environment(container), service)
        proposed = relevant(target.get("environment", {}), service)
        changed = {
            key for key in current.keys() | proposed.keys() if current.get(key) != proposed.get(key)
        }
        require(not changed, f"Target environment differs: {service}/" + ", ".join(sorted(changed)))
        current_ports = {
            (port, binding.get("HostIp") or "", binding["HostPort"])
            for port, bindings in (container["HostConfig"].get("PortBindings") or {}).items()
            for binding in (bindings or [])
        }
        proposed_ports = {
            (
                f"{entry['target']}/{entry.get('protocol', 'tcp')}",
                entry.get("host_ip") or "",
                str(entry["published"]),
            )
            for entry in target.get("ports", [])
        }
        require(current_ports == proposed_ports, f"Published ports differ: {service}")
        current_mounts = {
            (
                m["Type"],
                m.get("Name") if m["Type"] == "volume" else m["Source"],
                m["Destination"],
                m["RW"],
            )
            for m in container["Mounts"]
        }
        proposed_mounts = set()
        for entry in target.get("volumes", []):
            source = entry["source"]
            if entry["type"] == "volume":
                volume = candidate["volumes"][source]
                require(volume.get("external") is True, "Persistent volumes must be external")
                source = volume["name"]
            proposed_mounts.add(
                (entry["type"], source, entry["target"], not entry.get("read_only", False))
            )
        require(current_mounts == proposed_mounts, f"Data bindings differ: {service}")
    renderer = candidate["services"]["issuer-renderer"]
    require(renderer["read_only"] and renderer["user"] == "pwuser", "Renderer isolation differs")
    require(
        set(renderer["cap_drop"]) == {"ALL"} and not renderer.get("privileged", False),
        "Renderer privileges differ",
    )
    require(
        int(renderer["mem_limit"]) == 1073741824
        and float(renderer["cpus"]) == 1.0
        and int(renderer["pids_limit"]) == 256
        and int(renderer["shm_size"]) == 268435456,
        "Renderer resource limits differ",
    )
    security = renderer["security_opt"]
    require(
        "no-new-privileges:true" in security
        and any(item.startswith("seccomp=") for item in security)
        and not any("unconfined" in item for item in security),
        "Renderer sandbox differs",
    )


def verify_identity(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> None:
    expected = containers_by_service(before)
    actual = containers_by_service(after)
    for service in SERVICES:
        require(
            all(
                expected[service][key] == actual[service][key]
                for key in ("Id", "Image", "Config", "HostConfig", "Mounts")
            ),
            f"Running deployment changed since preparation: {service}",
        )


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous JSON without exposing a duplicate key or its value."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def verify_configuration(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Ignore JSON presentation only; retain scalar types and array ordering."""
    require(isinstance(before, dict) and isinstance(after, dict), "Expected Compose objects")
    expected = json.dumps(before, sort_keys=True, separators=(",", ":"), allow_nan=False)
    actual = json.dumps(after, sort_keys=True, separators=(",", ":"), allow_nan=False)
    require(expected == actual, "Effective Compose configuration changed")


def main() -> int:
    try:
        payload = json.load(sys.stdin, object_pairs_hook=unique_object)
        mode = sys.argv[1]
        if mode == "overlay":
            print(json.dumps(make_overlay(payload[0], payload[1], sys.argv[2]), indent=2))
        elif mode == "validate":
            validate_candidate(payload[0], payload[1])
        elif mode == "identity":
            verify_identity(payload[0], payload[1])
        elif mode == "config":
            verify_configuration(payload[0], payload[1])
        else:
            raise ValueError("Unknown validation mode")
    except DeploymentError as exc:
        print(f"Deployment validation failed: {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, TypeError, IndexError):
        # Input includes secrets. Never render exception text or the offending value.
        print(
            "Deployment validation failed; inspect private inputs locally. No values printed.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
