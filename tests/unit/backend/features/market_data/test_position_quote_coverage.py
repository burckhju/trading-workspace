from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.features.market_data.api.quote_coverage import (
    get_position_quote_coverage_service,
)
from app.features.market_data.persistence.position_quote_coverage import (
    PositionQuoteCoverageRecord,
)
from app.features.market_data.service.position_quote_coverage import (
    PositionQuoteCoverageReport,
    PositionQuoteCoverageService,
    PositionQuoteCoverageSummary,
    PositionQuoteSourceHealth,
)
from app.features.market_data.service.quote_coverage import ProductCoverage, RouteCoverage
from app.main import create_application

NOW = datetime(2026, 9, 19, 8, 0, tzinfo=UTC)


def record(*, selection_status: str | None = "SELECTED", identity: str = "identity"):
    workspace = uuid4()
    listing = uuid4()
    mapping = uuid4()
    warrant = uuid4()
    return workspace, PositionQuoteCoverageRecord(
        position_id=uuid4(),
        trade_id=uuid4(),
        warrant_id=warrant,
        name="Synthetic warrant",
        isin="DE000AB00001",
        wkn="AB0000",
        selection_id=uuid4() if selection_status is not None else None,
        selection_status=selection_status,
        selection_reason=(
            "UNIQUE_VERIFIED_ROUTE"
            if selection_status == "SELECTED"
            else selection_status
        ),
        policy_version=(
            "POSITION_QUOTE_SOURCE_POLICY_V1"
            if selection_status is not None
            else None
        ),
        selected_at=NOW - timedelta(days=1) if selection_status is not None else None,
        provider="GETTEX_DELAYED" if selection_status == "SELECTED" else None,
        listing_id=listing if selection_status == "SELECTED" else None,
        mapping_id=mapping if selection_status == "SELECTED" else None,
        persisted_identity_key=identity if selection_status == "SELECTED" else None,
        persisted_mapping_version=1 if selection_status == "SELECTED" else None,
        current_identity_key=identity if selection_status == "SELECTED" else None,
        current_mapping_status="ACTIVE" if selection_status == "SELECTED" else None,
        current_mapping_version=1 if selection_status == "SELECTED" else None,
        provider_exchange_code="MUND" if selection_status == "SELECTED" else None,
        mic="XSTU" if selection_status == "SELECTED" else None,
        currency="EUR" if selection_status == "SELECTED" else None,
    )


def route(
    row: PositionQuoteCoverageRecord,
    *,
    observed_at: datetime,
    configured: bool = True,
    observation_status: str = "BID_WITHIN_AGE_BUDGET",
    refresh_error: str | None = None,
    trading_status: str | None = "OPEN",
) -> RouteCoverage:
    assert row.listing_id is not None and row.mapping_id is not None
    return RouteCoverage(
        provider="GETTEX_DELAYED",
        listing_id=row.listing_id,
        mic="XSTU",
        currency="EUR",
        mapping_id=row.mapping_id,
        mapping_status="ACTIVE",
        provider_identity=row.isin,
        provider_exchange_code="MUND",
        validated_at=NOW - timedelta(days=1),
        configured=configured,
        route_reason="ROUTE_IDENTITY_VERIFIED",
        observation_status=observation_status,
        bid=Decimal("1.01"),
        ask=Decimal("1.03"),
        observed_at=observed_at,
        retrieved_at=observed_at,
        age_seconds=int((NOW - observed_at).total_seconds()),
        max_quote_age_seconds=3600,
        trading_status=trading_status,
        refresh_error=refresh_error,
    )


def product(row: PositionQuoteCoverageRecord, selected_route: RouteCoverage) -> ProductCoverage:
    return ProductCoverage(
        warrant_id=row.warrant_id,
        name=row.name,
        isin=row.isin,
        wkn=row.wkn,
        issuer="Synthetic issuer",
        issuer_probe_eligible=False,
        coverage="BID_WITHIN_AGE_BUDGET",
        routes=(selected_route,),
        refresh_status="DISABLED",
        refresh_reason=None,
        checked_at=None,
        next_run_at=None,
        discovery_reasons=(),
    )


def service_for(
    workspace,
    row: PositionQuoteCoverageRecord,
    product_coverage: ProductCoverage | None,
):
    reader = SimpleNamespace(open_positions=AsyncMock(return_value=(row,)))
    report = SimpleNamespace(
        items=(() if product_coverage is None else (product_coverage,)),
        configured_sources=("GETTEX_DELAYED",),
        source_order=("FRANKFURT_QUOTES", "GETTEX_DELAYED"),
    )
    products = SimpleNamespace(report=AsyncMock(return_value=report))
    return PositionQuoteCoverageService(reader, products), reader, products


@pytest.mark.asyncio
async def test_selected_position_projects_fresh_stored_quote_without_provider_read():
    workspace, row = record()
    selected_route = route(row, observed_at=NOW - timedelta(minutes=1))
    service, reader, products = service_for(workspace, row, product(row, selected_route))

    result = await service.report(workspace, {"workspace_id": workspace}, as_of=NOW)

    item = result.items[0]
    assert item.source_health is PositionQuoteSourceHealth.FRESH_QUOTE
    assert item.source_verified is item.identity_valid is True
    assert item.monitoring_usable is True
    assert item.execution_usable is False
    assert item.quote_type == "BID"
    assert item.bid == Decimal("1.01")
    assert result.summary.open_positions == 1
    assert result.summary.bound_positions == 1
    assert result.summary.source_verified == 1
    assert result.summary.fresh_quote == 1
    reader.open_positions.assert_awaited_once_with(workspace)
    products.report.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("selected_route", "expected"),
    [
        (
            lambda row: route(
                row,
                observed_at=datetime(2026, 9, 18, 19, 59, tzinfo=UTC),
                observation_status="OLDER_BID",
                trading_status="CLOSED",
            ),
            PositionQuoteSourceHealth.LAST_AVAILABLE,
        ),
        (
            lambda row: route(
                row,
                observed_at=NOW - timedelta(hours=2),
                observation_status="OLDER_BID",
                refresh_error="WARRANT_NO_QUOTE_RETURNED",
            ),
            PositionQuoteSourceHealth.RETAINED_AFTER_REFRESH_ERROR,
        ),
        (
            lambda row: route(
                row,
                observed_at=NOW - timedelta(hours=2),
                observation_status="OLDER_BID",
                trading_status="OPEN",
            ),
            PositionQuoteSourceHealth.STALE,
        ),
    ],
)
async def test_selected_position_separates_last_retained_and_stale(
    selected_route, expected
):
    workspace, row = record()
    selected = selected_route(row)
    service, _, _ = service_for(workspace, row, product(row, selected))

    result = await service.report(workspace, {"workspace_id": workspace}, as_of=NOW)

    assert result.items[0].source_health is expected
    assert result.items[0].monitoring_usable is True


@pytest.mark.asyncio
async def test_changed_identity_is_mapping_conflict_even_if_product_route_looks_available():
    workspace, row = record()
    row = PositionQuoteCoverageRecord(
        **{
            **row.__dict__,
            "current_identity_key": "changed",
        }
    )
    selected_route = route(row, observed_at=NOW - timedelta(minutes=1))
    service, _, _ = service_for(workspace, row, product(row, selected_route))

    result = await service.report(workspace, {"workspace_id": workspace}, as_of=NOW)

    assert result.items[0].source_health is PositionQuoteSourceHealth.MAPPING_CONFLICT
    assert result.items[0].source_verified is False
    assert result.items[0].monitoring_usable is False
    assert result.summary.mapping_conflict == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("selection_status", "expected"),
    [
        (None, PositionQuoteSourceHealth.LEGACY_UNBOUND),
        (
            "NO_VERIFIED_QUOTE_SOURCE",
            PositionQuoteSourceHealth.NO_VERIFIED_QUOTE_SOURCE,
        ),
        ("AMBIGUOUS_SOURCE", PositionQuoteSourceHealth.AMBIGUOUS_SOURCE),
    ],
)
async def test_unbound_and_fail_closed_positions_never_gain_a_selected_route(
    selection_status, expected
):
    workspace, row = record(selection_status=selection_status)
    service, _, _ = service_for(workspace, row, None)

    result = await service.report(workspace, {"workspace_id": workspace}, as_of=NOW)

    assert result.items[0].source_health is expected
    assert result.items[0].selected_provider is None
    assert result.items[0].source_verified is False
    assert result.items[0].monitoring_usable is False
    assert result.summary.missing_source == 1


def test_position_coverage_api_is_get_only_and_uses_runtime_workspace():
    workspace = uuid4()
    report = PositionQuoteCoverageReport(
        assessed_at=NOW,
        configured_sources=("GETTEX_DELAYED",),
        source_order=("GETTEX_DELAYED",),
        summary=PositionQuoteCoverageSummary(
            open_positions=0,
            bound_positions=0,
            legacy_unbound=0,
            source_verified=0,
            fresh_quote=0,
            last_available=0,
            retained_after_refresh_error=0,
            stale=0,
            reference_only=0,
            missing_quote=0,
            missing_source=0,
            source_disabled=0,
            mapping_conflict=0,
            ambiguous_source=0,
            invalid_quote=0,
        ),
        items=(),
    )
    service = SimpleNamespace(report=AsyncMock(return_value=report))
    app = create_application(Settings(_env_file=None, environment="test"))
    app.state.market_data_refresh = SimpleNamespace(
        workspace_id=workspace,
        status=lambda: {"workspace_id": workspace, "enabled": False},
    )
    app.dependency_overrides[get_position_quote_coverage_service] = lambda: service
    client = TestClient(app)

    response = client.get("/api/v1/market-data/positions/quote-coverage")

    assert response.status_code == 200
    assert response.json()["summary"]["open_positions"] == 0
    service.report.assert_awaited_once()
    assert client.post("/api/v1/market-data/positions/quote-coverage").status_code == 405
