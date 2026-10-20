"""Negative qualification cases: a green command is not proof of the learning journeys."""

from __future__ import annotations

import copy
import importlib.util
import os
import subprocess
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPORT = load("journal_report", "scripts/check-journal-e2e-report.py")
STACK = load("journal_stack", "tests/e2e/support/journal_stack_contract.py")
DATABASE = load("journal_database", "tests/e2e/support/journal_database_guard.py")
RUN = "00000000-0000-4000-8000-000000000123"
PROJECT = "tw-journal-evidence-e2e-" + UUID(RUN).hex
SOURCE = "/synthetic-empty/source"
DB_NAME = "trading_workspace_test_journal_" + UUID(RUN).hex
CONTAINER_URL = f"postgresql+asyncpg://tw_journal_e2e:synthetic@database:5432/{DB_NAME}"
HOST_URL = f"postgresql+asyncpg://tw_journal_e2e:synthetic@127.0.0.1:25432/{DB_NAME}"


def report(*, discovery=False):
    specs = []
    for index, (filename, title) in enumerate(sorted(REPORT.EXPECTED)):
        specs.append(
            {
                "file": filename,
                "title": title,
                "id": f"stable-test-{index}",
                "ok": True,
                "tests": [
                    {
                        "projectName": "chromium",
                        "expectedStatus": "passed",
                        "status": "expected",
                        "results": (
                            [] if discovery else [{"status": "passed", "retry": 0, "errors": []}]
                        ),
                    }
                ],
            }
        )
    return {
        "suites": [{"suites": [{"specs": specs}]}],
        "errors": [],
        "stats": {"expected": 2, "unexpected": 0, "skipped": 0, "flaky": 0},
    }


def first_spec(value):
    return value["suites"][0]["suites"][0]["specs"][0]


def test_exact_two_discovered_journeys_pass_once():
    manifest = REPORT.record_discovery(report(discovery=True))
    REPORT.check_results(report(), manifest)


@pytest.mark.parametrize(
    "defect",
    [
        "empty",
        "missing",
        "extra",
        "wrong_file",
        "wrong_title",
        "wrong_project",
        "duplicate_id",
        "changed_id",
        "global_error",
        "skipped",
        "flaky",
        "expected_failure",
        "failed",
        "retry",
        "second_attempt",
        "no_attempt",
        "attempt_error",
        "stats_lie",
    ],
)
def test_report_rejects_incomplete_or_retried_evidence(defect):
    value = report()
    spec = first_spec(value)
    test = spec["tests"][0]
    specs = value["suites"][0]["suites"][0]["specs"]
    if defect == "empty":
        specs.clear()
    elif defect == "missing":
        specs.pop()
    elif defect == "extra":
        specs.append(copy.deepcopy(spec))
    elif defect == "wrong_file":
        spec["file"] = "some-other-journey.spec.ts"
    elif defect == "wrong_title":
        spec["title"] = "A different passing test"
    elif defect == "wrong_project":
        test["projectName"] = "webkit"
    elif defect == "duplicate_id":
        specs[1]["id"] = spec["id"]
    elif defect == "changed_id":
        spec["id"] = "different-after-discovery"
    elif defect == "global_error":
        value["errors"] = [{"message": "worker teardown failed"}]
    elif defect in ("skipped", "flaky"):
        test["status"] = defect
    elif defect == "expected_failure":
        test["expectedStatus"] = "failed"
    elif defect == "failed":
        test["results"][0]["status"] = "failed"
    elif defect == "retry":
        test["results"][0]["retry"] = 1
    elif defect == "second_attempt":
        test["results"].append(copy.deepcopy(test["results"][0]))
    elif defect == "no_attempt":
        test["results"].clear()
    elif defect == "attempt_error":
        test["results"][0]["errors"] = [{"message": "unexpected error"}]
    elif defect == "stats_lie":
        value["stats"]["skipped"] = 1
    with pytest.raises(ValueError):
        REPORT.check_results(value, REPORT.record_discovery(report(discovery=True)))


def test_discovery_cannot_be_reconstructed_from_an_executed_report():
    with pytest.raises(ValueError, match="precede execution"):
        REPORT.record_discovery(report())


def labels(service=None):
    value = {"com.docker.compose.project": PROJECT, STACK.RUN_LABEL: RUN}
    if service:
        value["com.docker.compose.service"] = service
    return value


def environment():
    return {
        "TRADING_WORKSPACE_DATABASE_URL": CONTAINER_URL,
        "TRADING_WORKSPACE_ENVIRONMENT": "test",
        "TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED": "false",
        "TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED": "false",
        "TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__BOT_TOKEN": "",
    }


def resources():
    networks = [
        {
            "Name": PROJECT + "_" + name,
            "Id": "id-" + name,
            "Internal": internal,
            "Driver": "bridge",
            "Labels": labels(),
        }
        for name, internal in (("default", True), ("ingress", False))
    ]
    volumes = [{"Name": PROJECT + "_postgres-data", "Driver": "local", "Labels": labels()}]
    containers = []
    for service in ("database", "backend", "frontend"):
        expected = ["default"] if service == "backend" else ["default", "ingress"]
        ports = {
            "database": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "25432"}]},
            "backend": {},
            "frontend": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]},
        }
        mounts = {
            "database": [{"Type": "volume", "Name": PROJECT + "_postgres-data"}],
            "backend": [{"Type": "bind", "Source": SOURCE, "RW": False}],
            "frontend": [],
        }
        containers.append(
            {
                "Id": "container-" + service,
                "Image": "synthetic-image-id",
                "Config": {
                    "Labels": labels(service),
                    "Env": [f"{key}={value}" for key, value in environment().items()],
                },
                "HostConfig": {"Privileged": False},
                "Mounts": mounts[service],
                "NetworkSettings": {
                    "Networks": {
                        PROJECT + "_" + name: {"NetworkID": "id-" + name} for name in expected
                    },
                    "Ports": ports[service],
                },
                "State": {"Running": True, "Health": {"Status": "healthy"}},
            }
        )
    return containers, networks, volumes


def test_runtime_accepts_only_the_expected_live_project():
    evidence = STACK.runtime(*resources(), PROJECT, RUN, SOURCE, CONTAINER_URL)
    assert set(evidence["services"]) == {"database", "backend", "frontend"}
    assert evidence["networks"]["default"]["internal"]


def compose_configuration():
    config = {
        "name": PROJECT,
        "volumes": {"postgres-data": {"name": PROJECT + "_postgres-data", "labels": labels()}},
        "networks": {
            name: {"name": PROJECT + "_" + name, "internal": internal, "labels": labels()}
            for name, internal in (("default", True), ("ingress", False))
        },
        "services": {},
    }
    for service in ("database", "backend", "frontend"):
        config["services"][service] = {
            "labels": labels(service),
            "networks": {"default": {}} if service == "backend" else {"default": {}, "ingress": {}},
        }
    database = config["services"]["database"]
    database["ports"] = [{"host_ip": "127.0.0.1", "target": 5432, "published": "25432"}]
    database["volumes"] = [{"type": "volume", "source": "postgres-data"}]
    backend = config["services"]["backend"]
    backend["volumes"] = [{"type": "bind", "source": SOURCE, "read_only": True}]
    backend["environment"] = environment()
    frontend = config["services"]["frontend"]
    frontend["ports"] = [{"host_ip": "127.0.0.1", "target": 8080, "published": "8080"}]
    frontend["build"] = {"args": {"VITE_API_BASE_URL": "http://localhost:8080/api"}}
    return config


def test_valid_compose_contract_precedes_creation():
    STACK.configuration(compose_configuration(), PROJECT, RUN, SOURCE, CONTAINER_URL)


@pytest.mark.parametrize(
    "defect",
    [
        "origin",
        "foreign_mount",
        "external_volume",
        "provider",
        "secret",
        "port",
        "network",
    ],
)
def test_compose_guard_rejects_unsafe_configuration_before_creation(defect):
    value = compose_configuration()
    backend = value["services"]["backend"]
    if defect == "origin":
        value["services"]["frontend"]["build"]["args"][
            "VITE_API_BASE_URL"
        ] = "http://127.0.0.1:8080/api"
    elif defect == "foreign_mount":
        backend["volumes"][0]["source"] = "/user/private"
    elif defect == "external_volume":
        value["volumes"]["postgres-data"]["external"] = True
    elif defect == "provider":
        backend["environment"]["TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED"] = "true"
    elif defect == "secret":
        value["secrets"] = {"private": {"file": "/user/credentials"}}
    elif defect == "port":
        value["services"]["database"]["ports"][0]["host_ip"] = "0.0.0.0"
    elif defect == "network":
        backend["networks"]["ingress"] = {}
    with pytest.raises(ValueError):
        STACK.configuration(value, PROJECT, RUN, SOURCE, CONTAINER_URL)


@pytest.mark.parametrize(
    "defect",
    [
        "run_label",
        "foreign_project",
        "volume",
        "extra_network",
        "backend_egress",
        "wrong_network_id",
        "published_backend",
        "public_database",
        "wrong_port",
        "foreign_database",
        "provider_enabled",
        "secret",
        "private_mount",
        "unhealthy",
    ],
)
def test_runtime_rejects_unsafe_or_misidentified_targets(defect):
    containers, networks, volumes = resources()
    database, backend, frontend = containers
    if defect == "run_label":
        del networks[0]["Labels"][STACK.RUN_LABEL]
    elif defect == "foreign_project":
        volumes[0]["Labels"]["com.docker.compose.project"] = "user-stack"
    elif defect == "volume":
        database["Mounts"][0]["Name"] = "user-volume"
    elif defect == "extra_network":
        networks.append(copy.deepcopy(networks[0]))
    elif defect == "backend_egress":
        networks[0]["Internal"] = False
    elif defect == "wrong_network_id":
        backend["NetworkSettings"]["Networks"][PROJECT + "_default"]["NetworkID"] = "foreign"
    elif defect == "published_backend":
        backend["NetworkSettings"]["Ports"] = {
            "8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]
        }
    elif defect == "public_database":
        database["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostIp"] = "0.0.0.0"
    elif defect == "wrong_port":
        frontend["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"] = "38080"
    elif defect == "foreign_database":
        backend["Config"]["Env"][0] = "TRADING_WORKSPACE_DATABASE_URL=postgresql://foreign/real"
    elif defect == "provider_enabled":
        backend["Config"]["Env"].append("TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=true")
    elif defect == "secret":
        backend["Config"]["Env"].append(
            "TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__BOT_TOKEN=secret"
        )
    elif defect == "private_mount":
        backend["Mounts"][0]["Source"] = "/user/private-config"
    elif defect == "unhealthy":
        database["State"]["Health"]["Status"] = "unhealthy"
    with pytest.raises(ValueError):
        STACK.runtime(containers, networks, volumes, PROJECT, RUN, SOURCE, CONTAINER_URL)


def test_cleanup_refuses_missing_or_foreign_run_labels():
    containers, networks, volumes = resources()
    containers[0]["Config"]["Labels"][STACK.RUN_LABEL] = "a-different-run"
    with pytest.raises(ValueError, match="run label"):
        STACK.ownership(containers, networks, volumes, PROJECT, RUN)


@pytest.fixture
def target_environment(monkeypatch):
    values = {
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "JOURNAL_E2E_WRITES_ALLOWED": "1",
        "FT011_E2E_WRITES_ALLOWED": "1",
        "TRADING_WORKSPACE_ENVIRONMENT": "test",
        "JOURNAL_E2E_WORKSPACE_ID": DATABASE.WORKSPACE,
        "JOURNAL_E2E_RUN_ID": RUN,
        "TRADING_WORKSPACE_TEST_DATABASE_URL": HOST_URL,
        "TRADING_WORKSPACE_DATABASE_URL": HOST_URL,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_database_configuration_is_bound_to_the_exact_run(target_environment):
    run_id, target = DATABASE.configured_target()
    assert run_id == RUN and target.database == DB_NAME


@pytest.mark.parametrize(
    "key,value",
    [
        ("CI", "false"),
        ("GITHUB_ACTIONS", "false"),
        ("JOURNAL_E2E_WRITES_ALLOWED", "0"),
        ("FT011_E2E_WRITES_ALLOWED", "0"),
        ("TRADING_WORKSPACE_ENVIRONMENT", "production"),
        ("JOURNAL_E2E_WORKSPACE_ID", "00000000-0000-4000-8000-000000000999"),
        ("JOURNAL_E2E_RUN_ID", "00000000-0000-4000-8000-000000000999"),
        ("TRADING_WORKSPACE_TEST_DATABASE_URL", HOST_URL.replace("127.0.0.1", "remote")),
        ("TRADING_WORKSPACE_TEST_DATABASE_URL", HOST_URL.replace("25432", "5432")),
        ("TRADING_WORKSPACE_TEST_DATABASE_URL", HOST_URL.replace(DB_NAME, "trading_workspace")),
        ("TRADING_WORKSPACE_DATABASE_URL", HOST_URL.replace(DB_NAME, "foreign")),
    ],
)
def test_database_guard_rejects_config_before_connecting(
    target_environment, monkeypatch, key, value
):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        DATABASE.configured_target()


def test_runner_refuses_non_ci_context_before_any_command(tmp_path):
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/run-journal-evidence-e2e.sh")],
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)},
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert "requires its disposable GitHub Actions checkout" in result.stderr
