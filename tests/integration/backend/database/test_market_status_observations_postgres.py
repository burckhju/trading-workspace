"""Real append-only status migration, concurrent capture and read-only restart.

Only a UUID disposable database under the guarded test parent is ever written.
All external HTTP is intercepted; prices/statuses are explicitly synthetic.
"""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import seed_scope
from tests.integration.backend.test_realized_gross_report_postgres import _client
from tests.integration.backend.test_trade_capture_safety import WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider, QualityStatus
from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)
from app.features.market_data.domain.status_observations import StatusRouteBinding
from app.features.market_data.persistence.models import (
    WarrantMarketStatusObservationModel,
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
    WarrantQuoteSampleModel,
)
from app.features.market_data.persistence.quote_identity import read_quote_identity
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.market_data.service.status_observations import MarketStatusReader
from app.features.market_data.service.types import WarrantQuoteRequest

status_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http
PROVIDER = MarketDataProvider.FRANKFURT_QUOTES


def test_migrated_status_journal_parallel_capture_restart_and_original_guards(status_database):
    _migrate(status_database, "20261117_0054")

    async def exercise():
        assert make_url(status_database).database.startswith("tw_currency_ref_test_")
        engine = create_async_engine(status_database, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with _client(status_database) as (client, database):
                scope = await seed_scope(client)
                listing = UUID(scope["listing"]["id"])
                warrant = UUID(scope["product"]["id"])
                now = datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=1)
                async with sessions() as session:
                    await session.execute(
                        insert(WarrantProviderMappingModel).values(
                            id=uuid4(),
                            workspace_id=UUID(WORKSPACE),
                            warrant_listing_id=listing,
                            provider=PROVIDER,
                            provider_symbol=scope["product"]["isin"],
                            provider_exchange_code="XFRA",
                            status=MappingStatus.ACTIVE,
                            validated_at=now,
                            version=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    await session.commit()
                quote = saved.quote_result(listing, now)
                envelope = quote.data.original_evidence
                original = OriginalMarketStatusEvidence(
                    version="original-market-status-evidence-v1",
                    source_contract=envelope.source_contract,
                    source_reference=envelope.source_reference,
                    generated_at=envelope.generated_at,
                    isin=envelope.isin,
                    venue_mic=envelope.venue_mic,
                    status="OPEN",
                    original_status_text="OPEN",
                    source_status_field="trading_status",
                    observed_at=envelope.bid.observed_at,
                    original_time_text=envelope.bid.observed_at.isoformat(),
                    source_time_field="status_observed_at",
                )
                quote = replace(quote, data=replace(quote.data, original_market_status=original))
                provider = Mock()
                provider.get_warrant_listing_quote = AsyncMock(return_value=quote)
                request = WarrantQuoteRequest(UUID(WORKSPACE), listing, uuid4(), now)

                def runtime(at):
                    return RetainedWarrantQuoteProvider(
                        database, provider, PROVIDER, capture_clock=lambda: at
                    )

                await asyncio.gather(
                    runtime(now).get_warrant_listing_quote(request),
                    runtime(now).get_warrant_listing_quote(
                        replace(request, correlation_id=uuid4())
                    ),
                )
                async with sessions() as session:
                    assert (
                        await session.scalar(
                            select(func.count()).select_from(WarrantMarketStatusObservationModel)
                        )
                        == 1
                    )
                    price = await session.get(
                        WarrantQuoteObservationModel, (UUID(WORKSPACE), listing, PROVIDER.value)
                    )
                    original_price_payload = price.payload
                    identity = await read_quote_identity(session, request, PROVIDER)
                    route = StatusRouteBinding(
                        UUID(WORKSPACE),
                        warrant,
                        listing,
                        PROVIDER.value,
                        identity.key,
                        identity.isin,
                        identity.mic,
                    )
                closed_at = now + timedelta(seconds=30)
                closed = replace(
                    original,
                    status="CLOSED",
                    original_status_text="CLOSED",
                    generated_at=closed_at,
                    observed_at=closed_at,
                    original_time_text=closed_at.isoformat(),
                )
                provider.get_warrant_listing_quote.return_value = replace(
                    quote,
                    retrieved_at=closed_at,
                    quality_status=QualityStatus.INCOMPLETE,
                    data=replace(
                        quote.data,
                        bid=None,
                        ask=None,
                        observed_at=None,
                        original_evidence=None,
                        original_market_status=closed,
                        trading_status="CLOSED",
                    ),
                )
                fallback = await runtime(closed_at).get_warrant_listing_quote(
                    replace(request, as_of=closed_at, correlation_id=uuid4())
                )
                assert fallback.data.retained and fallback.data.original_market_status == original
                later = closed_at + timedelta(seconds=1)
                provider.get_warrant_listing_quote.side_effect = TimeoutError("synthetic outage")
                await runtime(later).get_warrant_listing_quote(
                    replace(request, as_of=later, correlation_id=uuid4())
                )
                # A fresh database session models process restart and is an
                # actual repeatable-read/read-only PostgreSQL transaction.
                async with sessions() as session:
                    await session.execute(
                        text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    )
                    reader = MarketStatusReader(session)
                    current = await reader.read(route=route, event_at=later, known_at=later)
                    assert current.point_verdict == "NO_POINT_AT_EVENT"
                    assert current.latest_gap.reason == "TimeoutError"
                    assert current.latest_observations[0].original.status == "CLOSED"
                    point = await reader.read(route=route, event_at=closed_at, known_at=later)
                    assert point.observed_status == "CLOSED"
                    row_id = point.point_observations[0].id
                    price = await session.get(
                        WarrantQuoteObservationModel, (UUID(WORKSPACE), listing, PROVIDER.value)
                    )
                    assert price.payload == original_price_payload
                    assert (
                        await session.scalar(
                            select(func.count()).select_from(WarrantQuoteSampleModel)
                        )
                        == 1
                    )
                    assert (
                        await session.scalar(
                            select(func.count()).select_from(WarrantMarketStatusObservationModel)
                        )
                        == 3
                    )
                    await session.rollback()
                for mutation in (
                    "UPDATE warrant_market_status_observations SET reason='changed' WHERE id=:id",
                    "DELETE FROM warrant_market_status_observations WHERE id=:id",
                    "TRUNCATE warrant_market_status_observations",
                ):
                    async with sessions() as session:
                        with pytest.raises(IntegrityError, match="append-only"):
                            await session.execute(text(mutation), {"id": row_id})
                        await session.rollback()
                async with sessions() as session:
                    original_row = await session.get(WarrantMarketStatusObservationModel, row_id)
                    values = {
                        column.name: getattr(original_row, column.name)
                        for column in WarrantMarketStatusObservationModel.__table__.columns
                    }
                    values.update(id=uuid4(), fingerprint="a" * 64, venue_mic="XSTU")
                    with pytest.raises(IntegrityError, match="route mismatch"):
                        await session.execute(
                            insert(WarrantMarketStatusObservationModel).values(**values)
                        )
                    await session.rollback()
        finally:
            await engine.dispose()

    asyncio.run(exercise())
    with pytest.raises(AssertionError, match="immutable market status observations"):
        _migrate(status_database, "20261116_0053", action="downgrade")
