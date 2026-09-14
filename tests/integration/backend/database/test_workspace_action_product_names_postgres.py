"""Real read-model joins and batched identity reads; no provider or notification delivery."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import event, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.backend.database import test_bulk_rule_confirmation_postgres as seed_data

from app.features.alert.persistence.models import AlertModel
from app.features.notification.persistence.models import NotificationModel
from app.features.operational_workspace.api.dtos import OperationalActionResponse
from app.features.operational_workspace.service.read_model import OperationalWorkspaceReadModel
from app.features.product.persistence.models import WarrantModel
from app.features.product.service.application import WarrantService
from app.features.trade_position.persistence.models import PositionModel, TradeModel

depot = seed_data.depot


async def test_actions_keep_exact_names_for_alerts_delivery_open_and_closed_trades(depot):
    now = datetime.now(UTC)
    async with AsyncSession(
        bind=depot.connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        rows = (
            await session.execute(
                select(TradeModel, PositionModel, WarrantModel)
                .join(PositionModel, PositionModel.trade_id == TradeModel.id)
                .join(WarrantModel, WarrantModel.id == TradeModel.product_id)
                .order_by(TradeModel.id)
            )
        ).all()
        # Restrict fixture operations to this transaction's three local products + one foreign.
        rows = [r for r in rows if r[0].created_by == depot.actor]
        local = [r for r in rows if r[0].workspace_id == depot.workspace]
        assert len(local) == 3
        expected = {}
        for index, (trade, position, warrant) in enumerate(rows):
            name = f"SYNTHETIC Optionsschein {index} <A&B>"
            await session.execute(
                update(WarrantModel)
                .where(WarrantModel.id == warrant.id)
                .values(
                    display_name=name,
                    isin=f"DE000SYN00{index}0",
                    wkn=f"SYN00{index}",
                    underlying_id=(
                        local[0][2].underlying_id
                        if trade.workspace_id == depot.workspace
                        else warrant.underlying_id
                    ),
                )
            )
            alert_id = uuid4()
            await session.execute(
                insert(AlertModel).values(
                    id=alert_id,
                    position_id=position.id,
                    trade_id=trade.id,
                    alert_type="STOP_REACHED",
                    severity="WARNING",
                    rule_key="SYNTHETIC",
                    reason="SYNTHETIC Stop reached",
                    observed_value=1,
                    threshold_value=2,
                    market_data_observed_at=now,
                    detected_at=now,
                    status="OPEN",
                )
            )
            await session.execute(
                insert(NotificationModel).values(
                    id=uuid4(),
                    alert_id=alert_id,
                    channel="TELEGRAM",
                    destination_key="synthetic",
                    body="SYNTHETIC immutable historical body",
                    created_at=now,
                    status="FAILED",
                )
            )
            if trade.workspace_id == depot.workspace:
                expected[warrant.id] = (name, f"DE000SYN00{index}0", f"SYN00{index}")
        await session.flush()
        statements = []

        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            statements.append(statement)

        event.listen(depot.connection.sync_connection, "before_cursor_execute", capture)
        try:
            actions = await OperationalWorkspaceReadModel(session).list_actions(
                workspace_id=depot.workspace
            )
        finally:
            event.remove(depot.connection.sync_connection, "before_cursor_execute", capture)
        assert (
            len(actions) == 9
        )  # Three alerts + three terminal failures + two open + one post-trade.
        assert {a.action_type for a in actions} == {
            "POSITION_ALERT",
            "NOTIFICATION_DELIVERY_FAILURE",
            "OPEN_POSITION_MANAGEMENT",
            "POST_TRADE_OBSERVATION",
        }
        for item in actions:
            assert (item.product_name, item.product_isin, item.product_wkn) == expected[
                item.product_id
            ]
            assert (
                OperationalActionResponse(
                    **{k: getattr(item, k) for k in item.__dataclass_fields__}
                ).product_name
                == item.product_name
            )
        assert sum("FROM warrants" in s for s in statements) == 1
        assert all(s.lstrip().upper().startswith("SELECT") for s in statements)
        # A stale / cross-workspace foreign key cannot expose another workspace's labels.
        foreign = next(r for r in rows if r[0].workspace_id != depot.workspace)
        identities = await WarrantService(session).read_identities(
            workspace_id=depot.workspace, warrant_ids={foreign[2].id, *expected}
        )
        assert set(identities) == set(expected)
        assert all(
            n.body == "SYNTHETIC immutable historical body"
            for n in await session.scalars(
                select(NotificationModel)
                .join(AlertModel, AlertModel.id == NotificationModel.alert_id)
                .where(AlertModel.trade_id.in_([r[0].id for r in rows]))
            )
        )
        # Cancellation exclusions still apply in every action projection.
        cancelled = local[0][0]
        await session.execute(
            update(TradeModel)
            .where(TradeModel.id == cancelled.id)
            .values(
                cancelled_at=now, cancelled_by=depot.actor, cancellation_reason="SYNTHETIC test"
            )
        )
        later = await OperationalWorkspaceReadModel(session).list_actions(
            workspace_id=depot.workspace
        )
        assert all(a.product_id != cancelled.product_id for a in later)
