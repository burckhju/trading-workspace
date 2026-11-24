"""Passive HTTP reads bind the existing listing and cannot choose source semantics."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.unit.backend.features.product.test_listing_unit_review_composition import (
    ROUTE,
    current_listing_evidence,
    kids,
)

from app.core.config import Environment, Settings
from app.features.market.persistence.models import TradingVenueModel
from app.features.product.api import listing_unit_evidence as api
from app.features.product.persistence.models import WarrantListingModel
from app.features.product.service import listing_unit_read as service
from app.main import create_application

pytestmark = pytest.mark.asyncio
URL = f"/api/v1/warrants/{kids.WARRANT}/listings/{ROUTE.listing_id}/current-unit-evidence"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return kids.NOW.astimezone(tz or UTC)


class ReadSession:
    def __init__(self):
        self.statements = []
        self.listing = SimpleNamespace(
            id=ROUTE.listing_id,
            workspace_id=kids.WORKSPACE,
            warrant_id=kids.WARRANT,
            trading_venue_id=UUID(int=1401),
            quotation_currency_code="EUR",
        )
        self.venue = SimpleNamespace(mic="MUND")
        self.rollback = AsyncMock()
        self.commit = AsyncMock(side_effect=AssertionError("passive read committed"))
        self.flush = AsyncMock(side_effect=AssertionError("passive read flushed"))
        self.add = Mock(side_effect=AssertionError("passive read wrote"))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def execute(self, statement):
        self.statements.append(str(statement))

    async def get(self, model, identity):
        if model is WarrantListingModel:
            assert identity == ROUTE.listing_id
            return self.listing
        assert model is TradingVenueModel
        assert identity == UUID(int=1401)
        return self.venue


@pytest.fixture
def context(monkeypatch):
    application = create_application(
        Settings(_env_file=None, environment=Environment.TEST, documentation_enabled=True)
    )
    session = ReadSession()
    engine = Mock(spec=AsyncEngine)
    factory = Mock(return_value=session)
    owner = SimpleNamespace(
        current=AsyncMock(
            return_value=current_listing_evidence(
                SimpleNamespace(id=UUID(int=1801), document_sha256="e" * 64)
            )
        )
    )
    require_warrant = AsyncMock()
    monkeypatch.setattr(service, "AsyncSession", factory)
    monkeypatch.setattr(service, "ListingUnitEvidenceReader", lambda session: owner)
    monkeypatch.setattr(service, "require_warrant", require_warrant)
    monkeypatch.setattr(service, "datetime", FrozenDatetime)
    monkeypatch.setattr(api, "WORKSPACE_ID", kids.WORKSPACE)
    application.dependency_overrides[api.get_read_service] = (
        lambda: service.ListingUnitEvidenceReadService(engine)
    )
    yield SimpleNamespace(
        app=application,
        session=session,
        owner=owner,
        factory=factory,
        engine=engine,
        require_warrant=require_warrant,
    )
    application.dependency_overrides.clear()


async def get(context, suffix=""):
    async with AsyncClient(
        transport=ASGITransport(app=context.app), base_url="http://test"
    ) as client:
        return await client.get(URL + suffix)


async def test_listing_clock_and_scope_are_server_owned_and_read_is_rolled_back(context):
    response = await get(context)
    assert response.status_code == 200, response.text
    assert response.json()["operation_status"] == "READ_ONLY"
    assert "document_base64" not in response.text
    assert "original_row" not in response.text
    context.require_warrant.assert_awaited_once_with(
        context.session, workspace_id=kids.WORKSPACE, warrant_id=kids.WARRANT
    )
    context.owner.current.assert_awaited_once_with(
        workspace_id=kids.WORKSPACE,
        warrant_id=kids.WARRANT,
        route=ROUTE,
        known_at=kids.NOW,
        event_at=kids.NOW,
    )
    context.factory.assert_called_once_with(context.engine, expire_on_commit=False, autoflush=False)
    assert context.session.statements == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    context.session.rollback.assert_awaited_once()
    context.session.commit.assert_not_awaited()
    context.session.flush.assert_not_awaited()
    context.session.add.assert_not_called()


@pytest.mark.parametrize(
    "query",
    ["known_at=2026-01-01", "provider=OTHER", "currency=USD", "refresh=true", "verified=true"],
)
async def test_query_cannot_supply_clock_source_currency_or_qualification(context, query):
    response = await get(context, "?" + query)
    assert response.status_code == 422
    assert response.json()["code"] == "LISTING_UNIT_QUERY_INVALID"
    context.factory.assert_not_called()


@pytest.mark.parametrize("change", ["missing", "foreign_workspace", "foreign_product"])
async def test_unknown_or_foreign_listing_never_reaches_evidence_owner(context, change):
    if change == "missing":
        context.session.listing = None
    elif change == "foreign_workspace":
        context.session.listing.workspace_id = UUID(int=9991)
    else:
        context.session.listing.warrant_id = UUID(int=9992)
    response = await get(context)
    assert response.status_code == 404
    context.owner.current.assert_not_awaited()
    context.session.rollback.assert_awaited_once()


async def test_missing_venue_mic_is_not_filled_from_the_source_name(context):
    context.session.venue.mic = None
    response = await get(context)
    assert response.status_code == 422
    assert response.json()["code"] == "LISTING_UNIT_ROUTE_UNSUPPORTED"
    context.owner.current.assert_not_awaited()


async def test_actual_listing_currency_is_passed_to_owner_validation(context):
    context.session.listing.quotation_currency_code = "USD"
    await get(context)
    assert context.owner.current.await_args.kwargs["route"] == replace(ROUTE, currency="USD")


async def test_database_error_is_bounded_and_rolls_back_without_leaking_sql(context):
    context.owner.current.side_effect = DBAPIError(
        "private sql", {"secret": "private value"}, Exception("private database details")
    )
    response = await get(context)
    assert response.status_code == 503
    assert response.json()["code"] == "LISTING_UNIT_READ_UNAVAILABLE"
    assert "private" not in response.text
    context.session.rollback.assert_awaited_once()


async def test_no_http_import_is_exposed(context):
    async with AsyncClient(
        transport=ASGITransport(app=context.app), base_url="http://test"
    ) as client:
        response = await client.post(URL, json={"verified": True})
    assert response.status_code == 405
    context.factory.assert_not_called()
