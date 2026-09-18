"""Persist position quote-source decisions against the migrated PostgreSQL schema."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_frankfurt_setup_postgres import (
    current_database_url,  # noqa: F401
)

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import PositionQuoteSourceSelectionModel
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.position_quote_source import PositionQuoteSourceSelector
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.resolvers import ResolvedProduct


@pytest.mark.asyncio
async def test_selection_is_identity_verified_persistent_and_idempotent(
    current_database_url,  # noqa: F811
):
    engine = create_async_engine(current_database_url)
    now = datetime.now(UTC)
    ids = {
        key: uuid4()
        for key in (
            "workspace",
            "issuer",
            "underlying",
            "warrant",
            "listing",
            "mapping",
            "actor",
            "trade_without_source",
            "position_without_source",
        )
    }
    params = {**ids, "now": now, "issuer_name": f"Quote source test {ids['issuer']}"}
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                for sql in (
                    "INSERT INTO workspaces(id,name,created_at) "
                    "VALUES (:workspace,'Quote source test',:now)",
                    "INSERT INTO issuers(id,legal_name,display_name,is_active,version,"
                    "created_at,updated_at) VALUES "
                    "(:issuer,:issuer_name,:issuer_name,true,1,:now,:now)",
                    "INSERT INTO underlyings(id,workspace_id,type,name,lifecycle_status,"
                    "quality_status,version,created_at,updated_at,data_origin) VALUES "
                    "(:underlying,:workspace,'STOCK','Quote source test','ACTIVE',"
                    "'VERIFIED',1,:now,:now,'MANUAL')",
                    "INSERT INTO warrants(id,workspace_id,issuer_id,underlying_id,product_family,"
                    "display_name,isin,lifecycle_status,version,created_at,updated_at) VALUES "
                    "(:warrant,:workspace,:issuer,:underlying,'WARRANT','Quote source test',"
                    "'DE000QS00001','ACTIVE',1,:now,:now)",
                ):
                    await connection.execute(text(sql), params)

                venue = await connection.scalar(
                    text("SELECT id FROM trading_venues WHERE mic='XSTU'")
                )
                if venue is None:
                    venue = uuid4()
                    await connection.execute(
                        text(
                            "INSERT INTO trading_venues(id,mic,name,country_code,timezone,"
                            "is_active,reference_version,version,created_at,updated_at) VALUES "
                            "(:id,'XSTU','Quote source test','DE','Europe/Berlin',true,"
                            "'test',1,:now,:now)"
                        ),
                        {"id": venue, "now": now},
                    )
                params["venue"] = venue

                for sql in (
                    "INSERT INTO warrant_listings(id,workspace_id,warrant_id,trading_venue_id,"
                    "symbol,quotation_currency_code,lifecycle_status,version,"
                    "created_at,updated_at) "
                    "VALUES (:listing,:workspace,:warrant,:venue,NULL,'EUR','ACTIVE',1,:now,:now)",
                    "INSERT INTO warrant_provider_mappings(id,workspace_id,warrant_listing_id,"
                    "provider,provider_symbol,provider_exchange_code,status,validated_at,version,"
                    "created_at,updated_at) VALUES "
                    "(:mapping,:workspace,:listing,'GETTEX_DELAYED','DE000QS00001','MUND',"
                    "'ACTIVE',:now,1,:now,:now)",
                    "INSERT INTO trades(id,workspace_id,product_id,origin,created_at,created_by) "
                    "VALUES (:trade_without_source,:workspace,:warrant,'EXTERNAL',:now,:actor)",
                    "INSERT INTO positions(id,trade_id,product_id,open_quantity,cost_basis,"
                    "average_entry_price,opened_at,last_execution_at,realized_gross_pnl) VALUES "
                    "(:position_without_source,:trade_without_source,:warrant,10,10,1,:now,:now,0)",
                ):
                    await connection.execute(text(sql), params)

                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    repository = PositionQuoteSourceSelectionRepository(session)
                    selector = PositionQuoteSourceSelector(
                        repository, {MarketDataProvider.GETTEX_DELAYED}
                    )
                    products = SimpleNamespace(
                        resolve=AsyncMock(
                            return_value=ResolvedProduct(
                                workspace_id=ids["workspace"],
                                product_id=ids["warrant"],
                            )
                        )
                    )
                    service = TradePositionService(
                        uow=SqlAlchemyTradePositionUnitOfWork(session),
                        workspace_selections=SimpleNamespace(resolve=AsyncMock()),
                        products=products,
                        quote_source_selector=selector,
                    )
                    _trade, _execution, position = await service.record_external_purchase(
                        workspace_id=ids["workspace"],
                        product_id=ids["warrant"],
                        quantity=10,
                        price_per_unit=Decimal("1.00"),
                        executed_at=now,
                        actor=ids["actor"],
                    )
                    selected = await repository.active_for_position(ids["workspace"], position.id)
                    assert selected is not None
                    assert selected.selection_status == "SELECTED"
                    assert selected.warrant_listing_id == ids["listing"]
                    assert selected.warrant_provider_mapping_id == ids["mapping"]
                    assert selected.provider == "GETTEX_DELAYED"
                    assert selected.mapping_version == 1
                    assert selected.identity_key and len(selected.identity_key) == 64

                    repeated = await selector.select_once(
                        workspace_id=ids["workspace"],
                        position_id=position.id,
                        warrant_id=ids["warrant"],
                    )
                    assert repeated.id == selected.id
                    assert (
                        await session.scalar(
                            select(PositionQuoteSourceSelectionModel).where(
                                PositionQuoteSourceSelectionModel.workspace_id == ids["workspace"],
                                PositionQuoteSourceSelectionModel.position_id == position.id,
                            )
                        )
                    ).id == selected.id
                    assert (
                        await session.scalar(
                            text(
                                "SELECT count(*) FROM position_quote_source_selections "
                                "WHERE workspace_id=:workspace AND position_id=:position "
                                "AND superseded_at IS NULL"
                            ),
                            {"workspace": ids["workspace"], "position": position.id},
                        )
                        == 1
                    )

                    no_source_selector = PositionQuoteSourceSelector(repository, ())
                    missing = await no_source_selector.select_once(
                        workspace_id=ids["workspace"],
                        position_id=ids["position_without_source"],
                        warrant_id=ids["warrant"],
                        selected_at=now,
                    )
                    assert missing.selection_status == "NO_VERIFIED_QUOTE_SOURCE"
                    assert missing.provider is None
                    assert missing.warrant_listing_id is None
                    assert missing.warrant_provider_mapping_id is None
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
