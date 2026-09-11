from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPOSITORY_ROOT / "docker" / "compose.yml"
ENV_EXAMPLE = REPOSITORY_ROOT / "docker" / ".env.example"
BACKEND_DOCKERFILE = REPOSITORY_ROOT / "backend" / "Dockerfile"


def test_backend_container_database_url_is_isolated_from_host_application_env() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")

    assert (
        "TRADING_WORKSPACE_DATABASE_URL: ${TRADING_WORKSPACE_DATABASE_URL" not in compose
    )
    assert "TRADING_WORKSPACE_DOCKER_DATABASE_URL" in compose
    assert "@database:5432/" in compose


def test_docker_env_example_uses_dedicated_database_override() -> None:
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "TRADING_WORKSPACE_DOCKER_DATABASE_URL=" in env_example
    assert "\nTRADING_WORKSPACE_DATABASE_URL=" not in env_example


def test_backend_container_healthcheck_requires_database_readiness() -> None:
    dockerfile = BACKEND_DOCKERFILE.read_text(encoding="utf-8")

    assert "http://127.0.0.1:8000/health/ready" in dockerfile
    assert "http://127.0.0.1:8000/health'" not in dockerfile
