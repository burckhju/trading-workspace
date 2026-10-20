"""No Docker daemon, provider traffic or production data is needed for these guards."""

from __future__ import annotations

import copy
import io
import json
import sys
from typing import Any

import pytest

from app.tools import legacy_issuer_deployment as migration

REVISION = "a" * 40


def deployment_fixture() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Synthetic Docker inspect and resolved Compose model, also used by real-Compose CI."""
    items = []
    services = {}
    for service in migration.SERVICES:
        renderer = service == "issuer-renderer"
        env = {}
        if service == "backend":
            env = dict.fromkeys(migration.PRESERVED_KEYS, "false")
            env.update(
                {
                    "TRADING_WORKSPACE_DATABASE_URL": "synthetic-secret=$DOLLAR",
                    "TRADING_WORKSPACE_POSITION_MONITORING__ENABLED": "false",
                }
            )
        elif service == "database":
            env = {
                "POSTGRES_PASSWORD": "synthetic-secret=$DOLLAR",
                "POSTGRES_USER": "test",
                "POSTGRES_DB": "test",
            }
        mounts = []
        target_mounts = []
        if service == "backend":
            mounts = [
                {
                    "Type": "bind",
                    "Source": "/existing path/$literal/xstu",
                    "Destination": "/var/lib/trading-workspace/xstu",
                    "RW": False,
                }
            ]
            target_mounts = [
                {
                    "type": "bind",
                    "source": mounts[0]["Source"],
                    "target": mounts[0]["Destination"],
                    "read_only": True,
                }
            ]
        elif service in ("database", "issuer-renderer"):
            volume, target = (
                ("postgres-data", "/var/lib/postgresql/data")
                if service == "database"
                else ("issuer-consent-state", "/state")
            )
            mounts = [
                {
                    "Type": "volume",
                    "Name": f"trading-workspace_{volume}",
                    "Destination": target,
                    "RW": True,
                }
            ]
            target_mounts = [{"type": "volume", "source": volume, "target": target}]
        port = {"backend": 8000, "frontend": 8080, "database": 5432}.get(service)
        host = {
            "ReadonlyRootfs": renderer,
            "Privileged": False,
            "CapDrop": ["ALL"] if renderer else None,
            "Memory": 1073741824 if renderer else 0,
            "NanoCpus": 1000000000 if renderer else 0,
            "PidsLimit": 256 if renderer else None,
            "ShmSize": 268435456 if renderer else 67108864,
            "SecurityOpt": (
                ["no-new-privileges:true", "seccomp=synthetic-profile"] if renderer else None
            ),
            "PortBindings": (
                {f"{port}/tcp": [{"HostIp": "", "HostPort": str(port)}]} if port else {}
            ),
        }
        user = "pwuser" if renderer else ("app" if service == "backend" else "")
        items.append(
            {
                "Name": f"/trading-workspace-{service}-1",
                "Id": f"id-{service}",
                "Image": f"sha256:old-{service}",
                "State": {"Running": True},
                "Mounts": mounts,
                "HostConfig": host,
                "Config": {
                    "User": user,
                    "Env": [f"{k}={v}" for k, v in env.items()],
                    "Labels": {
                        "com.docker.compose.project": "trading-workspace",
                        "com.docker.compose.service": service,
                    },
                },
            }
        )
        target_service: dict[str, Any] = {
            "environment": env,
            "volumes": target_mounts,
            "ports": [{"target": port, "published": str(port)}] if port else [],
        }
        if renderer:
            target_service.update(
                {
                    "user": "pwuser",
                    "read_only": True,
                    "cap_drop": ["ALL"],
                    "mem_limit": "1073741824",
                    "cpus": 1.0,
                    "pids_limit": 256,
                    "shm_size": "268435456",
                    "security_opt": host["SecurityOpt"],
                }
            )
        services[service] = target_service
    model = {
        "name": "trading-workspace",
        "services": services,
        "volumes": {
            name: {"name": f"trading-workspace_{name}", "external": True}
            for name in ("postgres-data", "issuer-consent-state")
        },
    }

    return items, migration.compose_literal(model)


def test_overlay_preserves_false_flags_and_literal_paths_without_copying_secrets() -> None:
    items, base = deployment_fixture()
    overlay = migration.make_overlay(items, base, REVISION)
    assert set(overlay["services"]["backend"]["environment"]) == migration.PRESERVED_KEYS
    assert set(overlay["services"]["backend"]["environment"].values()) == {"false"}
    assert "synthetic-secret" not in json.dumps(overlay)
    assert overlay["services"]["backend"]["volumes"][0]["source"] == "/existing path/$$literal/xstu"
    assert not overlay["services"]["backend"]["volumes"][0]["bind"]["create_host_path"]
    assert overlay["volumes"]["postgres-data"] == {
        "external": True,
        "name": "trading-workspace_postgres-data",
    }
    assert REVISION in overlay["services"]["backend"]["image"]
    migration.validate_candidate(items, base)
    migration.verify_identity(items, copy.deepcopy(items))


@pytest.mark.parametrize(
    "kind", ["env", "missing-setting", "revision", "project", "duplicate", "stopped", "name"]
)
def test_unreviewed_baselines_are_rejected(kind: str) -> None:
    items, base = deployment_fixture()
    revision = REVISION
    if kind == "env":
        items[0]["Config"]["Env"].append("TRADING_WORKSPACE_UNREVIEWED=secret-value")
    elif kind == "missing-setting":
        items[0]["Config"]["Env"].pop(0)
    elif kind == "revision":
        revision = "not-a-commit"
    elif kind == "project":
        items[0]["Config"]["Labels"]["com.docker.compose.project"] = "another-project"
    elif kind == "duplicate":
        items.append(copy.deepcopy(items[0]))
    elif kind == "stopped":
        items[0]["State"]["Running"] = False
    elif kind == "name":
        items[0]["Name"] = "/another-name"
    with pytest.raises(migration.DeploymentError) as error:
        migration.make_overlay(items, base, revision)
    assert "secret-value" not in str(error.value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("Privileged", True),
        ("CapAdd", ["SYS_ADMIN"]),
        ("Devices", ["device"]),
        ("ReadonlyRootfs", False),
        ("CapDrop", []),
        ("Memory", 0),
        ("NanoCpus", 0),
        ("PidsLimit", 0),
        ("ShmSize", 67108864),
        ("SecurityOpt", ["seccomp=unconfined"]),
        ("SecurityOpt", ["seccomp=profile"]),
        ("SecurityOpt", ["no-new-privileges:true"]),
    ],
)
def test_renderer_restrictions_cannot_be_lost(field: str, value: Any) -> None:
    items, base = deployment_fixture()
    items[1]["HostConfig"][field] = value
    with pytest.raises(migration.DeploymentError):
        migration.make_overlay(items, base, REVISION)


@pytest.mark.parametrize(
    "kind",
    ["mount", "volume", "port", "env", "external", "limits", "sandbox", "cap", "rootfs", "cpu"],
)
def test_target_drift_is_rejected(kind: str) -> None:
    items, target = deployment_fixture()
    backend = target["services"]["backend"]
    renderer = target["services"]["issuer-renderer"]
    if kind == "mount":
        backend["volumes"][0]["source"] = "/empty-new-directory"
    elif kind == "volume":
        target["volumes"]["postgres-data"]["name"] = "wrong-data"
    elif kind == "port":
        backend["ports"][0]["published"] = "9000"
    elif kind == "env":
        backend["environment"]["TRADING_WORKSPACE_DATABASE_URL"] = "wrong-secret"
    elif kind == "external":
        target["volumes"]["issuer-consent-state"]["external"] = False
    elif kind == "limits":
        renderer["mem_limit"] = 0
    elif kind == "sandbox":
        renderer["security_opt"] = ["seccomp=unconfined"]
    elif kind == "cap":
        renderer["cap_add"] = ["SYS_ADMIN"]
    elif kind == "rootfs":
        renderer["read_only"] = False
    elif kind == "cpu":
        renderer["cpus"] = 4
    with pytest.raises(migration.DeploymentError):
        migration.validate_candidate(items, target)


@pytest.mark.parametrize("field", ["Id", "Image", "Config", "HostConfig", "Mounts"])
def test_apply_requires_unchanged_prepared_containers(field: str) -> None:
    items, _ = deployment_fixture()
    current = copy.deepcopy(items)
    if field in ("Id", "Image"):
        current[0][field] = "changed"
    elif field in ("Config", "HostConfig"):
        current[0][field]["changed"] = True
    else:
        current[0][field].append({"changed": True})
    with pytest.raises(migration.DeploymentError, match="changed since preparation"):
        migration.verify_identity(items, current)


@pytest.mark.parametrize(
    "mode",
    [
        "overlay",
        "validate",
        "identity",
        "unknown",
        "invalid-json",
        "invalid-input",
        "invalid-target",
    ],
)
def test_cli_reports_no_private_values(
    mode: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    items, base = deployment_fixture()
    payload: Any = [items, items if mode == "identity" else base]
    if mode == "invalid-target":
        payload[1]["services"]["backend"]["environment"][
            "TRADING_WORKSPACE_DATABASE_URL"
        ] = "secret-new"
    if mode == "invalid-input":
        payload = {"synthetic-secret": "private"}
    monkeypatch.setattr(
        sys, "stdin", io.StringIO("not-json" if mode == "invalid-json" else json.dumps(payload))
    )
    monkeypatch.setattr(
        sys, "argv", ["validator", "validate" if mode.startswith("invalid") else mode, REVISION]
    )
    result = migration.main()
    out = capsys.readouterr()
    assert result == (0 if mode in ("overlay", "validate", "identity") else 2)
    assert "synthetic-secret" not in out.out + out.err
    assert "secret-new" not in out.out + out.err


@pytest.mark.parametrize("literal", ["$TOKEN", "$$TOKEN", "${TOKEN}", "$", "a$$$b"])
def test_compose_serialization_is_decoded_once_without_interpreting_variables(literal: str) -> None:
    items, candidate = deployment_fixture()
    key = "TRADING_WORKSPACE_DATABASE_URL"
    items[0]["Config"]["Env"] = [
        entry if not entry.startswith(key + "=") else f"{key}={literal}"
        for entry in items[0]["Config"]["Env"]
    ]
    candidate["services"]["backend"]["environment"][key] = migration.compose_literal(literal)
    source = "/existing/" + literal
    items[0]["Mounts"][0]["Source"] = source
    candidate["services"]["backend"]["volumes"][0]["source"] = migration.compose_literal(source)
    migration.make_overlay(items, candidate, REVISION)
    migration.validate_candidate(items, candidate)


@pytest.mark.parametrize(
    "before,after",
    [
        ({"flag": False}, {"flag": 0}),
        ({"count": 1}, {"count": 1.0}),
        ({"limit": "256"}, {"limit": 256}),
        ({"secret": "$TOKEN"}, {"secret": "$$TOKEN"}),
        ({"command": ["a", "b"]}, {"command": ["b", "a"]}),
        ({"value": None}, {}),
        ({}, {"added": "private-value"}),
        ({"flag": False}, {"flag": True}),
    ],
)
def test_configuration_comparison_preserves_values_types_and_order(
    before: dict[str, Any], after: dict[str, Any]
) -> None:
    with pytest.raises(migration.DeploymentError, match="configuration changed"):
        migration.verify_configuration(before, after)


@pytest.mark.parametrize(
    "payload,success",
    [
        ('[{"b":2,"a":{"x":"\\u00e4"}}, {"a":{"x":"ä"},"b":2}]', True),
        ('[{"secret":"private-value"},{"secret":"private-changed"}]', False),
        ('[{"flag":false,"flag":true},{"flag":true}]', False),
        ('[{"value":NaN},{"value":NaN}]', False),
        ('[{"value":Infinity},{"value":Infinity}]', False),
        ("[[],[]]", False),
        ("private-invalid-json", False),
    ],
)
def test_configuration_cli_ignores_presentation_and_rejects_ambiguous_inputs(
    payload: str,
    success: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    monkeypatch.setattr(sys, "argv", ["validator", "config"])
    assert migration.main() == (0 if success else 2)
    output = capsys.readouterr()
    assert "private-" not in output.out + output.err
