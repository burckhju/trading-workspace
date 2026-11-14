"""Owner qualifications accept exactly the repository's current migration head."""

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID

import pytest
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[3]
RUN = "00000000-0000-4000-8000-000000000123"
WORKSPACE = "00000000-0000-4000-8000-000000000001"
CURRENT = "20261114_0051"


@pytest.fixture(params=["realized_gross", "journal", "candidate_governance"])
def guard(request, monkeypatch):
    name = request.param
    spec = importlib.util.spec_from_file_location(
        name + "_schema_guard", ROOT / f"tests/e2e/support/{name}_database_guard.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prefix, user, port, marker = {
        "realized_gross": ("tw_realized_report_e2e_", "tw_report_e2e", 35432, "realized-gross"),
        "journal": ("trading_workspace_test_journal_", "tw_journal_e2e", 25432, "journal-evidence"),
        "candidate_governance": (
            "trading_workspace_test_cg_",
            "tw_candidate_e2e",
            25432,
            "candidate-governance",
        ),
    }[name]
    database = prefix + UUID(RUN).hex
    url = f"postgresql+asyncpg://{user}:synthetic@127.0.0.1:{port}/{database}"
    variables = {
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "TRADING_WORKSPACE_ENVIRONMENT": "test",
        "TRADING_WORKSPACE_TEST_DATABASE_URL": url,
        "TRADING_WORKSPACE_DATABASE_URL": url,
        "FT011_E2E_WRITES_ALLOWED": "1",
    }
    for owner in ("REPORT", "JOURNAL", "CANDIDATE_GOVERNANCE"):
        variables.update(
            {
                f"{owner}_E2E_WRITES_ALLOWED": "1",
                f"{owner}_E2E_RUN_ID": RUN,
                f"{owner}_E2E_WORKSPACE_ID": WORKSPACE,
            }
        )
    for key, value in variables.items():
        monkeypatch.setenv(key, value)

    async def execute(statement):
        query = str(statement)
        if query.startswith("SET TRANSACTION"):
            assert query.endswith("READ ONLY")
            return None
        assert query == "SELECT current_database(), current_user, inet_server_port()"
        return Mock(one=Mock(return_value=(database, user, 5432)))

    async def scalar(statement):
        query = str(statement)
        if "shobj_description" in query:
            return f"synthetic {marker} browser {RUN}"
        if query == "SHOW server_version_num":
            return "170005"
        assert query == "SELECT version()"
        return "PostgreSQL 17.5 (synthetic unit fixture)"

    connection = Mock(execute=AsyncMock(side_effect=execute), scalar=AsyncMock(side_effect=scalar))
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=connection)
    context.__aexit__ = AsyncMock(return_value=False)
    engine = Mock(connect=Mock(return_value=context), dispose=AsyncMock())
    factory = Mock(return_value=engine)
    monkeypatch.setattr(module, "create_async_engine", factory)
    return module, connection, engine


def test_owner_guard_pin_is_exactly_the_repository_head(guard):
    module, _, _ = guard
    assert ScriptDirectory(str(ROOT / "backend/migrations")).get_heads() == [module.REVISION]


@pytest.mark.parametrize(
    "revisions",
    [
        [CURRENT],
        [],
        ["20261109_0049"],
        ["unexpected_head"],
        [CURRENT, "20261109_0049"],
        ["20261109_0049", CURRENT],
        [CURRENT, CURRENT],
    ],
)
def test_owner_guard_rejects_missing_old_or_multiple_heads(guard, revisions):
    module, connection, engine = guard

    async def scalars(statement):
        query = str(statement)
        if query == "SELECT version_num FROM alembic_version":
            values = revisions
        elif query == "SELECT id FROM workspaces":
            values = [UUID(WORKSPACE)]
        else:
            assert "pg_tables" in query or "information_schema.columns" in query
            values = []
        return Mock(all=Mock(return_value=values))

    connection.scalars = AsyncMock(side_effect=scalars)
    if revisions == [CURRENT]:
        evidence = asyncio.run(module.verify())
        assert evidence["schema_revision"] == CURRENT
        assert evidence["run_id"] == RUN
    else:
        with pytest.raises(RuntimeError, match="Unexpected or multiple migration heads"):
            asyncio.run(module.verify())
        assert connection.scalars.await_count == 1
    engine.dispose.assert_awaited_once()
    assert "READ ONLY" in str(connection.execute.await_args_list[0].args[0])
