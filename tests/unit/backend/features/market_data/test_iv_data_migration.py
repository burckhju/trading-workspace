"""Execute the actual migration on SQLite; PostgreSQL trigger checks are separate."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def test_migration_roundtrip_and_refusal_to_discard_observations(monkeypatch):
    path = (
        Path(__file__).resolve().parents[5]
        / "backend/migrations/versions/20261012_0045_iv_data_evidence.py"
    )
    spec = importlib.util.spec_from_file_location("iv_data_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(connection)))
        module.upgrade()
        assert set(inspect(connection).get_table_names()) == {
            "warrant_quote_samples",
            "warrant_valuation_evidence",
        }
        module.downgrade()
        assert inspect(connection).get_table_names() == []
        module.upgrade()
        row = dict(
            id=uuid4().hex,
            workspace=uuid4().hex,
            warrant=uuid4().hex,
            listing=uuid4().hex,
            identity="a" * 64,
        )
        statement = text(
            "INSERT INTO warrant_quote_samples (id,workspace_id,warrant_id,warrant_listing_id,"
            "provider,identity_key,isin,slot_at,day_utc,captured_at,status,payload) VALUES "
            "(:id,:workspace,:warrant,:listing,'FRANKFURT_QUOTES',:identity,'DE000VH2LU21',"
            "'2026-10-12 10:00:00','2026-10-12','2026-10-12 10:01:00','NO_QUOTE','{}')"
        )
        connection.execute(statement, row)
        with pytest.raises(IntegrityError):
            connection.execute(statement, {**row, "id": uuid4().hex})
        with pytest.raises(RuntimeError, match="immutable IV data evidence exists"):
            module.downgrade()
        assert connection.scalar(text("SELECT count(*) FROM warrant_quote_samples")) == 1
