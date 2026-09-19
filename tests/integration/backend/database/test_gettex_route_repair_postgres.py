"""Qualify venue-correct GETTEX route repair on migrated PostgreSQL."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_frankfurt_setup_postgres import (
    current_database_url,  # noqa: F401
)

from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.tools.repair_gettex_listing_routes import _repair_session


@pytest.mark.asyncio
async def test_gettex_route_repair_moves_mapping_but_not_historical_observation(
    current_database_url,  # noqa: F811
):
    engine = create_async_engine(current_database_url)
    now = datetime.now(UTC)
    ids = {
        key: uuid4()
        for key in ("workspace", "issuer", "underlying", "warrant", "source_listing", "mapping")
    }
    params = {**ids, "now": now, "issuer_name": f"GETTEX repair {ids['issuer']}"}

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                for sql in (
                    "INSERT INTO workspaces(id,name,created_at) "
                    "VALUES (:workspace,'GETTEX repair test',:now)",
                    "INSERT INTO issuers(id,legal_name,display_name,is_active,version,"
                    "created_at,updated_at) VALUES "
                    "(:issuer,:issuer_name,:issuer_name,true,1,:now,:now)",
                    "INSERT INTO underlyings(id,workspace_id,type,name,lifecycle_status,"
                    "quality_status,version,created_at,updated_at,data_origin) VALUES "
                    "(:underlying,:workspace,'STOCK','GETTEX repair','ACTIVE',"
                    "'VERIFIED',1,:now,:now,'MANUAL')",
                    "INSERT INTO warrants(id,workspace_id,issuer_id,underlying_id,product_family,"
                    "display_name,isin,lifecycle_status,version,created_at,updated_at) VALUES "
                    "(:warrant,:workspace,:issuer,:underlying,'WARRANT','GETTEX repair',"
                    "'DE000GR00001','ACTIVE',1,:now,:now)",
                ):
                    await connection.execute(text(sql), params)

                xfra = await connection.scalar(
                    text("SELECT id FROM trading_venues WHERE mic='XFRA'")
                )
                if xfra is None:
                    xfra = uuid4()
                    await connection.execute(
                        text(
                            "INSERT INTO trading_venues(id,mic,name,country_code,timezone,"
                            "is_active,reference_version,version,created_at,updated_at) VALUES "
                            "(:id,'XFRA','Frankfurt test','DE','Europe/Berlin',true,"
                            "'test',1,:now,:now)"
                        ),
                        {"id": xfra, "now": now},
                    )
                mund = await connection.scalar(
                    text("SELECT id FROM trading_venues WHERE mic='MUND'")
                )
                assert mund is not None
                params.update(xfra=xfra, mund=mund)

                for sql in (
                    "INSERT INTO warrant_listings(id,workspace_id,warrant_id,trading_venue_id,"
                    "symbol,quotation_currency_code,lifecycle_status,version,"
                    "created_at,updated_at) "
                    "VALUES (:source_listing,:workspace,:warrant,:xfra,NULL,'EUR','ACTIVE',"
                    "1,:now,:now)",
                    "INSERT INTO warrant_provider_mappings(id,workspace_id,warrant_listing_id,"
                    "provider,provider_symbol,provider_exchange_code,status,validated_at,"
                    "validation_message,version,created_at,updated_at) VALUES "
                    "(:mapping,:workspace,:source_listing,'GETTEX_DELAYED','DE000GR00001',"
                    "'MUND','ACTIVE',:now,'test evidence',1,:now,:now)",
                    "INSERT INTO warrant_quote_observations(workspace_id,warrant_listing_id,"
                    "provider,identity_key,payload) VALUES "
                    "(:workspace,:source_listing,'GETTEX_DELAYED',"
                    "'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',"
                    "CAST(:payload AS JSON))",
                ):
                    await connection.execute(
                        text(sql),
                        {**params, "payload": '{"historical": true}'},
                    )

                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    preview = await _repair_session(
                        session,
                        workspace_id=ids["workspace"],
                        apply=False,
                    )
                    assert preview["changed_count"] == 1
                    assert preview["plans"][0]["action"] == "CREATE_LISTING_AND_MOVE_MAPPING"
                    assert preview["plans"][0]["target_listing_id"] is None
                    assert (
                        await session.scalar(
                            text(
                                "SELECT count(*) FROM warrant_listings "
                                "WHERE workspace_id=:workspace AND warrant_id=:warrant "
                                "AND trading_venue_id=:mund"
                            ),
                            params,
                        )
                        == 0
                    )

                    applied = await _repair_session(
                        session,
                        workspace_id=ids["workspace"],
                        apply=True,
                    )
                    assert applied["changed_count"] == 1
                    target_id = applied["plans"][0]["target_listing_id"]
                    assert target_id is not None

                    mapping = await session.scalar(
                        select(WarrantProviderMappingModel).where(
                            WarrantProviderMappingModel.id == ids["mapping"]
                        )
                    )
                    target_listing = await session.scalar(
                        select(WarrantListingModel).where(
                            WarrantListingModel.id == target_id
                        )
                    )
                    warrant = await session.scalar(
                        select(WarrantModel).where(WarrantModel.id == ids["warrant"])
                    )
                    target_venue = await session.scalar(
                        select(TradingVenueModel).where(TradingVenueModel.id == mund)
                    )
                    assert mapping is not None
                    assert target_listing is not None
                    assert warrant is not None
                    assert target_venue is not None
                    assert mapping.warrant_listing_id == target_listing.id
                    assert mapping.version == 2
                    identity = verified_identity(
                        ids["workspace"],
                        target_listing,
                        warrant,
                        target_venue,
                        MarketDataProvider.GETTEX_DELAYED,
                        mapping,
                    )
                    assert identity is not None
                    assert identity.mic == identity.exchange == "MUND"

                    old_observation = await session.scalar(
                        select(WarrantQuoteObservationModel).where(
                            WarrantQuoteObservationModel.workspace_id == ids["workspace"],
                            WarrantQuoteObservationModel.warrant_listing_id
                            == ids["source_listing"],
                            WarrantQuoteObservationModel.provider == "GETTEX_DELAYED",
                        )
                    )
                    new_observation = await session.scalar(
                        select(WarrantQuoteObservationModel).where(
                            WarrantQuoteObservationModel.workspace_id == ids["workspace"],
                            WarrantQuoteObservationModel.warrant_listing_id == target_listing.id,
                            WarrantQuoteObservationModel.provider == "GETTEX_DELAYED",
                        )
                    )
                    assert old_observation is not None
                    assert old_observation.payload == {"historical": True}
                    assert new_observation is None
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
