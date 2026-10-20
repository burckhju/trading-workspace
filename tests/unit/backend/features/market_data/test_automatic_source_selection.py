"""Exercise persistent route selection, history and monitoring across refreshes."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import MetaData, select, text
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained_fixtures
from tests.unit.backend.features.market_data.test_retained_quotes import (
    SqlSession,
)

from app.features.market.persistence.models import CurrencyModel, IssuerModel
from app.features.market_data.domain.enums import MappingStatus
from app.features.market_data.domain.enums import MarketDataProvider as P
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel as Selection,
)
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel as Mapping,
)
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository as Repository,
)
from app.features.market_data.service import refresh as refresh_module
from app.features.market_data.service.position_quote_source import (
    POSITION_QUOTE_SOURCE_POLICY_V1 as GENERIC_POLICY,
)
from app.features.market_data.service.position_quote_source import (
    PositionQuoteSourceSelector as Selector,
)
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.features.market_data.service.source_reconciliation import reconcile_warrant_positions
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel

context = retained_fixtures.context

NOW = datetime(2026, 9, 28, 18, tzinfo=UTC)


class SelectionSession(SqlSession):
    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def flush(self):
        self.session.flush()


@pytest.fixture
def selection_context(context):
    c = context
    for model in (CurrencyModel, IssuerModel, TradeModel, PositionModel):
        model.__table__.create(c.database.engine)
    # Mirror the PostgreSQL partial unique index in SQLite, without modifying
    # production metadata. SQLite does not implement the PostgreSQL row locks.
    metadata = MetaData()
    for table in Selection.metadata.tables.values():
        table.to_metadata(metadata)
    table = metadata.tables[Selection.__tablename__]
    for index in table.indexes:
        if index.name == "uq_position_quote_source_selections_active_position":
            index.dialect_options["sqlite"]["where"] = text("superseded_at IS NULL")
    table.create(c.database.engine)
    c.position, c.trade = uuid4(), uuid4()
    c.workspace = c.request.workspace_id
    with Session(c.database.engine) as session:
        warrant = session.get(WarrantModel, c.warrant)
        session.add(
            IssuerModel(
                id=warrant.issuer_id,
                legal_name="Test issuer",
                display_name="Test issuer",
                is_active=True,
                version=1,
                created_at=NOW,
                updated_at=NOW,
            )
        )
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
            TradeModel(
                id=c.trade,
                workspace_id=c.workspace,
                product_id=c.warrant,
                origin="EXTERNAL",
                created_at=NOW,
                created_by=uuid4(),
            )
        )
        session.add(
            PositionModel(
                id=c.position,
                trade_id=c.trade,
                product_id=c.warrant,
                open_quantity=10,
                cost_basis=Decimal(10),
                average_entry_price=Decimal(1),
                opened_at=NOW,
                last_execution_at=NOW,
            )
        )
        session.commit()

    @asynccontextmanager
    async def session_context():
        with Session(c.database.engine, expire_on_commit=False) as session:
            yield SelectionSession(session)

    c.database.session_context = session_context
    c.container = SimpleNamespace(
        database=c.database,
        frankfurt=object(),
        jpmorgan=None,
        morganstanley=None,
        vontobel=None,
        gettex=None,
        stuttgart=None,
        settings=SimpleNamespace(
            market_data=SimpleNamespace(
                frankfurt=SimpleNamespace(readiness_reason="CONFIGURED_NOT_PROBED"),
                stuttgart_delayed=SimpleNamespace(),
            )
        ),
    )
    return c


async def decide(c, *, retry=False, allowed=(P.FRANKFURT_QUOTES,), **kwargs):
    async with c.database.session_context() as session:
        selector = Selector(Repository(session), allowed)
        operation = selector.reconcile if retry else selector.select_once
        result = await operation(
            workspace_id=c.workspace,
            position_id=c.position,
            warrant_id=c.warrant,
            selected_at=NOW + timedelta(seconds=int(retry)),
            **kwargs,
        )
        await session.commit()
        return result


def history(c):
    with Session(c.database.engine) as session:
        return list(session.scalars(select(Selection).order_by(Selection.selected_at)))


def issuer_route(c, provider=P.JPMORGAN):
    isin = "DE000JE7KTY8" if provider is P.JPMORGAN else "DE000MJ3QFV9"
    with Session(c.database.engine) as session:
        warrant = session.get(WarrantModel, c.warrant)
        warrant.isin, warrant.wkn = isin, isin[5:11]
        mapping = session.get(Mapping, c.mapping)
        mapping.provider, mapping.provider_symbol = provider, isin
        mapping.provider_exchange_code = "ISSUER"
        session.commit()


@pytest.mark.asyncio
async def test_missing_route_becomes_selected_once_after_verification(selection_context):
    c = selection_context
    with Session(c.database.engine) as session:
        session.get(Mapping, c.mapping).validated_at = None
        session.commit()
    first = await decide(c, expected_currency="EUR")
    assert first.selection_status == "NO_VERIFIED_QUOTE_SOURCE"
    assert not (await decide(c, retry=True)).changed
    with Session(c.database.engine) as session:
        session.get(Mapping, c.mapping).validated_at = NOW
        session.commit()
    result = await reconcile_warrant_positions(c.container, c.workspace, c.warrant)
    assert result["decisions_changed"] == 1
    assert result["statuses"] == {"SELECTED": 1}
    assert (await reconcile_warrant_positions(c.container, c.workspace, c.warrant))[
        "decisions_changed"
    ] == 0
    rows = history(c)
    assert len(rows) == 2 and rows[0].superseded_at is not None
    assert rows[1].superseded_at is None
    assert rows[1].evidence["previous_selection_id"] == str(first.id)
    assert rows[1].evidence["expected_currency"] == "EUR"
    with Session(c.database.engine) as session:
        position = session.get(PositionModel, c.position)
        assert position.open_quantity == 10 and position.cost_basis == 10


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", [P.JPMORGAN, P.MORGAN_STANLEY])
async def test_purchase_selection_passes_real_issuer_rule_validation(selection_context, provider):
    from tests.unit.backend.features.position_monitoring.test_issuer_indicative_rules import (
        check,
        valuation,
    )

    c = selection_context
    issuer_route(c, provider)
    row = await decide(c, allowed=(provider,))
    value = valuation(provider.value, source_selection_policy_version=row.policy_version)
    result = await check(value)
    assert result.status == "INDICATIVE"
    assert result.observation is not None
    assert value.quote_observed_at is None and value.execution_usable is False
    assert row.selection_reason == f"VERIFIED_{provider.value}_ISSUER_INDICATION"


@pytest.mark.asyncio
async def test_generic_issuer_policy_is_repaired_without_changing_route(selection_context):
    c = selection_context
    issuer_route(c)
    first = await decide(c, allowed=(P.JPMORGAN,))
    with Session(c.database.engine) as session:
        old = session.get(Selection, first.id)
        old.policy_version, old.selection_reason = GENERIC_POLICY, "UNIQUE_VERIFIED_ROUTE"
        session.commit()
    result = await decide(c, retry=True, allowed=(P.JPMORGAN,))
    assert result.changed and result.reason == "ISSUER_POLICY_RECONCILED"
    assert result.selection.identity_key == first.identity_key
    assert result.selection.warrant_provider_mapping_id == first.warrant_provider_mapping_id
    assert result.selection.mapping_version == first.mapping_version
    assert not (await decide(c, retry=True, allowed=(P.JPMORGAN,))).changed
    assert len(history(c)) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["disabled", "version", "identity", "manual", "constraints"])
async def test_selected_issuer_policy_repair_requires_exact_old_identity(selection_context, mode):
    c = selection_context
    issuer_route(c)
    first = await decide(c, allowed=(P.JPMORGAN,))
    with Session(c.database.engine) as session:
        old = session.get(Selection, first.id)
        old.policy_version, old.selection_reason = GENERIC_POLICY, "UNIQUE_VERIFIED_ROUTE"
        mapping = session.get(Mapping, c.mapping)
        if mode == "disabled":
            mapping.status = MappingStatus.DISABLED
        elif mode == "version":
            mapping.version += 1
        elif mode == "identity":
            old.identity_key = "x" * 64
        elif mode == "manual":
            old.policy_version = "MANUAL_POLICY"
        else:
            old.evidence = {**old.evidence, "expected_currency": "USD"}
        session.commit()
    assert not (await decide(c, retry=True, allowed=(P.JPMORGAN,))).changed
    assert len(history(c)) == 1


@pytest.mark.asyncio
async def test_no_fallback_or_source_switch_for_an_existing_selection(selection_context):
    c = selection_context
    first = await decide(c)
    issuer_route(c)
    result = await decide(c, retry=True, allowed=(P.JPMORGAN,))
    assert not result.changed and result.selection.id == first.id
    assert result.selection.provider == P.FRANKFURT_QUOTES.value


@pytest.mark.asyncio
async def test_ambiguity_is_preserved_until_only_one_eligible_route_remains(selection_context):
    c = selection_context
    issuer_route(c)
    with Session(c.database.engine) as session:
        session.add(
            Mapping(
                id=uuid4(),
                workspace_id=c.workspace,
                warrant_listing_id=c.request.warrant_listing_id,
                provider=P.FRANKFURT_QUOTES,
                provider_symbol="DE000JE7KTY8",
                provider_exchange_code="XSC",
                status=MappingStatus.ACTIVE,
                validated_at=NOW,
                version=1,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.commit()
    allowed = (P.JPMORGAN, P.FRANKFURT_QUOTES)
    assert (await decide(c, allowed=allowed)).selection_status == "AMBIGUOUS_SOURCE"
    assert not (await decide(c, retry=True, allowed=allowed)).changed
    result = await decide(c, retry=True, allowed=(P.JPMORGAN,))
    assert result.changed and result.selection.provider == "JPMORGAN"


@pytest.mark.asyncio
async def test_currency_constraint_survives_retries(selection_context):
    c = selection_context
    first = await decide(c, expected_currency="USD")
    result = await decide(c, retry=True)
    assert not result.changed and result.selection.id == first.id
    assert result.selection.selection_reason == "NO_VERIFIED_QUOTE_SOURCE_FOR_CURRENCY"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["closed", "cancelled", "workspace", "issuer_inactive"])
async def test_ineligible_positions_or_routes_are_not_selected(selection_context, mode):
    c = selection_context
    with Session(c.database.engine) as session:
        if mode == "closed":
            position = session.get(PositionModel, c.position)
            position.open_quantity, position.cost_basis, position.closed_at = 0, 0, NOW
        elif mode == "cancelled":
            trade = session.get(TradeModel, c.trade)
            trade.cancelled_at, trade.cancelled_by, trade.cancellation_reason = NOW, uuid4(), "Test"
        elif mode == "workspace":
            c.workspace = uuid4()
        else:
            issuer = session.get(WarrantModel, c.warrant).issuer_id
            session.get(IssuerModel, issuer).is_active = False
        session.commit()
    result = await decide(c, retry=True)
    if mode == "issuer_inactive":
        assert result.selection.selection_status == "NO_VERIFIED_QUOTE_SOURCE"
    else:
        assert result.selection is None and not result.changed
        assert not history(c)


@pytest.mark.asyncio
async def test_failed_successor_insert_rolls_back_superseding(selection_context, monkeypatch):
    c = selection_context
    first = await decide(c, allowed=())
    monkeypatch.setattr(Repository, "add", AsyncMock(side_effect=RuntimeError("TEST_FAILURE")))
    with pytest.raises(RuntimeError, match="TEST_FAILURE"):
        await decide(c, retry=True)
    rows = history(c)
    assert len(rows) == 1 and rows[0].id == first.id and rows[0].superseded_at is None


@pytest.mark.asyncio
async def test_refresh_reconciles_before_fetch_and_reports_selection(monkeypatch):
    from tests.unit.backend.features.market_data.test_refresh import runtime, session_context

    value = runtime(auto_configure=False)
    value.settings.auto_select_position_sources = True
    item = RefreshInstrument(uuid4(), "Test", None)
    result = {"positions_checked": 1, "decisions_changed": 1, "statuses": {"SELECTED": 1}}
    reconcile = AsyncMock(return_value=result)
    monkeypatch.setattr(refresh_module, "reconcile_warrant_positions", reconcile)
    session = SimpleNamespace(scalars=AsyncMock(side_effect=[[], []]))
    value.container = replace(
        value.container,
        database=SimpleNamespace(
            session_context=lambda: session_context(session),
        ),
    )
    response = await value._warrant(item)
    reconcile.assert_awaited_once_with(value.container, value.workspace_id, item.id)
    assert response["source_selection"] == result
    assert response["attempted_route_count"] == 0
