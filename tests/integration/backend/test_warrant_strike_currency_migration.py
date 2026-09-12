from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.database.base import Base


def test_strike_currency_migration_preserves_legacy_values_and_is_reversible() -> None:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is required")
    root = Path(__file__).resolve().parents[3]
    path = root / "backend/migrations/versions/20260912_0033_warrant_strike_currency.py"
    spec = importlib.util.spec_from_file_location("strike_currency_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    schema = "test_strike_currency_" + uuid4().hex

    def exercise(connection: Connection) -> None:
        # Never alter application tables: DDL, data and schema are rolled back.
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        connection.execute(text("CREATE TABLE currencies (code varchar(3) PRIMARY KEY)"))
        connection.execute(text("INSERT INTO currencies (code) VALUES ('EUR'), ('USD')"))
        connection.execute(
            text("CREATE TABLE warrant_terms_versions (id integer PRIMARY KEY, strike numeric)")
        )
        connection.execute(text("INSERT INTO warrant_terms_versions VALUES (1, 500)"))
        context = MigrationContext.configure(connection, opts={"target_metadata": Base.metadata})
        with Operations.context(context):
            migration.upgrade()
        old = connection.execute(
            text("SELECT strike, strike_currency_code FROM warrant_terms_versions WHERE id = 1")
        ).one()
        assert old.strike == 500
        assert old.strike_currency_code is None
        column = next(
            col
            for col in inspect(connection).get_columns("warrant_terms_versions")
            if col["name"] == "strike_currency_code"
        )
        assert column["nullable"] is True
        assert column["default"] is None
        foreign_keys = inspect(connection).get_foreign_keys("warrant_terms_versions")
        assert any(
            fk["constrained_columns"] == ["strike_currency_code"]
            and fk["referred_table"] == "currencies"
            for fk in foreign_keys
        )
        for invalid in ("ZZZ", "usd", ""):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(
                    text(
                        "INSERT INTO warrant_terms_versions (id, strike, strike_currency_code) "
                        "VALUES (2, 500, :currency)"
                    ),
                    {"currency": invalid},
                )
        connection.execute(text("INSERT INTO warrant_terms_versions VALUES (2, 500, 'USD')"))
        with Operations.context(context):
            migration.downgrade()
        assert "strike_currency_code" not in {
            col["name"] for col in inspect(connection).get_columns("warrant_terms_versions")
        }
        assert connection.execute(text("SELECT count(*) FROM warrant_terms_versions")).scalar() == 2

    async def run() -> None:
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    await connection.run_sync(exercise)
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    asyncio.run(run())
