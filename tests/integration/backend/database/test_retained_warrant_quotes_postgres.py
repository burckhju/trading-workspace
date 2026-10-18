"""Exercise durable quotes and identifier correction against the migrated PostgreSQL schema."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_frankfurt_setup_postgres import (
    current_database_url,  # noqa: F401
)

from app.features.market.persistence.models import AuditEventModel
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import WarrantQuoteObservationModel
from app.features.market_data.service.errors import MarketDataNotFoundError
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.service.application import WarrantService
from app.features.product.service.valuation_evidence import ValuationEvidenceService, ValuationFacts


@pytest.mark.asyncio
async def test_durable_round_trip_and_audited_correction_invalidates_old_quote(
    current_database_url,  # noqa: F811
):
    engine = create_async_engine(current_database_url)
    now = datetime.now(UTC)
    ids = {
        key: uuid4()
        for key in ("workspace", "issuer", "underlying", "warrant", "listing", "mapping")
    }
    params = {**ids, "now": now, "name": str(ids["issuer"])}
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                for sql in (
                    "INSERT INTO workspaces(id,name,created_at) VALUES (:workspace,"
                    "'Retention test',:now)",
                    "INSERT INTO issuers(id,legal_name,display_name,is_active,version,"
                    "created_at,updated_at) "
                    "VALUES (:issuer,:name,:name,true,1,:now,:now)",
                    "INSERT INTO underlyings(id,workspace_id,type,name,lifecycle_status,"
                    "quality_status,"
                    "version,created_at,updated_at,data_origin) VALUES (:underlying,"
                    ":workspace,'STOCK',"
                    "'Retention test','ACTIVE','VERIFIED',1,:now,:now,'MANUAL')",
                    "INSERT INTO warrants(id,workspace_id,issuer_id,underlying_id,product_family,"
                    "display_name,isin,lifecycle_status,version,created_at,updated_at) VALUES "
                    "(:warrant,:workspace,:issuer,:underlying,'WARRANT','Retention test',"
                    "'DE000VH2LU21','ACTIVE',1,:now,:now)",
                ):
                    await connection.execute(text(sql), params)
                venue = await connection.scalar(
                    text("SELECT id FROM trading_venues WHERE mic='XSTU'")
                )
                if venue is None:
                    venue = uuid4()
                    await connection.execute(
                        text(
                            "INSERT INTO trading_venues(id,mic,name,country_code,"
                            "timezone,is_active,"
                            "reference_version,version,created_at,updated_at) VALUES "
                            "(:id,'XSTU','Retention test','DE','Europe/Berlin',"
                            "true,'test',1,:now,:now)"
                        ),
                        {"id": venue, "now": now},
                    )
                params["venue"] = venue
                await connection.execute(
                    text(
                        "INSERT INTO warrant_listings(id,workspace_id,warrant_id,"
                        "trading_venue_id,symbol,"
                        "quotation_currency_code,lifecycle_status,version,created_at,"
                        "updated_at) VALUES "
                        "(:listing,:workspace,:warrant,:venue,NULL,'EUR','ACTIVE',1,:now,:now)"
                    ),
                    params,
                )
                await connection.execute(
                    text(
                        "INSERT INTO warrant_provider_mappings(id,workspace_id,"
                        "warrant_listing_id,provider,"
                        "provider_symbol,provider_exchange_code,status,validated_at,"
                        "version,created_at,"
                        "updated_at) VALUES (:mapping,:workspace,:listing,"
                        "'VONTOBEL_MARKETS','DE000VH2LU21',"
                        "'ISSUER','ACTIVE',:now,1,:now,:now)"
                    ),
                    params,
                )

                @asynccontextmanager
                async def session_context():
                    async with AsyncSession(
                        bind=connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    ) as session:
                        yield session

                database = SimpleNamespace(session_context=session_context)
                request = WarrantQuoteRequest(ids["workspace"], ids["listing"], uuid4(), now)
                original = MarketDataResult(
                    data=WarrantQuoteSnapshot(
                        ids["listing"],
                        Decimal("0.24"),
                        Decimal("0.25"),
                        "EUR",
                        "DE000VH2LU21",
                        "ISSUER",
                        now,
                        isin="DE000VH2LU21",
                    ),
                    provider=MarketDataProvider.VONTOBEL_MARKETS,
                    capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                    correlation_id=uuid4(),
                    retrieved_at=now,
                    cache_status=CacheStatus.MISS,
                    quality_status=QualityStatus.VALID,
                    warnings=(),
                    retry_count=0,
                    provider_call_cost=1,
                )
                provider = AsyncMock()
                provider.get_warrant_listing_quote.return_value = original
                first = RetainedWarrantQuoteProvider(
                    database, provider, original.provider, capture_clock=lambda: now
                )
                assert await first.get_warrant_listing_quote(request) == original
                provider.get_warrant_listing_quote.side_effect = TimeoutError()
                restarted = RetainedWarrantQuoteProvider(
                    database, provider, original.provider, capture_clock=lambda: now
                )
                held = await restarted.get_warrant_listing_quote(
                    replace(request, correlation_id=uuid4())
                )
                assert held.data.retained and held.data.bid == Decimal("0.24")
                assert held.retrieved_at == now and held.data.observed_at == now
                # Qualify the new immutable journal against actual migrated PostgreSQL.
                journal = (
                    await connection.execute(
                        text(
                            "SELECT id, captured_at, payload FROM warrant_quote_samples "
                            "WHERE warrant_id=:warrant"
                        ),
                        params,
                    )
                ).one()
                assert journal.payload["quote"]["bid"] == "0.24"
                assert journal.payload["quote"]["observed_at"] is not None
                terms_id = uuid4()
                await connection.execute(
                    text(
                        "INSERT INTO warrant_terms_versions (id,warrant_id,version_no,"
                        "effective_from,option_direction,strike,strike_currency_code,"
                        "maturity_date,ratio,created_at) VALUES (:id,:warrant,1,:now,"
                        "'CALL',100,'EUR','2099-12-31',0.1,:now)"
                    ),
                    {**params, "id": terms_id},
                )
                async with session_context() as session:
                    evidence = await ValuationEvidenceService(session).record(
                        workspace_id=ids["workspace"],
                        warrant_id=ids["warrant"],
                        terms_id=terms_id,
                        expected_version=1,
                        expected_revision=0,
                        actor_id=uuid4(),
                        now=now,
                        facts=ValuationFacts(
                            product_type="VANILLA_WARRANT",
                            exercise_style="EUROPEAN",
                            quanto=False,
                            ratio_convention="UNDERLYING_UNITS_PER_WARRANT",
                            expiry_at=None,
                            reviewed_at=now,
                            document_reference="Synthetic PostgreSQL fixture",
                            note="Test only",
                        ),
                    )
                    assert evidence.current.facts.quanto is False
                for table in ("warrant_quote_samples", "warrant_valuation_evidence"):
                    for operation in (
                        f"UPDATE {table} SET payload=payload",
                        f"DELETE FROM {table}",
                    ):
                        savepoint = await connection.begin_nested()
                        try:
                            with pytest.raises(IntegrityError, match="append-only"):
                                await connection.execute(
                                    text(operation + " WHERE warrant_id=:warrant"), params
                                )
                        finally:
                            await savepoint.rollback()
                    columns = (
                        "id,workspace_id,warrant_id,warrant_listing_id,provider,identity_key,isin,"
                        "slot_at,day_utc,captured_at,status,reason,quote_fingerprint,payload"
                        if table == "warrant_quote_samples"
                        else (
                            "id,workspace_id,warrant_id,terms_id,revision,identity_key,"
                            "recorded_at,actor_id,payload"
                        )
                    )
                    for wrong_owner in (False, True):
                        values = columns.replace("id,workspace_id,", ":new_id,:owner,", 1)
                        savepoint = await connection.begin_nested()
                        try:
                            with pytest.raises(
                                IntegrityError,
                                match="workspace mismatch" if wrong_owner else "duplicate key",
                            ):
                                await connection.execute(
                                    text(
                                        f"INSERT INTO {table} ({columns}) SELECT {values} "
                                        f"FROM {table} WHERE warrant_id=:warrant"
                                    ),
                                    {
                                        **params,
                                        "new_id": uuid4(),
                                        "owner": uuid4() if wrong_owner else ids["workspace"],
                                    },
                                )
                        finally:
                            await savepoint.rollback()
                async with session_context() as session:
                    await WarrantService(session).correct_identifiers(
                        ids["workspace"],
                        ids["warrant"],
                        expected_version=1,
                        isin="DE000VH4VNA6",
                        wkn=None,
                        evidence="Synthetic correction fixture",
                    )
                    audit = await session.scalar(
                        select(AuditEventModel).where(
                            AuditEventModel.aggregate_id == ids["warrant"]
                        )
                    )
                    assert audit.field_changes["isin"]["old"] == "DE000VH2LU21"
                    assert (
                        await session.scalar(
                            select(WarrantQuoteObservationModel).where(
                                WarrantQuoteObservationModel.workspace_id == ids["workspace"]
                            )
                        )
                        is not None
                    )
                with pytest.raises(MarketDataNotFoundError):
                    await restarted.get_warrant_listing_quote(request)
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
