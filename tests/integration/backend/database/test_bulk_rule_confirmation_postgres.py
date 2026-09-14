"""Bulk confirmation uses real FT-010 writes with atomicity and tenant isolation."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_data_instrument_workspace_postgres import (
    _test_database_url,
)

from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
from app.features.trade_position.persistence.models import (
    PositionModel,
    TradeManagementEventModel,
    TradeModel,
)
from app.tools.confirm_warrant_rules import (
    ConfirmationPlan,
    TradePositionService,
    apply_plan,
    preview,
)


@pytest.fixture
async def depot():
    engine = create_async_engine(_test_database_url())
    now = datetime.now(UTC)
    workspace, foreign_workspace, actor = uuid4(), uuid4(), uuid4()
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                for owner in (workspace, foreign_workspace):
                    await connection.execute(
                        text("INSERT INTO workspaces(id,name,created_at) VALUES (:id,:name,:now)"),
                        {"id": owner, "name": str(owner), "now": now},
                    )
                original_ids = []
                for index, owner in enumerate((workspace, workspace, foreign_workspace, workspace)):
                    underlying, issuer, warrant, trade, position = (uuid4() for _ in range(5))
                    await connection.execute(
                        text(
                            "INSERT INTO issuers(id,legal_name,display_name,is_active,version,"
                            "created_at,updated_at) VALUES (:id,:name,:name,true,1,:now,:now)"
                        ),
                        {"id": issuer, "name": str(issuer), "now": now},
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO underlyings(id,workspace_id,type,name,lifecycle_status,"
                            "quality_status,version,created_at,updated_at,data_origin) VALUES "
                            "(:id,:workspace,'STOCK','Bulk test','ACTIVE','VERIFIED',1,:now,"
                            ":now,'MANUAL')"
                        ),
                        {"id": underlying, "workspace": owner, "now": now},
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO warrants(id,workspace_id,issuer_id,underlying_id,"
                            "product_family,display_name,isin,lifecycle_status,version,created_at,"
                            "updated_at) VALUES (:id,:workspace,:issuer,:underlying,'WARRANT',"
                            "'Bulk warrant',:isin,'ACTIVE',1,:now,:now)"
                        ),
                        {
                            "id": warrant,
                            "workspace": owner,
                            "issuer": issuer,
                            "underlying": underlying,
                            "isin": (
                                "DE000VH2LU21",
                                "DE000VH4VNA6",
                                "DE000HM4EB12",
                                "DE000DY982R1",
                            )[index],
                            "now": now,
                        },
                    )
                    await connection.execute(
                        insert(TradeModel).values(
                            id=trade,
                            workspace_id=owner,
                            product_id=warrant,
                            origin="EXTERNAL",
                            created_at=now,
                            created_by=actor,
                        )
                    )
                    await connection.execute(
                        insert(PositionModel).values(
                            id=position,
                            trade_id=trade,
                            product_id=warrant,
                            open_quantity=0 if index == 3 else 2000,
                            cost_basis=0 if index == 3 else 1020,
                            average_entry_price=Decimal(".51"),
                            opened_at=now,
                            last_execution_at=now,
                            realized_gross_pnl=0,
                            closed_at=now if index == 3 else None,
                        )
                    )
                    for kind, price in (("STOP_CHANGED", ".16"), ("TARGET_CHANGED", "2.50")):
                        event_id = uuid4()
                        original_ids.append(event_id)
                        await connection.execute(
                            insert(TradeManagementEventModel).values(
                                id=event_id,
                                trade_id=trade,
                                event_type=kind,
                                effective_at=now,
                                recorded_at=now,
                                recorded_by=actor,
                                numeric_value=Decimal(price),
                            )
                        )
                yield SimpleNamespace(
                    connection=connection,
                    workspace=workspace,
                    actor=actor,
                    original_ids=original_ids,
                )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def make_plan(depot):
    async with AsyncSession(
        bind=depot.connection, join_transaction_mode="create_savepoint"
    ) as session:
        return await preview(
            session, workspace_id=depot.workspace, currency="EUR", expect_positions=2
        )


async def test_bulk_confirmation_keeps_prices_history_and_scope_and_is_idempotent(depot):
    plan = await make_plan(depot)
    assert len(plan.rules) == 4 and not any(r.already_confirmed for r in plan.rules)
    # Preview is transferable from stdout to the apply process without decimal conversion.
    plan = ConfirmationPlan.model_validate_json(plan.model_dump_json())
    result = await apply_plan(
        depot.connection,
        plan=plan,
        workspace_id=depot.workspace,
        currency="EUR",
        actor=depot.actor,
    )
    assert result["events_created"] == 4
    assert result["status"] == "APPLIED"
    async with AsyncSession(
        bind=depot.connection, join_transaction_mode="create_savepoint"
    ) as session:
        originals = (
            await session.scalars(
                select(TradeManagementEventModel).where(
                    TradeManagementEventModel.id.in_(depot.original_ids)
                )
            )
        ).all()
        assert len(originals) == 8
        assert all(e.price_binding is None and e.supersedes_event_id is None for e in originals)
        assert {e.numeric_value for e in originals} == {Decimal(".16"), Decimal("2.50")}
        reader = SqlAlchemyMonitoringSubjectReader(
            session, for_rule_evaluation=True, workspace_id=depot.workspace
        )
        subjects = [r.subject for r in await reader.list_resolutions()]
        assert len(subjects) == 2
        for subject in subjects:
            assert subject.mapping_id is None  # No stock mappings or quote access required.
            assert all(r.price_binding.instrument_id == subject.warrant_id for r in subject.rules)
            assert all(r.price_binding.currency == "EUR" for r in subject.rules)
            position = await session.get(PositionModel, subject.position_id)
            assert position.open_quantity == 2000 and position.cost_basis == Decimal("1020")
        new_ids = [UUID(row["event_id"]) for row in result["events"]]
        new_events = (
            await session.scalars(
                select(TradeManagementEventModel).where(TradeManagementEventModel.id.in_(new_ids))
            )
        ).all()
        assert len(new_events) == 4
        assert all(
            e.recorded_by == depot.actor and e.supersedes_event_id is None for e in new_events
        )
    again = await apply_plan(
        depot.connection,
        plan=plan,
        workspace_id=depot.workspace,
        currency="EUR",
        actor=depot.actor,
    )
    assert again["status"] == "ALREADY_CONFIRMED" and again["events_created"] == 0
    assert again["rules_already_confirmed"] == 4


async def test_failure_after_first_ft010_commit_rolls_back_entire_batch(depot, monkeypatch):
    plan = await make_plan(depot)
    original = TradePositionService.record_management_event
    calls = 0

    async def fail_second(self, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated second write failure")
        return await original(self, **kwargs)

    monkeypatch.setattr(TradePositionService, "record_management_event", fail_second)
    with pytest.raises(RuntimeError, match="second write failure"):
        # Production owns engine.begin(); this nested transaction keeps test seed data.
        async with depot.connection.begin_nested():
            await apply_plan(
                depot.connection,
                plan=plan,
                workspace_id=depot.workspace,
                currency="EUR",
                actor=depot.actor,
            )
    assert calls == 2
    after = await make_plan(depot)
    assert after == plan and not any(r.already_confirmed for r in after.rules)
    rows = (
        await depot.connection.execute(
            select(TradeManagementEventModel.id)
            .join(TradeModel, TradeModel.id == TradeManagementEventModel.trade_id)
            .where(TradeModel.workspace_id == depot.workspace)
        )
    ).all()
    assert len(rows) == 6  # Only original events, including the closed position.


async def test_changed_threshold_aborts_before_any_write(depot):
    plan = await make_plan(depot)
    corrupted = plan.model_copy(
        update={
            "rules": (
                plan.rules[0].model_copy(update={"threshold": Decimal("99")}),
                *plan.rules[1:],
            )
        }
    )
    with pytest.raises(ValueError, match="PLAN_CHANGED"):
        async with depot.connection.begin_nested():
            await apply_plan(
                depot.connection,
                plan=corrupted,
                workspace_id=depot.workspace,
                currency="EUR",
                actor=depot.actor,
            )
    assert await make_plan(depot) == plan
