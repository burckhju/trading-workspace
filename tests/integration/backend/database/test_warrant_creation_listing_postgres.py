"""Atomic first-listing creation against native PostgreSQL sessions and constraints.

Only a randomly named test schema is used; existing application tables are untouched.
The browser regression separately exercises the migrated REST API and reload path.
"""

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event, func, insert, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.features.market.persistence.models import (
    CurrencyModel,
    IssuerModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)
from app.features.product.domain.models import OptionDirection
from app.features.product.persistence.models import (
    WarrantListingModel,
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product.service.application import InitialWarrantListing, WarrantService
from app.features.product.service.errors import WarrantServiceError


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_child", [False, True])
async def test_first_listing_commits_together_or_rolls_back_after_parent_insert(fail_child):
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is required")
    schema = "test_warrant_creation_" + uuid4().hex
    engine = create_async_engine(url, execution_options={"schema_translate_map": {None: schema}})
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    models = (
        WorkspaceModel,
        CurrencyModel,
        TradingVenueModel,
        IssuerModel,
        UnderlyingModel,
        ListingModel,
        WarrantModel,
        WarrantTermsVersionModel,
        WarrantListingModel,
    )
    now = datetime.now(UTC)
    workspace, underlying, issuer, venue = (uuid4() for _ in range(4))
    parent_seen_before_child_failure = False

    def fail_on_listing_insert(_mapper, connection, target):
        nonlocal parent_seen_before_child_failure
        parent_seen_before_child_failure = (
            connection.scalar(select(WarrantModel.id).where(WarrantModel.id == target.warrant_id))
            == target.warrant_id
        )
        # Let the actual PostgreSQL CHECK fail after the parent has been INSERTed.
        target.symbol = ""

    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.run_sync(
                lambda sync: Base.metadata.create_all(
                    sync, tables=[model.__table__ for model in models]
                )
            )
            await connection.execute(
                insert(WorkspaceModel), dict(id=workspace, name="synthetic", created_at=now)
            )
            await connection.execute(
                insert(CurrencyModel),
                [
                    dict(
                        code=code,
                        name=code,
                        minor_unit=2,
                        is_active=True,
                        reference_version="test",
                        created_at=now,
                        updated_at=now,
                    )
                    for code in ("EUR", "USD")
                ],
            )
            await connection.execute(
                insert(TradingVenueModel),
                dict(
                    id=venue,
                    mic="TEST",
                    name="synthetic",
                    country_code="DE",
                    timezone="Europe/Berlin",
                    is_active=True,
                    reference_version="test",
                    created_at=now,
                    updated_at=now,
                ),
            )
            await connection.execute(
                insert(IssuerModel),
                dict(
                    id=issuer,
                    legal_name="synthetic",
                    display_name="synthetic",
                    created_at=now,
                    updated_at=now,
                ),
            )
            await connection.execute(
                insert(UnderlyingModel),
                dict(
                    id=underlying,
                    workspace_id=workspace,
                    type="STOCK",
                    name="synthetic",
                    lifecycle_status="ACTIVE",
                    quality_status="COMPLETE",
                    version=1,
                    created_at=now,
                    updated_at=now,
                    data_origin="MANUAL",
                ),
            )
        if fail_child:
            event.listen(WarrantListingModel, "before_insert", fail_on_listing_insert)
        async with sessions() as session:
            args = dict(
                issuer_id=issuer,
                underlying_id=underlying,
                display_name="synthetic combined creation",
                isin=None,
                wkn=None,
                option_direction=OptionDirection.CALL,
                strike=Decimal("100"),
                strike_currency_code="USD",
                maturity_date=date(2099, 12, 31),
                ratio=Decimal("0.1"),
                initial_listing=InitialWarrantListing(venue, "EUR"),
            )
            if fail_child:
                with pytest.raises(WarrantServiceError):
                    await WarrantService(session).create(workspace, **args)
                assert parent_seen_before_child_failure
            else:
                product = await WarrantService(session).create(workspace, **args)
                product_id = product.id
        # A fresh session/transaction sees either the complete product or no partial data.
        async with sessions() as reader:
            for model in (WarrantModel, WarrantTermsVersionModel, WarrantListingModel):
                assert await reader.scalar(select(func.count()).select_from(model)) == int(
                    not fail_child
                )
            assert await reader.scalar(select(func.count()).select_from(UnderlyingModel)) == 1
            if not fail_child:
                listing = await reader.scalar(select(WarrantListingModel))
                terms = await reader.scalar(select(WarrantTermsVersionModel))
                assert listing.warrant_id == terms.warrant_id == product_id
                assert listing.workspace_id == workspace
                assert listing.trading_venue_id == venue
                assert listing.quotation_currency_code == "EUR"
                assert listing.symbol is None
                assert terms.strike_currency_code == "USD"
    finally:
        if event.contains(WarrantListingModel, "before_insert", fail_on_listing_insert):
            event.remove(WarrantListingModel, "before_insert", fail_on_listing_insert)
        try:
            async with engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        finally:
            await engine.dispose()
