"""Real SQL projection with constant query count; synthetic data only."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_retained_quotes import SqlDatabase

from app.features.market.persistence.models import CurrencyModel, IssuerModel, TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.quote_coverage import QuoteCoverageRepository
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.product_selection.persistence.models import ProductEvaluationModel  # noqa: F401
from app.features.trade_plan.persistence.models import TradePlanModel  # noqa: F401
from app.features.trade_position.persistence.models import PositionModel, TradeModel

NOW = datetime(2026, 9, 15, 10, tzinfo=UTC)


@pytest.fixture
def sample(tmp_path):
    database = SqlDatabase(f"sqlite:///{tmp_path}/coverage.db")
    for model in (
        CurrencyModel,
        IssuerModel,
        TradingVenueModel,
        WarrantModel,
        WarrantListingModel,
        WarrantProviderMappingModel,
        WarrantQuoteObservationModel,
        TradeModel,
        PositionModel,
    ):
        model.__table__.create(database.engine)
    workspace, other = uuid4(), uuid4()
    issuer_id, venue_id = uuid4(), uuid4()
    common = dict(created_at=NOW, updated_at=NOW, version=1)
    products = {}
    with Session(database.engine) as session:
        session.add(
            CurrencyModel(
                code="EUR",
                name="Euro",
                minor_unit=2,
                is_active=True,
                reference_version="test",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            IssuerModel(
                id=issuer_id,
                legal_name="VONT FINL.",
                display_name="Synthetic issuer",
                is_active=True,
                **common,
            )
        )
        session.add(
            TradingVenueModel(
                id=venue_id,
                mic="XSTU",
                name="Synthetic venue",
                country_code="DE",
                timezone="Europe/Berlin",
                is_active=True,
                reference_version="test",
                **common,
            )
        )
        for index, (name, scope, quantity, cancelled) in enumerate(
            [
                ("held", workspace, 10, False),
                ("closed", workspace, 0, False),
                ("cancelled", workspace, 10, True),
                ("foreign", other, 10, False),
                ("unlisted", workspace, 10, False),
            ]
        ):
            pid, listing_id, trade_id = uuid4(), uuid4(), uuid4()
            products[name] = (pid, listing_id)
            session.add(
                WarrantModel(
                    id=pid,
                    workspace_id=scope,
                    issuer_id=issuer_id,
                    underlying_id=uuid4(),
                    product_family="WARRANT",
                    display_name=name,
                    isin=f"DE000AB00{index:03d}",
                    lifecycle_status="ACTIVE",
                    **common,
                )
            )
            session.add(
                TradeModel(
                    id=trade_id,
                    workspace_id=scope,
                    product_id=pid,
                    origin="EXTERNAL",
                    created_at=NOW,
                    created_by=uuid4(),
                    cancelled_at=NOW if cancelled else None,
                    cancelled_by=uuid4() if cancelled else None,
                    cancellation_reason="Synthetic incorrect capture" if cancelled else None,
                )
            )
            session.add(
                PositionModel(
                    id=uuid4(),
                    trade_id=trade_id,
                    product_id=pid,
                    open_quantity=quantity,
                    cost_basis=Decimal(quantity),
                    average_entry_price=Decimal(1),
                    opened_at=NOW,
                    last_execution_at=NOW,
                    realized_gross_pnl=Decimal(0),
                    closed_at=NOW if quantity == 0 else None,
                )
            )
            if name != "unlisted":
                session.add(
                    WarrantListingModel(
                        id=listing_id,
                        workspace_id=scope,
                        warrant_id=pid,
                        trading_venue_id=venue_id,
                        quotation_currency_code="EUR",
                        lifecycle_status="ACTIVE",
                        symbol=None,
                        **common,
                    )
                )
        # A disabled mapping must stay visible, not be interpreted as missing.
        session.add(
            WarrantProviderMappingModel(
                id=uuid4(),
                workspace_id=workspace,
                warrant_listing_id=products["held"][1],
                provider=MarketDataProvider.VONTOBEL_MARKETS,
                provider_symbol="DE000AB00000",
                provider_exchange_code="ISSUER",
                status=MappingStatus.DISABLED,
                validated_at=NOW,
                **common,
            )
        )
        session.commit()
    yield database, workspace, products, issuer_id
    database.engine.dispose()


@pytest.mark.asyncio
async def test_complete_held_universe_read_only_and_four_queries(sample):
    database, workspace, products, _ = sample
    statements = []
    event.listen(
        database.engine,
        "before_cursor_execute",
        lambda conn, cursor, sql, params, ctx, many: statements.append(sql),
    )
    result = await QuoteCoverageRepository(database).held_products(workspace)
    assert len(statements) == 4
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in statements)
    assert {p.warrant_id for p in result} == {products["held"][0], products["unlisted"][0]}
    held = next(p for p in result if p.name == "held")
    routes = {route.provider: route for route in held.routes}
    assert routes["VONTOBEL_MARKETS"].route_reason == "MAPPING_DISABLED"
    assert routes["VONTOBEL_MARKETS"].identity_key is None
    assert routes["BOERSE_STUTTGART_DELAYED"].route_reason == "ROUTE_IDENTITY_VERIFIED"
    assert routes["BOERSE_STUTTGART_DELAYED"].mapping_id is None
    assert held.issuer_probe_eligible is True
    assert next(p for p in result if p.name == "unlisted").routes == ()


@pytest.mark.asyncio
async def test_inactive_held_issuer_is_not_silently_dropped(sample):
    database, workspace, _, issuer = sample
    with Session(database.engine) as session:
        session.get(IssuerModel, issuer).is_active = False
        session.commit()
    result = await QuoteCoverageRepository(database).held_products(workspace)
    assert len(result) == 2
    assert all(not p.active for p in result)


@pytest.mark.asyncio
async def test_empty_workspace_short_circuits_and_cannot_read_other_holdings(sample):
    database, _, _, _ = sample
    statements = []
    event.listen(
        database.engine,
        "before_cursor_execute",
        lambda conn, cursor, sql, params, ctx, many: statements.append(sql),
    )
    assert await QuoteCoverageRepository(database).held_products(uuid4()) == ()
    assert len(statements) == 1
