"""Real SQLAlchemy flush/FK/rollback checks with SQLite, not a PostgreSQL substitute.

The adapter only makes the synchronous in-memory session awaitable. SQL statements,
foreign keys, checks and commit/rollback are executed by the real ORM and database.
The regular E2E flow additionally covers PostgreSQL API persistence and reload.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

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
async def test_real_creation_flushes_parent_and_rolls_back_every_record_on_child_failure(
    fail_child,
):
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    models = [
        WorkspaceModel,
        CurrencyModel,
        TradingVenueModel,
        IssuerModel,
        UnderlyingModel,
        ListingModel,
        WarrantModel,
        WarrantListingModel,
        WarrantTermsVersionModel,
    ]
    Base.metadata.create_all(engine, tables=[model.__table__ for model in models])
    now = datetime.now(UTC)
    workspace, underlying, issuer, venue = (uuid4() for _ in range(4))
    with engine.begin() as connection:
        connection.execute(insert(WorkspaceModel), dict(id=workspace, name="test", created_at=now))
        connection.execute(
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
        connection.execute(
            insert(TradingVenueModel),
            dict(
                id=venue,
                mic="TEST",
                name="test",
                country_code="DE",
                timezone="Europe/Berlin",
                is_active=True,
                reference_version="test",
                created_at=now,
                updated_at=now,
            ),
        )
        connection.execute(
            insert(IssuerModel),
            dict(
                id=issuer,
                legal_name="test",
                display_name="test",
                created_at=now,
                updated_at=now,
            ),
        )
        connection.execute(
            insert(UnderlyingModel),
            dict(
                id=underlying,
                workspace_id=workspace,
                type="STOCK",
                name="test",
                lifecycle_status="ACTIVE",
                quality_status="COMPLETE",
                version=1,
                created_at=now,
                updated_at=now,
                data_origin="MANUAL",
            ),
        )

    child_attempted = False

    def fail_on_listing_insert(_mapper, _connection, target):
        nonlocal child_attempted
        child_attempted = True
        target.symbol = ""  # Force the real child-table CHECK to fail after the parent INSERT.

    if fail_child:
        event.listen(WarrantListingModel, "before_insert", fail_on_listing_insert)
    try:
        with Session(engine, expire_on_commit=False, autoflush=False) as sync:
            session = MagicMock(spec=AsyncSession)
            for name in ("get", "scalar", "scalars", "flush", "commit", "rollback"):
                setattr(session, name, AsyncMock(side_effect=getattr(sync, name)))
            session.add_all.side_effect = sync.add_all
            session.add.side_effect = sync.add
            args = dict(
                issuer_id=issuer,
                underlying_id=underlying,
                display_name="test call",
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
                assert child_attempted
                session.rollback.assert_awaited_once()
            else:
                product = await WarrantService(session).create(workspace, **args)
                assert sync.scalar(select(WarrantListingModel.warrant_id)) == product.id
                assert sync.scalar(select(WarrantTermsVersionModel.warrant_id)) == product.id
            session.commit.assert_awaited_once()
            # Read in a separate session after the transaction has really completed.
            with Session(engine) as reader:
                for model in (WarrantModel, WarrantTermsVersionModel, WarrantListingModel):
                    assert reader.scalar(select(func.count()).select_from(model)) == int(
                        not fail_child
                    )
                assert reader.scalar(select(func.count()).select_from(UnderlyingModel)) == 1
    finally:
        if fail_child:
            event.remove(WarrantListingModel, "before_insert", fail_on_listing_insert)
        engine.dispose()
