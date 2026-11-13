"""F207-4 read/transport contracts with synthetic owners and blocked commands."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

import app.features.trade_position.service.hebeltrader_evidence as service_module
from app.core.exceptions import ApplicationError, register_exception_handlers
from app.features.trade_position.api.hebeltrader_evidence import (
    WORKSPACE_ID,
    get_evidence_reader,
    get_evidence_service,
    router,
)
from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.hebeltrader_evidence import (
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
)
from app.features.trade_position.domain.models import Position, Trade
from app.features.trade_position.service.hebeltrader_coverage import (
    CoverageItem,
    HebeltraderCoverage,
)
from app.features.trade_position.service.hebeltrader_evidence import (
    HebeltraderEvidenceHistory,
    HebeltraderEvidenceReader,
    evidence_error,
)
from app.features.trade_position.service.valuation_basis import PositionValuationBasis

NOW = datetime(2026, 11, 14, 10, tzinfo=UTC)
TRADE_ID = UUID(int=7001)
POSITION_ID = UUID(int=7002)
PRODUCT_ID = UUID(int=7003)
UNDERLYING_ID = UUID(int=7004)
BASE = f"/api/v1/trade-position/trades/{TRADE_ID}/hebeltrader-evidence"


def report():
    position = Position(
        id=POSITION_ID,
        trade_id=TRADE_ID,
        product_id=PRODUCT_ID,
        open_quantity=10,
        cost_basis=Decimal("20.123456789"),
        average_entry_price=Decimal("2.0123456789"),
        opened_at=NOW,
        last_execution_at=NOW,
    )
    return HebeltraderCoverage(
        trade_id=TRADE_ID,
        position_id=POSITION_ID,
        product_id=PRODUCT_ID,
        underlying_id=UNDERLYING_ID,
        basis_id="synthetic-basis",
        read_started_at=NOW,
        read_completed_at=NOW,
        evidence_revision_id=None,
        evidence_recorded_at=None,
        coverage_status="INCOMPLETE",
        items=(CoverageItem("entry", "Einstiegsgruppe", "MISSING", "Fehlt.", ("B55",)),),
        original_z1_quantity=None,
        assigned_z1_sold_quantity=None,
        original_underlying_entry=None,
        personal_underlying_entry=None,
        underlying_currency=None,
        source=None,
        valuation_basis=PositionValuationBasis(
            "position-unrealized-gross-v1", "synthetic-owner", position, None, "UNKNOWN", (), ()
        ),
        execution_links=(),
    )


def app(reader, service=None):
    application = FastAPI()
    application.include_router(router)
    register_exception_handlers(application)
    application.dependency_overrides[get_evidence_reader] = lambda: reader
    if service is None:

        def forbidden_command_dependency():
            raise AssertionError("coverage/history GET constructed a command dependency")

        application.dependency_overrides[get_evidence_service] = forbidden_command_dependency
    else:
        application.dependency_overrides[get_evidence_service] = lambda: service
    return application


async def get(reader, suffix="", query=None):
    async with AsyncClient(
        transport=ASGITransport(app=app(reader)), base_url="http://test"
    ) as client:
        return await client.get(
            BASE + suffix,
            params=[("position_id", str(POSITION_ID))] if query is None else query,
        )


async def test_coverage_get_preserves_exact_decimals_identity_and_separate_status_dimensions():
    reader = AsyncMock(spec=HebeltraderEvidenceReader)
    reader.read.return_value = report()
    response = await get(reader)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["trade_id"] == str(TRADE_ID)
    assert body["position_id"] == str(POSITION_ID)
    assert body["valuation_basis"]["position"]["cost_basis"] == "20.123456789"
    assert body["definition_version"] == "hebeltrader-evidence-v1"
    assert body["implementation_status"] == "F207_4_EVIDENCE_ONLY"
    assert body["operation_status"] == "NOT_ASSESSED"
    assert body["read_started_at"] == body["read_completed_at"] == "2026-11-14T10:00:00Z"
    reader.read.assert_awaited_once_with(WORKSPACE_ID, TRADE_ID, POSITION_ID)
    reader.history.assert_not_awaited()


async def test_history_get_uses_only_history_reader_and_retains_empty_history():
    reader = AsyncMock(spec=HebeltraderEvidenceReader)
    reader.history.return_value = HebeltraderEvidenceHistory(
        TRADE_ID, POSITION_ID, None, (), NOW, NOW
    )
    response = await get(reader, "/history")
    assert response.status_code == 200, response.text
    assert response.json()["history"] == []
    reader.history.assert_awaited_once_with(WORKSPACE_ID, TRADE_ID, POSITION_ID)
    reader.read.assert_not_awaited()


@pytest.mark.parametrize("suffix", ["", "/history"])
@pytest.mark.parametrize(
    "query",
    [
        [],
        [("position_id", "not-a-uuid")],
        [("position_id", "")],
        [("position_id", str(POSITION_ID)), ("position_id", str(POSITION_ID))],
        [("position_id", str(POSITION_ID)), ("position_id", str(uuid4()))],
    ],
)
async def test_position_query_is_required_unique_and_valid_before_read(suffix, query):
    reader = AsyncMock(spec=HebeltraderEvidenceReader)
    response = await get(reader, suffix, query)
    assert response.status_code == 422, response.text
    reader.read.assert_not_awaited()
    reader.history.assert_not_awaited()


@pytest.mark.parametrize("suffix,method", [("", "read"), ("/history", "history")])
async def test_owner_identity_error_is_not_missing_evidence(suffix, method):
    reader = AsyncMock(spec=HebeltraderEvidenceReader)
    getattr(reader, method).side_effect = evidence_error(
        "BASELINE_POSITION_NOT_FOUND", "Fremde Position.", 404
    )
    response = await get(reader, suffix)
    assert response.status_code == 404
    assert response.json()["code"] == "BASELINE_POSITION_NOT_FOUND"
    assert "coverage_status" not in response.json()


@pytest.mark.parametrize("suffix,method", [("", "read"), ("/history", "history")])
async def test_database_failure_is_not_an_empty_success_or_private_error_detail(suffix, method):
    reader = AsyncMock(spec=HebeltraderEvidenceReader)
    getattr(reader, method).side_effect = DBAPIError("private SQL", {}, Exception("private token"))
    response = await get(reader, suffix)
    assert response.status_code == 503
    assert response.json()["code"] == "BASELINE_EVIDENCE_READ_UNAVAILABLE"
    assert "private" not in response.text
    assert "coverage_status" not in response.json()


def command_body():
    return {
        "position_id": str(POSITION_ID),
        "request_id": str(uuid4()),
        "confirmation": "CONFIRM_HISTORICAL_EVIDENCE",
        "declaration": {
            "entry_order": {
                "source_reference": "synthetic-order",
                "execution_ids": [str(uuid4())],
                "complete": True,
            },
            "underlying_trades": [
                {
                    "execution_id": str(uuid4()),
                    "source_reference": "synthetic-trade",
                    "price": "100",
                    "binding": {
                        "basis": "UNDERLYING",
                        "instrument_id": str(UNDERLYING_ID),
                        "currency": "USD",
                    },
                    "scale_reference": "synthetic-scale",
                    "last_trade_verified": True,
                    "observed_at": "2026-08-03T09:00:00Z",
                    "price_kind": "TRADE",
                }
            ],
        },
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda body: body.update(automatic_execution=True),
        lambda body: body.update(confirmation="CONFIRM_ORDER"),
        lambda body: body["declaration"].update(activate_baseline=True),
        lambda body: body["declaration"]["entry_order"].update(complete="true"),
        lambda body: body["declaration"]["entry_order"].update(order_quantity=50),
        lambda body: body["declaration"]["underlying_trades"][0].update(price_kind="BID"),
        lambda body: body["declaration"]["underlying_trades"][0].update(price="NaN"),
        lambda body: body["declaration"]["underlying_trades"][0].update(
            observed_at="2026-08-03T09:00:00"
        ),
        lambda body: body["declaration"]["underlying_trades"][0].update(observed_on="2026-08-03"),
        lambda body: body["declaration"]["underlying_trades"][0].update(
            observed_at=None, observed_on="2026-08-03"
        ),
        lambda body: body["declaration"]["underlying_trades"][0].update(
            observed_at=None, observed_on="2026-08-03", observation_timezone="Invalid/Zone"
        ),
        lambda body: body["declaration"]["underlying_trades"][0].update(
            observation_timezone="Europe/Berlin"
        ),
        lambda body: body["declaration"]["underlying_trades"][0]["binding"].update(basis="UNKNOWN"),
        lambda body: body["declaration"]["underlying_trades"][0]["binding"].update(currency="GBp"),
        lambda body: body["declaration"]["underlying_trades"][0]["binding"].update(
            inferred_price=True
        ),
    ],
)
async def test_malformed_evidence_is_rejected_before_command_or_read(mutation):
    reader, service = AsyncMock(), AsyncMock()
    body = command_body()
    mutation(body)
    async with AsyncClient(
        transport=ASGITransport(app=app(reader, service)), base_url="http://test"
    ) as client:
        response = await client.post(BASE, json=body)
    assert response.status_code == 422, response.text
    service.record.assert_not_called()
    reader.read.assert_not_called()
    reader.history.assert_not_called()


@pytest.mark.parametrize("fail_inside", [False, True])
async def test_snapshot_is_read_only_repeatable_no_autoflush_and_rolled_back(
    monkeypatch, fail_inside
):
    session = AsyncMock(spec=AsyncSession)
    session.__aenter__.return_value = session
    factory = Mock(return_value=session)
    monkeypatch.setattr(service_module, "AsyncSession", factory)
    engine = Mock()
    reader = HebeltraderEvidenceReader(engine)
    try:
        async with reader._snapshot() as snapshot:
            assert snapshot is session
            assert [str(call.args[0]) for call in session.execute.await_args_list] == [
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
                "SET LOCAL statement_timeout = '10000ms'",
            ]
            if fail_inside:
                raise RuntimeError("synthetic read failure")
    except RuntimeError:
        assert fail_inside
    factory.assert_called_once_with(engine, expire_on_commit=False, autoflush=False)
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()
    session.add.assert_not_called()


async def test_context_uses_read_owner_and_rejects_foreign_position_before_other_sources(
    monkeypatch,
):
    trade = Trade(TRADE_ID, WORKSPACE_ID, PRODUCT_ID, TradeOrigin.EXTERNAL, NOW, uuid4())
    trade_repository = Mock(get=AsyncMock(return_value=trade))
    position_repository = Mock(
        get_for_trade=AsyncMock(return_value=replace(report().valuation_basis.position, id=uuid4()))
    )
    monkeypatch.setattr(
        service_module, "SqlAlchemyReadOnlyTradeRepository", Mock(return_value=trade_repository)
    )
    write_owner = Mock(side_effect=AssertionError("read must not instantiate write owner"))
    monkeypatch.setattr(service_module, "SqlAlchemyTradeRepository", write_owner)
    monkeypatch.setattr(
        service_module, "SqlAlchemyPositionRepository", Mock(return_value=position_repository)
    )
    source_owner = Mock(side_effect=AssertionError("identity failure must stop before other reads"))
    monkeypatch.setattr(service_module, "WarrantService", source_owner)
    session = AsyncMock(spec=AsyncSession)
    with pytest.raises(ApplicationError) as error:
        await service_module._context(
            session,
            workspace_id=WORKSPACE_ID,
            trade_id=TRADE_ID,
            position_id=POSITION_ID,
            lock=False,
        )
    assert error.value.code == "BASELINE_POSITION_NOT_FOUND"
    session.scalars.assert_not_called()
    write_owner.assert_not_called()
    source_owner.assert_not_called()


@pytest.mark.parametrize("has_revision", [False, True])
async def test_read_consumes_only_owner_snapshot_and_explicit_pin(monkeypatch, has_revision):
    session = AsyncMock(spec=AsyncSession)
    session.__aenter__.return_value = session
    monkeypatch.setattr(service_module, "AsyncSession", Mock(return_value=session))
    basis = Mock()
    context = AsyncMock(return_value=(basis, UNDERLYING_ID))
    monkeypatch.setattr(service_module, "_context", context)
    pin = uuid4()
    revision = HebeltraderEvidenceRevision(
        uuid4(),
        WORKSPACE_ID,
        TRADE_ID,
        POSITION_ID,
        PRODUCT_ID,
        UNDERLYING_ID,
        HebeltraderEvidenceDeclaration(source_version_id=pin),
        NOW,
        uuid4(),
        uuid4(),
        "synthetic-request",
    )
    repository = Mock(history=AsyncMock(return_value=(revision,) if has_revision else ()))
    monkeypatch.setattr(
        service_module, "SqlAlchemyHebeltraderEvidenceRepository", Mock(return_value=repository)
    )
    source = AsyncMock(return_value=None)
    monkeypatch.setattr(service_module, "_source", source)
    projection = Mock(return_value=report())
    monkeypatch.setattr(service_module, "build_hebeltrader_coverage", projection)
    assert (
        await HebeltraderEvidenceReader(Mock()).read(WORKSPACE_ID, TRADE_ID, POSITION_ID)
        == report()
    )
    context.assert_awaited_once_with(
        session, workspace_id=WORKSPACE_ID, trade_id=TRADE_ID, position_id=POSITION_ID, lock=False
    )
    source.assert_awaited_once_with(
        session,
        basis=basis,
        underlying_id=UNDERLYING_ID,
        source_version_id=pin if has_revision else None,
        reuse_trade_link=not has_revision,
    )
    session.commit.assert_not_called()
    session.rollback.assert_awaited_once()
    session.flush.assert_not_called()


async def test_history_does_not_read_source_or_evaluate_coverage(monkeypatch):
    session = AsyncMock(spec=AsyncSession)
    session.__aenter__.return_value = session
    monkeypatch.setattr(service_module, "AsyncSession", Mock(return_value=session))
    monkeypatch.setattr(service_module, "_context", AsyncMock())
    repository = Mock(history=AsyncMock(return_value=()))
    monkeypatch.setattr(
        service_module, "SqlAlchemyHebeltraderEvidenceRepository", Mock(return_value=repository)
    )
    source, projection = AsyncMock(), Mock()
    monkeypatch.setattr(service_module, "_source", source)
    monkeypatch.setattr(service_module, "build_hebeltrader_coverage", projection)
    result = await HebeltraderEvidenceReader(Mock()).history(WORKSPACE_ID, TRADE_ID, POSITION_ID)
    assert result.history == () and result.current_revision_id is None
    source.assert_not_called()
    projection.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_awaited_once()
