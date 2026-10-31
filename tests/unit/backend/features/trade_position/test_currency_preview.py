"""Read-only previews use the existing resolver and exact proposed time, never a booking."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.unit.backend.features.trade_position.currency_evidence_fixtures import (
    FRANKFURT,
    document,
    historical,
    listing,
)
from tests.unit.backend.features.trade_position.test_currency_resolution import (
    AT,
    TRADE,
    confirmed,
    execution,
)

from app.core.exceptions import ApplicationError, register_exception_handlers
from app.features.trade_position.api.router import WORKSPACE_ID, router
from app.features.trade_position.api.source_router import get_source_reader
from app.features.trade_position.domain.currency import ExecutionCurrencyResolution
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidenceLimitExceeded,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.service import source_view
from app.features.trade_position.service.source_view import (
    TradeSourceReader,
    source_error,
)

BASE = "/api/v1/trade-position"
DAY = {"executed_on": "2026-08-20", "execution_timezone": "Europe/Vienna"}


def api(reader):
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_source_reader] = lambda: reader
    return TestClient(app)


@pytest.mark.parametrize("kind,side", [("trades", "BUY"), ("trades", "SELL"), ("products", "BUY")])
@pytest.mark.parametrize("precision", ["date", "instant"])
def test_preview_api_preserves_context_time_and_existing_provenance(kind, side, precision):
    reader = AsyncMock(spec=TradeSourceReader)
    identity = uuid4()
    source = uuid4()
    declaration = uuid4()
    reader.execution_currency_preview.return_value = ExecutionCurrencyResolution(
        "EUR", "PRIOR_BUYS", (source,), (declaration,)
    )
    times = DAY if precision == "date" else {"executed_at": "2026-08-20T09:37:12+02:00"}
    response = api(reader).get(
        f"{BASE}/{kind}/{identity}/execution-currency-preview",
        params={"side": side, **times},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "currency_code": "EUR",
        "source": "PRIOR_BUYS",
        "source_execution_ids": [str(source)],
        "confirmation_ids": [str(declaration)],
        "evidence_ids": [],
        "evidence": [],
        "reason": None,
        "resolver_version": "execution-currency-v3",
    }
    expected = {
        "trade_id" if kind == "trades" else "product_id": identity,
        "side": ExecutionSide(side),
        "executed_at": (
            datetime(2026, 8, 19, 22, tzinfo=UTC)
            if precision == "date"
            else datetime(2026, 8, 20, 7, 37, 12, tzinfo=UTC)
        ),
    }
    if precision == "date":
        expected.update(executed_on=date(2026, 8, 20), execution_timezone="Europe/Vienna")
    reader.execution_currency_preview.assert_awaited_once_with(WORKSPACE_ID, **expected)


@pytest.mark.parametrize(
    "query",
    [
        {"side": "SELL"},
        DAY,
        {"side": "OTHER", **DAY},
        {"side": "BUY", "executed_on": "2026-08-20"},
        {"side": "BUY", **DAY, "execution_timezone": "Mars/Olympus"},
        {"side": "BUY", "executed_at": "2026-08-20T09:37:12"},
        {"side": "BUY", **DAY, "executed_at": "2026-08-20T09:37:12Z"},
        {"side": "BUY", **DAY, "executed_on": "2099-01-01"},
        {"side": "BUY", "executed_at": "2099-01-01T00:00:00Z"},
        {"side": "BUY", **DAY, "currency_confirmation": "USER_CONFIRMED"},
        {"side": "BUY", **DAY, "quantity": "100"},
        {"side": "BUY", **DAY, "price_per_unit": "2"},
        {"side": "BUY", **DAY, "request_id": str(uuid4())},
        [("side", "BUY"), ("side", "SELL"), *DAY.items()],
        [("side", "BUY"), *DAY.items(), ("executed_on", "2026-08-21")],
    ],
)
def test_invalid_ambiguous_or_command_inputs_never_read_or_infer_now(query):
    reader = AsyncMock(spec=TradeSourceReader)
    response = api(reader).get(f"{BASE}/trades/{TRADE.id}/execution-currency-preview", params=query)
    assert response.status_code == 422, response.text
    reader.execution_currency_preview.assert_not_awaited()


@pytest.mark.parametrize("kind", ["trades", "products"])
def test_preview_is_get_only_and_database_failures_are_not_empty_evidence(kind):
    reader = AsyncMock(spec=TradeSourceReader)
    client = api(reader)
    path = f"{BASE}/{kind}/{uuid4()}/execution-currency-preview"
    assert client.post(path, json={"side": "BUY", **DAY}).status_code == 405
    reader.execution_currency_preview.assert_not_awaited()
    reader.execution_currency_preview.side_effect = DBAPIError(
        "private SQL", {}, Exception("private credential")
    )
    response = client.get(path, params={"side": "BUY", **DAY})
    assert response.status_code == 503
    assert response.json()["code"] == "SOURCE_READ_UNAVAILABLE"
    assert "private" not in response.text and "currency_code" not in response.json()


def test_initial_product_preview_requires_buy_and_does_not_read_for_sell():
    reader = AsyncMock(spec=TradeSourceReader)
    response = api(reader).get(
        f"{BASE}/products/{uuid4()}/execution-currency-preview",
        params={"side": "SELL", **DAY},
    )
    assert response.status_code == 422
    reader.execution_currency_preview.assert_not_awaited()


@pytest.fixture
def source_reader(monkeypatch):
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = TRADE.product_id
    reader = TradeSourceReader(Mock())

    @asynccontextmanager
    async def snapshot():
        yield session

    monkeypatch.setattr(reader, "_session", snapshot)
    monkeypatch.setattr(reader, "_trade", AsyncMock(return_value=TRADE))
    monkeypatch.setattr(reader, "_bounded", AsyncMock())
    executions = AsyncMock()
    executions.list_for_trade.return_value = []
    confirmations = AsyncMock()
    confirmations.current_for_trade.return_value = {}
    evidence = AsyncMock()
    evidence.list_for_product.return_value = ()
    for name, value in (
        ("SqlAlchemyExecutionRecordRepository", executions),
        ("SqlAlchemyExecutionCurrencyConfirmationRepository", confirmations),
        ("SqlAlchemyCurrencyEvidenceRepository", evidence),
    ):
        monkeypatch.setattr(source_view, name, Mock(return_value=value))
    yield reader, session, executions, confirmations, evidence
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
    executions.add.assert_not_awaited()
    confirmations.add.assert_not_awaited()
    evidence.add.assert_not_awaited()


def preview(reader, *, product=False, side=ExecutionSide.SELL, **kwargs):
    return asyncio.run(
        reader.execution_currency_preview(
            TRADE.workspace_id,
            **({"product_id": TRADE.product_id} if product else {"trade_id": TRADE.id}),
            side=ExecutionSide.BUY if product else side,
            **({"executed_at": AT + timedelta(days=20)} | kwargs),
        )
    )


@pytest.mark.parametrize("side", [ExecutionSide.BUY, ExecutionSide.SELL])
def test_existing_buy_is_reused_without_creating_a_confirmation(source_reader, side):
    reader, _, executions, confirmations, evidence = source_reader
    original = execution(10)
    declaration = confirmed(original)
    executions.list_for_trade.return_value = [original]
    confirmations.current_for_trade.return_value = {original.id: declaration}
    result = preview(reader, side=side)
    assert result == ExecutionCurrencyResolution(
        "EUR", "PRIOR_BUYS", (original.id,), (declaration.id,)
    )
    reader._trade.assert_awaited_once_with(source_reader[1], TRADE.workspace_id, TRADE.id)
    executions.list_for_trade.assert_awaited_once_with(TRADE.id)
    confirmations.current_for_trade.assert_awaited_once_with(TRADE.workspace_id, TRADE.id)
    evidence.list_for_product.assert_awaited_once_with(
        TRADE.workspace_id, TRADE.product_id, limit=source_view.MAX_FACTS
    )
    assert reader._bounded.await_count == 2


def test_proposed_earlier_time_does_not_borrow_later_purchase_currency(source_reader):
    reader, _, executions, confirmations, _ = source_reader
    original = execution(10)
    executions.list_for_trade.return_value = [original]
    confirmations.current_for_trade.return_value = {original.id: confirmed(original)}
    result = preview(reader, executed_at=AT + timedelta(days=9))
    assert result.currency_code is None and result.source == "UNKNOWN"
    assert result.source_execution_ids == result.confirmation_ids == ()


@pytest.mark.parametrize("currency,expected", [(None, "UNKNOWN"), ("USD", "MIXED")])
def test_incomplete_or_mixed_purchase_prefix_needs_user_input(source_reader, currency, expected):
    reader, _, executions, confirmations, _ = source_reader
    first, second = execution(10), execution(11)
    executions.list_for_trade.return_value = [first, second]
    confirmations.current_for_trade.return_value = {second.id: confirmed(second)}
    if currency is not None:
        confirmations.current_for_trade.return_value[first.id] = confirmed(first, currency)
    result = preview(reader)
    assert result.currency_code is None and result.source == expected
    assert result.source_execution_ids == (first.id, second.id)


def test_effective_correction_retains_confirmed_ancestry_without_reusing_superseded_buy(
    source_reader,
):
    reader, _, executions, confirmations, _ = source_reader
    first = execution(10)
    correction = replace(execution(12), supersedes_execution_id=first.id)
    executions.list_for_trade.return_value = [first, correction]
    confirmations.current_for_trade.return_value = {first.id: confirmed(first)}
    result = preview(reader)
    assert result.currency_code == "EUR" and result.source == "PRIOR_BUYS"
    assert result.source_execution_ids == (correction.id, first.id)
    assert result.confirmation_ids == (confirmed(first).id,)
    assert preview(reader, executed_at=AT + timedelta(days=11)).currency_code is None


@pytest.mark.parametrize("kind", ["exact", "full_day", "partial_day", "outside", "conflict"])
def test_initial_preview_uses_only_valid_complete_historical_sources(source_reader, kind):
    reader, session, executions, confirmations, evidence = source_reader
    start = datetime(2026, 8, 19, 22, tzinfo=UTC)
    end = datetime(2026, 8, 20, 22, tzinfo=UTC)
    sources = [historical(TRADE, start=start, end=end)]
    kwargs = {"executed_at": start + timedelta(hours=12)}
    if kind in {"full_day", "partial_day"}:
        kwargs = {
            "executed_at": start,
            "executed_on": date(2026, 8, 20),
            "execution_timezone": "Europe/Vienna",
        }
    if kind == "partial_day":
        sources = [replace(sources[0], valid_to=end - timedelta(minutes=1))]
    if kind == "outside":
        kwargs = {"executed_at": end}
    if kind == "conflict":
        sources.append(historical(TRADE, number=8002, codes=(listing(code="USD"),)))
    # An existing execution's document is never bound to the proposed first purchase.
    sources.append(document(TRADE, uuid4(), code="CHF"))
    evidence.list_for_product.return_value = tuple(sources)
    result = preview(reader, product=True, **kwargs)
    if kind in {"exact", "full_day"}:
        assert result.currency_code == "EUR" and result.source == "HISTORICAL_LISTINGS"
        assert result.evidence_ids == (sources[0].id,)
        assert result.evidence[0].source_reference == sources[0].source_reference
        assert result.evidence[0].valid_from == start and result.evidence[0].valid_to == end
    else:
        assert result.currency_code is None
        assert result.source == ("CONFLICT" if kind == "conflict" else "UNKNOWN")
    assert sources[-1].id not in result.evidence_ids
    assert result.source_execution_ids == result.confirmation_ids == ()
    executions.list_for_trade.assert_not_awaited()
    confirmations.current_for_trade.assert_not_awaited()
    statement = session.scalar.await_args.args[0]
    assert statement.compile().params == {
        "workspace_id_1": TRADE.workspace_id,
        "id_1": TRADE.product_id,
    }
    assert "FOR UPDATE" not in str(statement.compile(dialect=postgresql.dialect()))


def test_product_preview_without_history_never_reads_current_listings_or_other_trade_facts(
    source_reader,
):
    reader, session, executions, confirmations, evidence = source_reader
    evidence.list_for_product.return_value = (document(TRADE, uuid4()),)
    result = preview(reader, product=True)
    assert result == ExecutionCurrencyResolution()
    assert session.scalar.await_count == 1
    assert "warrant_listings" not in str(session.scalar.await_args.args[0])
    executions.list_for_trade.assert_not_awaited()
    confirmations.current_for_trade.assert_not_awaited()


def test_historical_derivation_never_seeds_reuse_outside_its_interval(source_reader):
    reader, _, executions, _, evidence = source_reader
    executions.list_for_trade.return_value = [execution(10)]
    evidence.list_for_product.return_value = (
        historical(TRADE, start=AT, end=AT + timedelta(days=15)),
    )
    result = preview(reader)
    assert result.currency_code is None and result.source == "UNKNOWN"
    assert result.confirmation_ids == ()


def test_same_venue_conflict_blocks_existing_confirmed_buy_reuse(source_reader):
    reader, _, executions, confirmations, evidence = source_reader
    first = execution(10)
    executions.list_for_trade.return_value = [first]
    confirmations.current_for_trade.return_value = {first.id: confirmed(first)}
    evidence.list_for_product.return_value = (
        historical(TRADE),
        historical(TRADE, number=8002, codes=(listing(code="USD"), listing(FRANKFURT))),
    )
    result = preview(reader)
    assert result.currency_code is None and result.source == "CONFLICT"
    assert result.reason == "LISTING_CONFLICT" and len(result.evidence_ids) == 2


@pytest.mark.parametrize(
    "problem",
    [
        "missing_product",
        "missing_trade",
        "cancelled",
        "bounds",
        "evidence",
        "provenance",
    ],
)
def test_context_and_read_limits_fail_closed_without_partial_result(
    source_reader, monkeypatch, problem
):
    reader, session, executions, confirmations, evidence = source_reader
    status = 413
    product = False
    if problem == "missing_product":
        product = True
        session.scalar.return_value = None
        status = 404
    elif problem == "missing_trade":
        reader._trade.side_effect = source_error("TRADE_NOT_FOUND", "Trade nicht gefunden.", 404)
        status = 404
    elif problem == "cancelled":
        reader._trade.return_value = replace(
            TRADE,
            cancelled_at=AT,
            cancelled_by=UUID(int=8),
            cancellation_reason="Synthetic error",
        )
        status = 409
    elif problem == "bounds":
        reader._bounded.side_effect = source_error("SOURCE_RESOURCE_LIMIT", "Limit", 413)
    elif problem == "evidence":
        evidence.list_for_product.side_effect = CurrencyEvidenceLimitExceeded("Limit")
    else:
        original = execution(10)
        executions.list_for_trade.return_value = [original]
        confirmations.current_for_trade.return_value = {original.id: confirmed(original)}
        monkeypatch.setattr(source_view, "MAX_CURRENCY_PROVENANCE_LINKS", 1)
    with pytest.raises(ApplicationError) as error:
        preview(reader, product=product)
    assert error.value.status_code == status


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"trade_id": TRADE.id, "product_id": TRADE.product_id},
        {"product_id": TRADE.product_id},
    ],
)
def test_ambiguous_scope_or_initial_sale_never_opens_snapshot(source_reader, arguments):
    reader, session, *_ = source_reader
    with pytest.raises(ValueError):
        asyncio.run(
            reader.execution_currency_preview(
                TRADE.workspace_id, side=ExecutionSide.SELL, executed_at=AT, **arguments
            )
        )
    session.scalar.assert_not_awaited()
    reader._trade.assert_not_awaited()
