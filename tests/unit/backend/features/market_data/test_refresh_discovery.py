"""Discovery preserves user decisions and routes only catalog proof into administration."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service import refresh_discovery as module
from app.features.market_data.service.refresh_discovery import discover_underlying
from app.features.market_data.service.types import ProviderInstrumentSearchItem
from app.providers.eodhd.stock_catalog import StockCatalogDiscovery, StockCatalogIdentity


@asynccontextmanager
async def context(session):
    yield session


def setup(monkeypatch):
    workspace, listing_id, venue_id = uuid4(), uuid4(), uuid4()
    listing = SimpleNamespace(
        id=listing_id, underlying_id=uuid4(), currency_code="EUR", trading_venue_id=venue_id
    )
    underlying = SimpleNamespace(
        workspace_id=workspace, isin="FR0000121329", lifecycle_status="ACTIVE"
    )
    venue = SimpleNamespace(id=venue_id, mic="XPAR", is_active=True)
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[listing, None, None]),
        get=AsyncMock(side_effect=[underlying, venue]),
    )
    now = datetime.now(UTC)
    proof = StockCatalogIdentity(
        ProviderInstrumentSearchItem(
            MarketDataProvider.EODHD, "HO", "PA", currency="EUR", isin=underlying.isin
        ),
        "XPAR",
        "/exchange-symbol-list/PA",
        now,
        now,
    )
    adapter = SimpleNamespace(
        stock_catalog=SimpleNamespace(
            discover=AsyncMock(
                return_value=StockCatalogDiscovery(
                    "EODHD_CATALOG_IDENTITY_VERIFIED", proof, "PA", 1
                )
            )
        )
    )
    container = SimpleNamespace(
        eodhd=SimpleNamespace(adapter=adapter),
        database=SimpleNamespace(session_context=lambda: context(session)),
    )
    admin = SimpleNamespace(
        create_or_update=AsyncMock(return_value=SimpleNamespace(id=uuid4())),
        validate=AsyncMock(
            return_value=SimpleNamespace(id=uuid4(), status=SimpleNamespace(value="ACTIVE"))
        ),
    )
    monkeypatch.setattr(module, "SqlAlchemyMarketDataUnitOfWork", Mock())
    monkeypatch.setattr(module, "MarketDataInstrumentIdentityService", Mock())
    monkeypatch.setattr(module, "ProviderMappingAdministrationService", Mock(return_value=admin))
    return container, session, adapter, admin, underlying, venue, workspace, listing_id


@pytest.mark.asyncio
async def test_first_mapping_uses_official_proof_and_existing_audited_administration(monkeypatch):
    container, _, adapter, admin, _, _, workspace, listing_id = setup(monkeypatch)
    result = await discover_underlying(container, workspace, listing_id)
    assert result["reason"] == "EODHD_MAPPING_ACTIVE"
    assert (
        result["listing_mic"] == "XPAR" and result["catalog_endpoint"] == "/exchange-symbol-list/PA"
    )
    adapter.stock_catalog.discover.assert_awaited_once_with(
        isin="FR0000121329", currency="EUR", mic="XPAR"
    )
    command = admin.create_or_update.await_args.args[0]
    assert (command.listing_id, command.provider_symbol, command.provider_exchange_code) == (
        listing_id,
        "HO",
        "PA",
    )
    admin.validate.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        "no_isin",
        "foreign",
        "inactive_stock",
        "inactive_venue",
        "no_venue",
        "existing_active",
        "existing_disabled",
        "inactive_listing",
        "disabled_provider",
        "currency",
    ],
)
async def test_unverified_identity_or_existing_mapping_never_changes_master_data(
    monkeypatch, failure
):
    container, session, adapter, admin, underlying, venue, workspace, listing_id = setup(
        monkeypatch
    )
    if failure == "no_isin":
        underlying.isin = None
    if failure == "foreign":
        underlying.workspace_id = uuid4()
    if failure == "inactive_stock":
        underlying.lifecycle_status = "INACTIVE"
    if failure == "inactive_venue":
        venue.is_active = False
    if failure == "no_venue":
        session.get.side_effect = [underlying, None]
    if failure.startswith("existing_"):
        session.scalar.side_effect = [
            SimpleNamespace(),
            SimpleNamespace(
                status="ACTIVE" if failure.endswith("active") else "DISABLED",
                validated_at=datetime.now(UTC),
            ),
        ]
    if failure == "inactive_listing":
        session.scalar.side_effect = [None]
    if failure == "disabled_provider":
        container.eodhd = None
    if failure == "currency":
        adapter.stock_catalog.discover.return_value = StockCatalogDiscovery(
            "EODHD_LISTING_CURRENCY_MISMATCH",
            provider_exchange_code="PA",
            matching_isin_count=1,
            candidate_currencies=("EUR",),
        )
    result = await discover_underlying(container, workspace, listing_id)
    if failure == "currency":
        assert result["reason"] == "EODHD_LISTING_CURRENCY_MISMATCH"
        assert result["candidate_currencies"] == "EUR"
        assert result["isin"] == underlying.isin
    elif failure == "existing_active":
        assert result["status"] == "AVAILABLE"
    else:
        assert result["status"] == "BLOCKED"
    admin.create_or_update.assert_not_awaited()
    admin.validate.assert_not_awaited()


@pytest.mark.asyncio
async def test_catalog_identity_owned_by_another_listing_is_not_reassigned(monkeypatch):
    container, session, _adapter, admin, _underlying, _venue, workspace, listing_id = setup(
        monkeypatch
    )
    owner = SimpleNamespace(id=uuid4(), listing_id=uuid4())
    values = list(session.scalar.side_effect)
    session.scalar.side_effect = [*values[:2], owner]
    result = await discover_underlying(container, workspace, listing_id)
    assert result["reason"] == "EODHD_PROVIDER_IDENTITY_ALREADY_MAPPED"
    assert result["owner_listing_id"] == str(owner.listing_id)
    admin.create_or_update.assert_not_awaited()
