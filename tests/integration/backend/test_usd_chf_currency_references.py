"""Real migrations and REST writes; only disposable test databases are modified."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Environment, Settings
from app.database.dependencies import get_database_session
from app.main import create_application

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS_REVISION = "20260912_0033"


def _migrate(url: str, revision: str, *, action: str = "upgrade") -> None:
    env = dict(os.environ)
    env["TRADING_WORKSPACE_DATABASE_URL"] = url
    env["TRADING_WORKSPACE_TEST_DATABASE_URL"] = url
    env["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + str(ROOT)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", action, revision],
        cwd=ROOT / "backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = (result.stdout + result.stderr).replace(url, "<REDACTED_DATABASE_URL>")
    password = make_url(url).password
    if password:
        output = output.replace(password, "<REDACTED>")
    assert result.returncode == 0, output


@pytest.fixture
def currency_database() -> Iterator[str]:
    configured = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is required")
    base_url = make_url(configured).set(drivername="postgresql+asyncpg")
    name = "tw_currency_ref_test_" + uuid4().hex
    url = base_url.set(database=name).render_as_string(hide_password=False)

    async def database_ddl(*, create: bool) -> None:
        engine = create_async_engine(base_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                # The name is generated here, never taken from user/configured database names.
                command = f'CREATE DATABASE "{name}"' if create else f'DROP DATABASE "{name}"'
                await connection.execute(text(command))
        finally:
            await engine.dispose()

    asyncio.run(database_ddl(create=True))
    try:
        # Run the actual complete released migration chain, not create_all or currency fixtures.
        _migrate(url, PREVIOUS_REVISION)
        yield url
    finally:
        asyncio.run(database_ddl(create=False))


@asynccontextmanager
async def _client(url: str) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def session_dependency() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    app = create_application(
        Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url=url,
            documentation_enabled=True,
            log_level="CRITICAL",
        )
    )
    app.dependency_overrides[get_database_session] = session_dependency
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _product_payload(client: AsyncClient) -> dict[str, object]:
    issuers = await client.post(
        "/api/v1/market-reference-data/issuers",
        json={"legal_name": "Currency Test AG", "display_name": "Currency Test"},
    )
    assert issuers.status_code == 201, issuers.text
    venues = await client.get("/api/v1/market-reference-data/trading-venues")
    assert venues.status_code == 200, venues.text
    venue = next(item for item in venues.json()["items"] if item["mic"] == "XETR")
    underlying = await client.post(
        "/api/v1/underlyings",
        json={
            "name": "Currency Reference Test Stock",
            "type": "STOCK",
            "primary_listing": {
                "trading_venue_id": venue["id"],
                "ticker": "CURRENCYTEST",
                "currency_code": "EUR",
            },
        },
    )
    assert underlying.status_code == 201, underlying.text
    return {
        "issuer_id": issuers.json()["id"],
        "underlying_id": underlying.json()["id"],
        "display_name": "Currency Test Call",
        "option_direction": "CALL",
        "strike": "500",
        "maturity_date": "2099-12-31",
        "ratio": "0.1",
    }


def test_fresh_migrations_make_usd_chf_available_for_real_warrant_writes(
    currency_database: str,
) -> None:
    async def exercise() -> None:
        async with _client(currency_database) as client:
            before = await client.get("/api/v1/market-reference-data/currencies")
            assert before.status_code == 200, before.text
            assert {item["code"] for item in before.json()["items"]} == {"EUR"}
            payload = await _product_payload(client)
            legacy = await client.post("/api/v1/warrants", json=payload)
            assert legacy.status_code == 201, legacy.text
            legacy_id = legacy.json()["id"]
            terms_url = f"/api/v1/warrants/{legacy_id}/terms"

            await asyncio.to_thread(_migrate, currency_database, "head")
            response = await client.get("/api/v1/market-reference-data/currencies")
            assert response.status_code == 200, response.text
            references = {item["code"]: item for item in response.json()["items"]}
            assert set(references) == {"EUR", "USD", "CHF"}
            assert references["EUR"] == before.json()["items"][0]
            for code in ("USD", "CHF"):
                assert references[code]["minor_unit"] == 2
                created = await client.post(
                    "/api/v1/warrants", json={**payload, "strike_currency_code": code.lower()}
                )
                assert created.status_code == 201, created.text
                history = await client.get(f"/api/v1/warrants/{created.json()['id']}/terms")
                assert history.status_code == 200, history.text
                assert history.json()[0]["strike_currency_code"] == code

            # No automatic assignment of a currency to the pre-existing terms.
            history = await client.get(terms_url)
            assert history.json()[0]["strike_currency_code"] is None
            venues = await client.get("/api/v1/market-reference-data/trading-venues")
            venue = next(item for item in venues.json()["items"] if item["mic"] == "XETR")
            listing = await client.post(
                f"/api/v1/warrants/{legacy_id}/listings",
                json={
                    "trading_venue_id": venue["id"],
                    "symbol": None,
                    "quotation_currency_code": "EUR",
                },
            )
            assert listing.status_code == 201, listing.text
            for version, code in enumerate(("USD", "CHF"), start=1):
                updated = await client.post(
                    terms_url,
                    json={
                        "expected_version": version,
                        "option_direction": "CALL",
                        "strike": "500",
                        "maturity_date": "2099-12-31",
                        "ratio": "0.1",
                        "strike_currency_code": code,
                    },
                )
                assert updated.status_code == 201, updated.text
            history = (await client.get(terms_url)).json()
            assert [item["strike_currency_code"] for item in history] == [None, "USD", "CHF"]
            assert sum(item["effective_to"] is None for item in history) == 1
            listings = (await client.get(f"/api/v1/warrants/{legacy_id}/listings")).json()
            assert listings[0]["quotation_currency_code"] == "EUR"

            rejected = await client.post(
                "/api/v1/warrants", json={**payload, "strike_currency_code": "ZZZ"}
            )
            assert 400 <= rejected.status_code < 500

    asyncio.run(exercise())


def test_existing_local_and_inactive_references_survive_upgrade_and_rollback(
    currency_database: str,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(currency_database, poolclass=NullPool)
        query = text("SELECT * FROM currencies ORDER BY code")
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO currencies "
                        "(code, name, minor_unit, is_active, reference_version, "
                        "created_at, updated_at) VALUES "
                        "('USD', 'Local dollar label', 2, true, 'LOCAL-USD-20260912', "
                        "'2026-09-01T00:00:00Z', '2026-09-02T00:00:00Z'), "
                        "('CHF', 'Deliberately inactive franc', 2, false, 'LOCAL-CHF', "
                        "'2026-09-01T00:00:00Z', '2026-09-02T00:00:00Z')"
                    )
                )
            async with engine.connect() as connection:
                before = (await connection.execute(query)).all()
            for action, revision in (
                ("upgrade", "head"),
                ("downgrade", PREVIOUS_REVISION),
                ("upgrade", "head"),
            ):
                await asyncio.to_thread(_migrate, currency_database, revision, action=action)
                async with engine.connect() as connection:
                    after = (await connection.execute(query)).all()
                assert after == before
            async with _client(currency_database) as client:
                response = await client.get("/api/v1/market-reference-data/currencies")
                assert {item["code"] for item in response.json()["items"]} == {"EUR", "USD"}
                payload = await _product_payload(client)
                rejected = await client.post(
                    "/api/v1/warrants", json={**payload, "strike_currency_code": "CHF"}
                )
                assert 400 <= rejected.status_code < 500
                assert "inactive" in rejected.text.lower()
        finally:
            await engine.dispose()

    asyncio.run(exercise())
