"""Watchlist read/API contracts; database owner orchestration is qualified in PostgreSQL."""

from dataclasses import replace
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.unit.backend.features.market_data.test_mapping_administration import Uow

from app.features.market.api.chart_watchlist import get_chart_watchlist_service, router
from app.features.market.domain.enums import LifecycleStatus, UnderlyingType
from app.features.market.persistence.chart_watchlist import ChartWatchlistMemberModel
from app.features.market.persistence.models import (
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.market.persistence.top_down_models import (
    MarketReferenceModel,
    ReferenceSeriesDefinitionModel,
)
from app.features.market.service.chart_watchlist import ChartWatchlistService
from app.features.market.service.chart_watchlist_catalog import (
    ChartWatchlistDefinition,
    bundled_chart_watchlist_catalog,
)
from app.features.market.service.chart_watchlist_contracts import (
    ChartWatchlistError,
    ChartWatchlistHistory,
)
from app.features.market.service.chart_watchlist_setup import ChartWatchlistSetup
from app.features.market.service.chart_watchlist_state import ChartWatchlistStateReader
from app.features.market.service.types import Actor
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel
from app.features.market_data.service.administration import (
    MappingCommand,
    ProviderMappingAdministrationService,
)


def test_bundled_watchlist_separates_direct_index_from_thirty_sourced_etfs():
    catalog = bundled_chart_watchlist_catalog()
    index, *etfs = catalog.items
    assert catalog.catalog_version == "GLOBAL_MARKETS_ETF_V1_20261109"
    assert index.code == "SP500" and index.kind == "INDEX"
    assert (index.isin, index.mic, index.currency, index.ticker) == (
        None,
        None,
        None,
        None,
    )
    assert len(etfs) == len({item.isin for item in etfs}) == 30
    assert sum(item.mic == "ARCX" for item in etfs) == 24
    assert sum(item.mic == "XNMS" for item in etfs) == 6
    assert all(item.kind == "ETF" and item.currency == "USD" for item in etfs)
    assert all(item.source_url.startswith("https://") and item.venue_source_url for item in etfs)
    assert all("provider_symbol" not in item.model_dump() for item in etfs)
    assert catalog.checksum == bundled_chart_watchlist_catalog().checksum
    assert replace(catalog, name="Other reviewed universe").checksum != catalog.checksum


@pytest.mark.parametrize(
    "changes",
    [
        {"isin": None},
        {"mic": None},
        {"currency": None},
        {"ticker": None},
        {"country_code": None},
        {"timezone": None},
        {"venue_source_url": None},
        {"source_url": "http://example.com/source"},
        {"source_url": "https://user:secret@example.com/source"},
        {"venue_source_url": "javascript:alert(1)"},
        {"currency": "UNKNOWN"},
        {"kind": "STOCK"},
    ],
)
def test_catalog_requires_complete_sourced_etf_identity(changes):
    item = bundled_chart_watchlist_catalog().items[1]
    with pytest.raises(ValidationError):
        ChartWatchlistDefinition.model_validate({**item.model_dump(), **changes})


def test_catalog_rejects_duplicate_security_and_synthetic_index_listing():
    catalog = bundled_chart_watchlist_catalog()
    with pytest.raises(ValueError, match="Duplicate watchlist code"):
        replace(catalog, items=(catalog.items[0], catalog.items[0]))
    other = catalog.items[1].model_copy(update={"code": "DUPLICATE_ETF"})
    with pytest.raises(ValueError, match="Duplicate ETF security"):
        replace(catalog, items=(catalog.items[1], other))
    with pytest.raises(ValidationError):
        ChartWatchlistDefinition.model_validate(
            {**catalog.items[0].model_dump(), "currency": "USD", "ticker": "GSPC"}
        )


@pytest.mark.asyncio
async def test_preview_is_read_only_and_does_not_consult_provider():
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = None
    provider = SimpleNamespace(verify=AsyncMock(side_effect=AssertionError("provider called")))
    service = ChartWatchlistService(session, uuid4(), etf_discovery=provider)
    result = await service.read()
    assert result.enabled is False
    assert len(result.items) == 31
    assert all(item.setup_status == "PENDING" and item.target_key is None for item in result.items)
    assert all(item.history.last_date is None for item in result.items)
    session.add.assert_not_called()
    session.commit.assert_not_awaited()
    provider.verify.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "confirmed,version,reason",
    [
        (
            False,
            "GLOBAL_MARKETS_ETF_V1_20261109",
            "CHART_WATCHLIST_CONFIRMATION_REQUIRED",
        ),
        (True, "unreviewed-version", "CHART_WATCHLIST_CATALOG_VERSION_MISMATCH"),
    ],
)
async def test_activation_rejects_missing_confirmation_and_unknown_version_without_io(
    confirmed, version, reason
):
    session = AsyncMock(spec=AsyncSession)
    service = ChartWatchlistService(session, uuid4())
    with pytest.raises(ChartWatchlistError, match=reason):
        await service.activate(
            catalog_version=version,
            confirmed=confirmed,
            actor=Actor("local-user", "User"),
        )
    session.scalar.assert_not_awaited()
    session.commit.assert_not_awaited()


def _owner_projection(*, index=False):
    now = datetime.now(UTC)
    workspace_id, underlying_id, listing_id, venue_id, reference_id, instrument_id = (
        uuid4() for _ in range(6)
    )
    catalog = bundled_chart_watchlist_catalog()
    definition = catalog.items[0 if index else 1]
    mapping = ProviderInstrumentMappingModel(
        id=uuid4(),
        workspace_id=workspace_id,
        listing_id=None if index else listing_id,
        market_data_instrument_id=instrument_id,
        provider=MarketDataProvider.EODHD,
        provider_symbol="GSPC" if index else "XLE",
        provider_exchange_code="INDX" if index else "US",
        status=MappingStatus.ACTIVE,
        version=2,
        validated_at=now,
    )
    member = ChartWatchlistMemberModel(
        workspace_id=workspace_id,
        code=definition.code,
        kind=definition.kind,
        definition=definition.model_dump(mode="json"),
        ordinal=0,
        listing_id=None if index else listing_id,
        market_reference_id=reference_id if index else None,
        last_attempt_at=now,
        setup_completed_at=now,
        verified_mapping_id=mapping.id,
        verified_mapping_version=2,
        verified_provider_symbol=mapping.provider_symbol,
        verified_provider_exchange_code=mapping.provider_exchange_code,
    )
    underlying = UnderlyingModel(
        id=underlying_id,
        workspace_id=workspace_id,
        type=UnderlyingType.ETF,
        isin=definition.isin,
        lifecycle_status=LifecycleStatus.ACTIVE,
    )
    listing = ListingModel(
        id=listing_id,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        trading_venue_id=venue_id,
        ticker=definition.ticker,
        currency_code=definition.currency,
        lifecycle_status=LifecycleStatus.ACTIVE,
    )
    venue = TradingVenueModel(id=venue_id, mic=definition.mic, is_active=True)
    currency = CurrencyModel(code="USD", is_active=True)
    reference = MarketReferenceModel(
        id=reference_id,
        workspace_id=workspace_id,
        code="SP500",
        reference_type="INDEX",
        active=True,
    )
    instrument = MarketDataInstrumentModel(
        id=instrument_id,
        workspace_id=workspace_id,
        kind="MARKET_REFERENCE" if index else "LISTING",
        listing_id=None if index else listing_id,
        market_reference_id=reference_id if index else None,
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalars.side_effect = [
        [] if index else [listing],
        [] if index else [underlying],
        [] if index else [venue],
        [] if index else [currency],
        [reference] if index else [],
        [instrument],
        [mapping],
        *(
            [
                [
                    ReferenceSeriesDefinitionModel(
                        market_reference_id=reference_id,
                        mapping_id=mapping.id,
                        mapping_version=mapping.version,
                        return_basis="PRICE_INDEX",
                    )
                ]
            ]
            if index
            else []
        ),
    ]
    session.execute.return_value = [(instrument_id, 3, date(2026, 11, 4), date(2026, 11, 6), now)]
    return SimpleNamespace(
        session=session,
        workspace_id=workspace_id,
        member=member,
        mapping=mapping,
        underlying=underlying,
        listing=listing,
        venue=venue,
        currency=currency,
        reference=reference,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("index", [False, True])
async def test_read_uses_owner_facts_and_preserves_native_history(index):
    case = _owner_projection(index=index)
    item = (await ChartWatchlistStateReader(case.session, case.workspace_id).read((case.member,)))[
        0
    ]
    assert item.setup_status == "CONFIGURED"
    assert item.setup_reason is None
    assert item.mapping.version == 2
    assert item.history.observation_count == 3
    assert item.history.first_date == date(2026, 11, 4)
    assert item.history.last_date == date(2026, 11, 6)
    assert item.history.last_received_at is not None
    assert item.target_key.startswith("reference:" if index else "listing:")
    assert item.currency is None if index else item.currency == "USD"
    case.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "owner,field,value,reason",
    [
        ("mapping", "version", 3, "MAPPING_CHANGED_SINCE_WATCHLIST_SETUP"),
        (
            "mapping",
            "provider_symbol",
            "WRONG",
            "MAPPING_CHANGED_SINCE_WATCHLIST_SETUP",
        ),
        (
            "mapping",
            "provider_exchange_code",
            "WRONG",
            "MAPPING_CHANGED_SINCE_WATCHLIST_SETUP",
        ),
        ("mapping", "id", uuid4(), "MAPPING_CHANGED_SINCE_WATCHLIST_SETUP"),
        (
            "mapping",
            "status",
            MappingStatus.DISABLED,
            "VALIDATED_EODHD_MAPPING_REQUIRED",
        ),
        ("mapping", "validated_at", None, "VALIDATED_EODHD_MAPPING_REQUIRED"),
        ("underlying", "type", UnderlyingType.STOCK, "ETF_LISTING_IDENTITY_CONFLICT"),
        ("underlying", "isin", "US0000000000", "ETF_LISTING_IDENTITY_CONFLICT"),
        (
            "underlying",
            "lifecycle_status",
            LifecycleStatus.INACTIVE,
            "ETF_MASTER_DATA_INACTIVE",
        ),
        (
            "listing",
            "lifecycle_status",
            LifecycleStatus.INACTIVE,
            "ETF_MASTER_DATA_INACTIVE",
        ),
        ("listing", "ticker", "OTHER", "ETF_LISTING_IDENTITY_CONFLICT"),
        ("listing", "currency_code", "EUR", "CURRENCY_INACTIVE_OR_MISSING"),
        ("venue", "mic", "XNYS", "ETF_LISTING_IDENTITY_CONFLICT"),
        ("venue", "is_active", False, "TRADING_VENUE_INACTIVE_OR_MISSING"),
        ("currency", "is_active", False, "CURRENCY_INACTIVE_OR_MISSING"),
    ],
)
async def test_later_owner_changes_block_watchlist_without_rewriting_facts(
    owner, field, value, reason
):
    case = _owner_projection()
    setattr(getattr(case, owner), field, value)
    item = (await ChartWatchlistStateReader(case.session, case.workspace_id).read((case.member,)))[
        0
    ]
    assert item.setup_status == "BLOCKED"
    assert item.setup_reason == reason
    assert item.history.observation_count == 3
    assert item.setup_completed_at == case.member.setup_completed_at
    case.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_active_mapping_without_finished_evidence_stays_pending():
    case = _owner_projection()
    case.member.setup_completed_at = None
    case.member.verified_mapping_id = None
    item = (await ChartWatchlistStateReader(case.session, case.workspace_id).read((case.member,)))[
        0
    ]
    assert item.setup_status == "PENDING"
    assert item.setup_reason == "MAPPING_CONFIRMATION_PENDING"


@pytest.mark.parametrize("change", ["foreign_id", "later_version"])
def test_resume_permission_is_bound_to_own_exact_mapping_attempt(change):
    case = _owner_projection()
    case.member.created_mapping_id = case.mapping.id
    case.member.created_mapping_version = case.mapping.version
    ChartWatchlistSetup._require_owned_attempt(case.member, case.mapping)
    if change == "foreign_id":
        case.mapping.id = uuid4()
    else:
        case.mapping.version += 1
    with pytest.raises(ChartWatchlistError, match="EXISTING_INACTIVE_MAPPING_PRESERVED"):
        ChartWatchlistSetup._require_owned_attempt(case.member, case.mapping)


@pytest.mark.asyncio
async def test_reserved_mapping_id_does_not_duplicate_owner_audit_ids():
    uow = Uow()
    reserved = uuid4()
    owner = ProviderMappingAdministrationService(uow, mapping_id_factory=lambda: reserved)
    command = MappingCommand(
        uuid4(), uuid4(), MarketDataProvider.EODHD, "XLE", "US", "actor", "User"
    )
    created = await owner.create_or_update(command)
    validated = await owner.validate(
        command.workspace_id, created.id, actor_id="actor", actor_name="User"
    )
    assert created.id == validated.id == reserved
    assert validated.version == 2
    audit_ids = [event.id for event in uow.audit_events.events]
    assert len(audit_ids) == len(set(audit_ids)) == 2
    assert reserved not in audit_ids


@pytest.mark.asyncio
async def test_create_only_mapping_refuses_existing_owner_without_resetting_its_revision():
    uow = Uow()
    owner = ProviderMappingAdministrationService(uow)
    command = MappingCommand(
        uuid4(), uuid4(), MarketDataProvider.EODHD, "XLE", "US", "actor", "User"
    )
    created = await owner.create_or_update(command)
    validated = await owner.validate(
        command.workspace_id, created.id, actor_id="actor", actor_name="User"
    )
    uow.committed = False
    with pytest.raises(ValueError, match="PROVIDER_MAPPING_ALREADY_EXISTS"):
        await owner.create_or_update(replace(command, provider_symbol="WRONG", require_absent=True))
    current = uow.mappings.value
    assert current.provider_symbol == "XLE"
    assert current.version == validated.version
    assert current.status == MappingStatus.ACTIVE
    assert len(uow.audit_events.events) == 2
    assert not uow.committed


@pytest.mark.asyncio
async def test_http_activation_requires_reviewed_scope_and_returns_scheduler_receipt():
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = None
    preview = await ChartWatchlistService(session, uuid4()).read()
    service = SimpleNamespace(read=AsyncMock(return_value=preview), activate=AsyncMock())
    service.activate.return_value = preview.model_copy(update={"enabled": True})
    wake = SimpleNamespace(set=lambda: None)
    application = FastAPI()
    application.include_router(router)
    application.state.market_data_refresh = SimpleNamespace(
        status=lambda: {
            "enabled": False,
            "leader": False,
            "jobs": [{"name": "unrelated warrant"}],
            "settings": {"underlyings_interval_seconds": 3600, "auto_configure": True},
        },
        wake=wake,
        container=SimpleNamespace(eodhd=None),
    )
    application.dependency_overrides[get_chart_watchlist_service] = lambda: service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/market-charts/watchlist")
        assert response.status_code == 200
        assert response.json()["scheduler"]["enabled"] is False
        assert response.json()["scheduler"]["settings"] == {"underlyings_interval_seconds": 3600}
        assert "jobs" not in response.json()["scheduler"]
        for body in (
            {"catalog_version": preview.catalog_version, "confirmed": False},
            {
                "catalog_version": preview.catalog_version,
                "confirmed": True,
                "provider_symbol": "ARBITRARY",
            },
        ):
            response = await client.post("/api/v1/market-charts/watchlist/activate", json=body)
            assert response.status_code == 422
        service.activate.assert_not_awaited()
        response = await client.post(
            "/api/v1/market-charts/watchlist/activate",
            json={"catalog_version": preview.catalog_version, "confirmed": True},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is True
        assert response.json()["items"][0]["setup_status"] == "PENDING"
        assert response.json()["scheduler"]["enabled"] is False
        service.activate.side_effect = ChartWatchlistError("CHART_WATCHLIST_CATALOG_CONFLICT")
        response = await client.post(
            "/api/v1/market-charts/watchlist/activate",
            json={"catalog_version": preview.catalog_version, "confirmed": True},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "CHART_WATCHLIST_CATALOG_CONFLICT"


async def _read_http_refresh_projection(jobs, *, provider_enabled):
    identity = "00000000-0000-4000-8000-000000000123"
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = None
    preview = await ChartWatchlistService(session, uuid4()).read()
    history = ChartWatchlistHistory(
        observation_count=3,
        first_date=date(2026, 11, 4),
        last_date=date(2026, 11, 6),
        last_received_at=datetime(2026, 11, 6, 22, tzinfo=UTC),
    )
    items = tuple(
        item.model_copy(
            update={
                "target_key": f"{kind}:{identity}",
                "setup_status": "CONFIGURED",
                "history": history,
            }
        )
        for item, kind in zip(preview.items[:2], ("reference", "listing"), strict=True)
    )
    service = SimpleNamespace(
        read=AsyncMock(return_value=preview.model_copy(update={"enabled": True, "items": items}))
    )
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_chart_watchlist_service] = lambda: service
    application.state.market_data_refresh = SimpleNamespace(
        status=lambda: {
            "enabled": True,
            "running": False,
            "last_error": None,
            "settings": {"underlyings_interval_seconds": 3600},
            "jobs": jobs,
        },
        container=SimpleNamespace(eodhd=object() if provider_enabled else None),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/market-charts/watchlist")
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_watchlist_projects_only_matching_eod_failures_without_hiding_saved_history():
    identity = "00000000-0000-4000-8000-000000000123"
    checked = datetime(2026, 11, 9, 12, tzinfo=UTC)
    jobs = [
        {
            "job": f"UNDERLYING_EOD:underlying:{identity}",
            "listing_id": identity,
            "status": "ERROR",
            "reason": "MarketDataUnavailableError",
            "checked_at": checked,
            "last_success_at": datetime(2026, 11, 6, 22, tzinfo=UTC),
            "next_run_at": datetime(2026, 11, 9, 13, tzinfo=UTC),
        },
        {
            "job": f"REFERENCE_EOD:{identity}",
            "market_reference_id": identity,
            "status": "BLOCKED",
            "reason": "EODHD_DISABLED",
            "checked_at": checked,
        },
        {"job": "CHART_SETUP:ETF_US_XLE", "listing_id": identity, "status": "AVAILABLE"},
        {"job": "WARRANT_QUOTES:other", "listing_id": identity, "status": "AVAILABLE"},
        {"job": "UNDERLYING_EOD:other", "listing_id": str(uuid4()), "status": "AVAILABLE"},
    ]
    response = await _read_http_refresh_projection(jobs, provider_enabled=False)
    index, etf = response["items"]
    assert response["scheduler"]["enabled"] is True
    assert response["scheduler"]["provider_enabled"] is False
    assert response["scheduler"]["last_error"] is None
    assert index["refresh"]["reason"] == "EODHD_DISABLED"
    assert index["refresh"]["status"] == "BLOCKED"
    assert etf["refresh"]["reason"] == "MarketDataUnavailableError"
    assert etf["refresh"]["status"] == "ERROR"
    assert etf["refresh"]["checked_at"] == "2026-11-09T12:00:00Z"
    assert etf["refresh"]["next_run_at"] == "2026-11-09T13:00:00Z"
    assert etf["refresh"]["scope"] == "PROCESS_LOCAL"
    assert etf["setup_status"] == "CONFIGURED"
    assert etf["history"]["last_date"] == "2026-11-06"
    assert etf["history"]["last_received_at"] == "2026-11-06T22:00:00Z"


@pytest.mark.asyncio
async def test_new_backend_process_does_not_invent_refresh_success_from_saved_history():
    response = await _read_http_refresh_projection([], provider_enabled=True)
    assert response["scheduler"]["provider_enabled"] is True
    assert all(item["refresh"] is None for item in response["items"])
    assert all(item["setup_status"] == "CONFIGURED" for item in response["items"])
    assert all(item["history"]["observation_count"] == 3 for item in response["items"])
