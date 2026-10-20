"""Real PostgreSQL -> read adapters -> HTTP chart contracts; synthetic rollback fixture."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_analysis_instrument_guard_postgres import (
    _test_database_url,
)

from app.core.config import Environment, Settings
from app.database.dependencies import get_database_session
from app.features.analysis.api import charts
from app.features.analysis.domain.enums import PriceField
from app.features.analysis.service.charts import ChartService
from app.features.market.domain.enums import (
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)
from app.features.market.domain.top_down import BenchmarkRole
from app.features.market.persistence.chart_context import SqlAlchemyChartContextReader
from app.features.market.persistence.models import (
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)
from app.features.market.persistence.top_down_models import (
    MarketReferenceModel,
    ReferenceSeriesDefinitionModel,
)
from app.features.market.service.sector_proposals import SECTOR_PROPOSALS
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider, PriceType
from app.features.market_data.domain.enums import QualityStatus as PriceQuality
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)
from app.features.market_data.persistence.time_series import SqlAlchemyTimeSeriesReader
from app.main import create_application

NOW = datetime(2026, 10, 4, tzinfo=UTC)
DAY = date(2026, 9, 1)


async def seed_series(session, workspace, *, reference=None, kind="ETF", isin=None):
    listing = None
    underlying = None
    symbol = f"CHART{uuid4().hex[:12]}"
    if reference is None:
        venue = await session.scalar(
            select(TradingVenueModel).where(TradingVenueModel.is_active.is_(True))
        )
        underlying = UnderlyingModel(
            id=uuid4(),
            workspace_id=workspace,
            type=UnderlyingType(kind),
            name=f"TEST ONLY {symbol}",
            isin=isin,
            wkn=None,
            lifecycle_status=LifecycleStatus.ACTIVE,
            quality_status=QualityStatus.COMPLETE,
            version=1,
            created_at=NOW,
            updated_at=NOW,
            data_origin=DataOrigin.MANUAL,
        )
        session.add(underlying)
        await session.flush()
        listing = ListingModel(
            id=uuid4(),
            workspace_id=workspace,
            underlying_id=underlying.id,
            trading_venue_id=venue.id,
            ticker=symbol,
            currency_code="USD",
            lifecycle_status=LifecycleStatus.ACTIVE,
            is_primary=True,
            version=1,
            created_at=NOW,
            updated_at=NOW,
            data_origin=DataOrigin.MANUAL,
        )
        session.add(listing)
        await session.flush()
    instrument = MarketDataInstrumentModel(
        id=uuid4(),
        workspace_id=workspace,
        kind="LISTING" if listing else "MARKET_REFERENCE",
        listing_id=listing.id if listing else None,
        market_reference_id=reference.id if reference else None,
        created_at=NOW,
    )
    session.add(instrument)
    await session.flush()
    mapping = ProviderInstrumentMappingModel(
        id=uuid4(),
        workspace_id=workspace,
        listing_id=listing.id if listing else None,
        market_data_instrument_id=instrument.id,
        provider=MarketDataProvider.EODHD,
        provider_symbol=symbol,
        provider_exchange_code="US" if listing else "INDX",
        status=MappingStatus.ACTIVE,
        validated_at=NOW,
        created_at=NOW,
        updated_at=NOW,
        version=1,
    )
    session.add(mapping)
    await session.flush()
    for offset in (0, 1, 3, 40):  # missing weekday; last point is future to requested range
        price = Decimal(100 + offset)
        session.add(
            DailyPriceModel(
                id=uuid4(),
                workspace_id=workspace,
                listing_id=listing.id if listing else None,
                market_data_instrument_id=instrument.id,
                trading_date=DAY + timedelta(days=offset),
                open=price,
                high=price,
                low=price,
                close=price,
                adjusted_close=price,
                volume=Decimal(100),
                currency="USD",
                provider=MarketDataProvider.EODHD,
                provider_symbol=symbol,
                retrieved_at=NOW,
                source_updated_at=None,
                quality_status=PriceQuality.VALID,
                warnings="fixture provenance",
                price_type=PriceType.EOD,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    await session.flush()
    return underlying, listing, instrument, mapping


@pytest.mark.asyncio
async def test_market_sector_stock_http_read_path_and_immutable_evidence(monkeypatch):
    engine = create_async_engine(_test_database_url())
    workspace = uuid4()
    other_workspace = uuid4()
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            session.add_all(
                [
                    WorkspaceModel(id=workspace, name="TEST Charts", created_at=NOW),
                    WorkspaceModel(id=other_workspace, name="TEST isolation", created_at=NOW),
                ]
            )
            await session.flush()
            admin = TopDownReferenceAdministrationService(session)
            refs = (await admin.bootstrap_v1(workspace)).market_references
            market = next(item for item in refs if item.code == "SP500")
            _, _, instrument, mapping = await seed_series(session, workspace, reference=market)
            definition = await admin.confirm_series_basis(
                workspace_id=workspace,
                market_reference_id=market.id,
                mapping_id=mapping.id,
                mapping_version=1,
                return_basis="PRICE_INDEX",
                source_url="https://example.test/fixture-index",
                actor="Chart integration test",
            )
            proxies = []
            sectors = []
            for index, hint in enumerate(SECTOR_PROPOSALS):
                sector = await admin.create_sector(
                    workspace_id=workspace,
                    code=hint.code,
                    name=hint.sector,
                    classification_system="GICS",
                    classification_version="fixture-only",
                )
                sectors.append(sector)
                if index >= 2:
                    continue
                reference = await admin.create_sector_reference(
                    workspace_id=workspace,
                    code=hint.ticker,
                    name=hint.benchmark,
                    region="US",
                    reference_version="fixture-only",
                )
                _, listing, _, _ = await seed_series(session, workspace, isin=hint.isin)
                proxies.append(listing)
                await admin.assign_sector_reference(
                    workspace_id=workspace,
                    sector_id=sector.id,
                    market_reference_id=reference.id,
                    valid_from=DAY,
                    valid_to=None,
                    source="TEST",
                    quality_status="GOOD",
                )
                await admin.assign_reference_listing(
                    workspace_id=workspace,
                    market_reference_id=reference.id,
                    listing_id=listing.id,
                    valid_from=DAY,
                    valid_to=None,
                    source="TEST",
                    source_reference=hint.source_url,
                    quality_status="GOOD",
                )
            stock, stock_listing, _, _ = await seed_series(session, workspace, kind="STOCK")
            await admin.assign_underlying_benchmark(
                workspace_id=workspace,
                underlying_id=stock.id,
                market_reference_id=market.id,
                role=BenchmarkRole.BROAD_MARKET,
                valid_from=DAY,
                valid_to=None,
                source="TEST",
                source_reference="fixture",
                quality_status="GOOD",
            )
            await admin.assign_underlying_sector(
                workspace_id=workspace,
                underlying_id=stock.id,
                sector_id=sectors[0].id,
                valid_from=DAY,
                valid_to=None,
                source="TEST",
                source_reference="fixture",
                quality_status="GOOD",
            )
            monkeypatch.setattr(charts, "WORKSPACE_ID", workspace)
            app = create_application(
                Settings(_env_file=None, environment=Environment.TEST, log_level="CRITICAL")
            )
            app.dependency_overrides[get_database_session] = lambda: session
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as http:
                catalog = await http.get("/api/v1/market-charts/catalog?as_of=2026-10-01")
                assert catalog.status_code == 200, catalog.text
                matrix = catalog.json()["sectors"]
                assert len(matrix) == 11
                assert [item["context"]["status"] for item in matrix].count(
                    "MISSING_REFERENCE"
                ) == 9
                assert all(item["proxy_history"]["count"] == 3 for item in matrix[:2])
                assert len(catalog.json()["proxies"]) == 2
                context = (
                    await http.get(f"/api/v1/market-charts/underlyings/{stock.id}?as_of=2026-10-01")
                ).json()
                assert context["sector"]["listing_id"] == str(proxies[0].id)
                assert context["market"]["reference_id"] == str(market.id)
                targets = [
                    f"reference:{market.id}",
                    f"listing:{proxies[0].id}",
                    f"listing:{proxies[1].id}",
                    f"listing:{stock_listing.id}",
                ]
                response = await http.get(
                    "/api/v1/market-charts/series",
                    params=[("target", key) for key in targets] + [("end_date", "2026-10-01")],
                )
                assert response.status_code == 200, response.text
                data = response.json()
                assert data["comparison_status"] == "READY"
                assert data["series"][0]["identity"]["listing_id"] is None
                assert data["series"][1]["identity"]["instrument_type"] == "ETF"
                assert data["series"][-1]["points"][-1]["normalized"] == "103.00000000"
                assert all(item["observation_count"] == 3 for item in data["series"])
                assert data["series"][0]["points"][-1]["gap_before"] is True
                assert data["series"][0]["points"][0]["warnings"] == ["fixture provenance"]
            foreign_reader = SqlAlchemyChartContextReader(session)
            with pytest.raises(ValueError, match="not found"):
                await foreign_reader.resolve(other_workspace, f"listing:{stock_listing.id}")
            assert (
                await SqlAlchemyTimeSeriesReader(session).observations(
                    other_workspace, instrument.id, DAY, NOW.date()
                )
                == ()
            )
            context = await SqlAlchemyChartContextReader(session).underlying(
                workspace, stock.id, DAY - timedelta(days=1)
            )
            assert context.market is None and context.sector is None
            # Database guards protect evidence even outside the application service.
            for command in (
                "UPDATE reference_series_definitions SET source_url = :url WHERE id = :id",
                "DELETE FROM reference_series_definitions WHERE id = :id",
            ):
                with pytest.raises(IntegrityError):
                    async with session.begin_nested():
                        await session.execute(
                            text(command),
                            {"url": "https://example.test/replaced", "id": definition.id},
                        )
            with pytest.raises(IntegrityError):
                async with session.begin_nested():
                    session.add(
                        ReferenceSeriesDefinitionModel(
                            id=uuid4(),
                            workspace_id=other_workspace,
                            market_reference_id=market.id,
                            mapping_id=mapping.id,
                            mapping_version=1,
                            return_basis="PRICE_INDEX",
                            source_url="https://example.test/foreign",
                            confirmed_by="test",
                            confirmed_at=NOW,
                        )
                    )
                    await session.flush()
            mapping.version = 2
            await session.flush()
            changed = ChartService(
                SqlAlchemyChartContextReader(session), SqlAlchemyTimeSeriesReader(session)
            )
            result = await changed.series(
                workspace, (f"reference:{market.id}",), DAY, NOW.date(), PriceField.CLOSE
            )
            assert result.comparison_status == "RETURN_BASIS_UNKNOWN"
            assert (
                await session.scalar(
                    select(MarketReferenceModel.id).where(MarketReferenceModel.id == market.id)
                )
                == market.id
            )
        await transaction.rollback()
    await engine.dispose()
