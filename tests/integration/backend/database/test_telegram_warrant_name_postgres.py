"""Database identity -> monitoring -> durable outbox -> mocked Telegram transport."""

import json
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.backend.database import test_bulk_rule_confirmation_postgres as seed_data

from app.features.notification.domain.models import DeliveryStatus
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.persistence.models import NotificationModel
from app.features.notification.providers.telegram import (
    TelegramDeliveryAdapter,
    TelegramDeliveryConfig,
)
from app.features.notification.service.durable_delivery import DurableNotificationDeliveryService
from app.features.position_monitoring.service.cycle import PositionMonitoringCycleService
from app.features.position_monitoring.service.processor import SqlAlchemyMonitoringRuleProcessor
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
)
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeService
from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
from app.features.product.persistence.models import WarrantModel
from app.tools.confirm_warrant_rules import apply_plan

depot = seed_data.depot


@pytest.mark.parametrize("observed,kind", [(".10", "STOP_REACHED"), ("3.00", "TARGET_REACHED")])
async def test_warrant_names_survive_persistence_retry_and_do_not_mix_products(
    depot, observed, kind
):
    # The imported fixture is restricted to a disposable PostgreSQL test database and rolls back.
    plan = await seed_data.make_plan(depot)
    await apply_plan(
        depot.connection,
        plan=plan,
        workspace_id=depot.workspace,
        currency="EUR",
        actor=depot.actor,
    )

    @asynccontextmanager
    async def session_context():
        async with AsyncSession(
            bind=depot.connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session

    database = SimpleNamespace(session_context=session_context)
    async with session_context() as session:
        reader = SqlAlchemyMonitoringSubjectReader(
            session, for_rule_evaluation=True, workspace_id=depot.workspace
        )
        subjects = [r.subject for r in await reader.list_resolutions()]
        assert len(subjects) == 2  # Neither the foreign workspace nor the closed position.
        for index, subject in enumerate(subjects):
            await session.execute(
                update(WarrantModel)
                .where(WarrantModel.id == subject.warrant_id)
                .values(
                    underlying_id=subjects[0].underlying_id,
                    display_name=f"SYNTHETIC Bank <A&B> Call {index}",
                    isin=f"DE000SYN00{index}0",
                    wkn=f"SYN00{index}",
                )
            )
        await session.commit()
        subjects = [r.subject for r in await reader.list_resolutions()]
        assert len({s.underlying_id for s in subjects}) == 1
        values = {
            s.trade_id: ProductPositionValuation(
                s.trade_id,
                s.position_id,
                ProductValuationStatus.AVAILABLE,
                "SYNTHETIC",
                quote_listing_id=uuid4(),
                isin=s.warrant_isin,
                currency="EUR",
                monitoring_usable=True,
                reference_price=Decimal(observed),
                reference_price_type="BID",
                quote_observed_at=datetime.now(UTC),
                selected_source="SYNTHETIC",
                provider_identity=s.warrant_isin,
            )
            for s in subjects
        }
        products = AsyncMock()
        products.for_trade.side_effect = lambda trade_id: values[trade_id]
        cycle = PositionMonitoringCycleService(
            subjects=reader,
            market_data=None,
            products=products,
            processor=SqlAlchemyMonitoringRuleProcessor(session),
            new_id=uuid4,
        )
        result = await cycle.run()
        assert result.alerts_created == 2
        assert all(c.alert.alert_type.value == kind for c in result.created_alerts)
        assert (await cycle.run()).alerts_created == 0

    runtime = PositionMonitoringRuntimeService(
        database=database,
        market_data=None,
        delivery_adapter=None,
    )
    for created in result.created_alerts:
        await runtime._create_notification(created)
    async with session_context() as session:
        notifications = list(
            await session.scalars(
                select(NotificationModel).where(
                    NotificationModel.alert_id.in_([c.alert.id for c in result.created_alerts])
                )
            )
        )
        assert len(notifications) == 2
        by_alert = {n.alert_id: n for n in notifications}
        for subject, created in zip(subjects, result.created_alerts, strict=True):
            body = by_alert[created.alert.id].body
            assert f"Optionsschein: {subject.warrant_name}\n" in body
            assert f"WKN: {subject.warrant_wkn} | ISIN: {subject.warrant_isin}" in body
            assert "Kursbezug: WARRANT" in body and "Keine Orderfreigabe." in body
            other = next(s for s in subjects if s.trade_id != subject.trade_id)
            assert other.warrant_name not in body

    sent = []

    async def handler(request):
        payload = json.loads(request.content)
        sent.append(payload["text"])
        assert "parse_mode" not in payload
        if len(sent) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": len(sent)}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = TelegramDeliveryAdapter(
            config=TelegramDeliveryConfig(bot_token=SecretStr("synthetic-token"), chat_id="test"),
            client=client,
        )
        delivery = DurableNotificationDeliveryService(
            store=SqlAlchemyDurableNotificationDeliveryStore(database),
            adapter=adapter,
            new_id=uuid4,
            now=lambda: datetime.now(UTC),
        )
        first = result.created_alerts[0]
        notification_id = by_alert[first.alert.id].id
        assert (await delivery.deliver(notification_id)).status is DeliveryStatus.FAILED
        await runtime._create_notification(replace(first, warrant_name="SYNTHETIC Renamed"))
        assert (await delivery.deliver(notification_id)).status is DeliveryStatus.DELIVERED
        assert sent[0] == sent[1] == by_alert[first.alert.id].body
        assert "Renamed" not in sent[1]
        assert (await delivery.deliver(notification_id)).status is DeliveryStatus.DELIVERED
        assert len(sent) == 2  # Delivered outbox item is not sent again.
        other = result.created_alerts[1]
        assert (
            await delivery.deliver(by_alert[other.alert.id].id)
        ).status is DeliveryStatus.DELIVERED
        assert len(sent) == 3 and sent[-1] == by_alert[other.alert.id].body
