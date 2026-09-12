"""Actual PostgreSQL constraints/transactions for explicit Frankfurt mapping setup."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW

from app.providers.frankfurt_quotes.configure import configure_warrant
from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice


@pytest.mark.asyncio
async def test_setup_dry_run_apply_idempotency_and_conflict_with_real_constraints():
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    assert url.split("?", 1)[0].rsplit("/", 1)[-1] == "trading_workspace_test"
    engine = create_async_engine(url)
    workspace, warrant, issuer, underlying = (uuid4() for _ in range(4))
    client = SimpleNamespace(
        settings=public_settings(),
        load_public=AsyncMock(
            return_value=(FrankfurtPublicPrice.model_validate(wire()), NOW, False)
        ),
    )
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                params = dict(
                    workspace=workspace,
                    warrant=warrant,
                    issuer=issuer,
                    underlying=underlying,
                    now=NOW,
                )
                await connection.execute(
                    text(
                        "INSERT INTO workspaces (id, name, created_at) "
                        "VALUES (:workspace, 'Frankfurt test', :now)"
                    ),
                    params,
                )
                await connection.execute(
                    text(
                        "INSERT INTO issuers (id, legal_name, display_name, is_active, "
                        "version, created_at, updated_at) "
                        "VALUES (:issuer, :name, 'Frankfurt test', true, 1, :now, :now)"
                    ),
                    {**params, "name": f"Frankfurt test {issuer}"},
                )
                await connection.execute(
                    text(
                        "INSERT INTO underlyings (id, workspace_id, type, name, "
                        "lifecycle_status, quality_status, "
                        "version, created_at, updated_at, data_origin) VALUES "
                        "(:underlying, :workspace, 'STOCK', 'Frankfurt test', 'ACTIVE', "
                        "'VERIFIED', 1, :now, :now, 'MANUAL')"
                    ),
                    params,
                )
                await connection.execute(
                    text(
                        "INSERT INTO warrants (id, workspace_id, issuer_id, underlying_id, "
                        "product_family, display_name, "
                        "isin, wkn, lifecycle_status, version, created_at, updated_at) VALUES "
                        "(:warrant, :workspace, :issuer, :underlying, 'WARRANT', 'Frankfurt test', "
                        "'DE000VH2LU21', 'VH2LU2', 'ACTIVE', 1, :now, :now)"
                    ),
                    params,
                )

                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    preview = await configure_warrant(
                        session, client, workspace_id=workspace, warrant_id=warrant
                    )
                    assert preview["status"] == "DRY_RUN"
                    assert (
                        await session.scalar(
                            text("SELECT count(*) FROM warrant_listings WHERE warrant_id=:id"),
                            {"id": warrant},
                        )
                        == 0
                    )
                    applied = await configure_warrant(
                        session, client, workspace_id=workspace, warrant_id=warrant, apply=True
                    )
                    repeated = await configure_warrant(
                        session, client, workspace_id=workspace, warrant_id=warrant, apply=True
                    )
                    assert applied["warrant_listing_id"] == repeated["warrant_listing_id"]
                    assert repeated["create_mapping"] is repeated["create_listing"] is False
                    row = (
                        await session.execute(
                            text(
                                "SELECT l.symbol, l.quotation_currency_code, l.version, v.mic, "
                                "m.provider_symbol, "
                                "m.provider_exchange_code, m.status FROM warrant_listings l "
                                "JOIN trading_venues v ON v.id=l.trading_venue_id "
                                "JOIN warrant_provider_mappings m ON m.warrant_listing_id=l.id "
                                "WHERE l.warrant_id=:id"
                            ),
                            {"id": warrant},
                        )
                    ).one()
                    assert tuple(row) == (None, "EUR", 1, "XFRA", "DE000VH2LU21", "XSC", "ACTIVE")
                    # Conflicts must be reviewed, not silently overwritten or revalidated.
                    await session.execute(
                        text("UPDATE warrant_provider_mappings SET status='INACTIVE' WHERE id=:id"),
                        {"id": applied["mapping_id"]},
                    )
                    await session.commit()
                    session.expire_all()
                    with pytest.raises(ValueError, match="conflicts"):
                        await configure_warrant(
                            session, client, workspace_id=workspace, warrant_id=warrant, apply=True
                        )
                    assert (
                        await session.scalar(
                            text("SELECT count(*) FROM warrant_listings WHERE warrant_id=:id"),
                            {"id": warrant},
                        )
                        == 1
                    )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
