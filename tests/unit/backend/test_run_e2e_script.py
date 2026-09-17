"""Guard the local E2E runner against reusing persistent runtime resources."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "run-e2e.sh"


def test_run_e2e_uses_isolated_compose_project_and_ports() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'compose_project="trading-workspace-e2e"' in script
    assert '--project-name "${compose_project}"' in script
    assert 'postgres_port="${E2E_POSTGRES_PORT:-25432}"' in script
    assert 'backend_port="${E2E_BACKEND_PORT:-28000}"' in script
    assert 'frontend_port="${E2E_FRONTEND_PORT:-28080}"' in script
    assert 'VITE_API_BASE_URL="${vite_api_base_url}"' in script
    assert 'PLAYWRIGHT_BASE_URL="${playwright_base_url}"' in script

    # Volume cleanup is allowed only through the isolated Compose wrapper.
    assert "compose down --volumes --remove-orphans" in script
    assert 'docker compose -f "${compose_file}" down --volumes' not in script
