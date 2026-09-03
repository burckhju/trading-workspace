from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.database import DatabaseManager
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.notification.domain.models import DeliveryStatus
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.persistence.repositories import SqlAlchemyNotificationRepository
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.delivery import NotificationDeliveryAdapter
from app.features.notification.service.durable_delivery import DurableNotificationDeliveryService
from app.features.position_monitoring.service.cycle import (
    CreatedPositionAlert,
    MonitoringCycleResult,
    PositionMonitoringCycleService,
)
from app.features.position_monitoring.service.processor import SqlAlchemyMonitoringRuleProcessor
from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader


@dataclass(frozen=True, slots=True)
class PositionMonitoringRuntimeResult:
    cycle: MonitoringCycleResult
    notifications_created: int
    notifications_delivered: int
    notification_failures: int


class PositionMonitoringRuntimeService:
    """Compose monitoring and optional notification delivery across durable boundaries."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        market_data: LatestCompletedDailyPriceProvider,
        delivery_adapter: NotificationDeliveryAdapter | None,
        max_completed_price_age_days: int = 4,
        delivery_max_attempts: int = 3,
        delivery_recovery_timeout: timedelta = timedelta(minutes=5),
    ) -> None:
        self._database = database
        self._market_data = market_data
        self._delivery_adapter = delivery_adapter
        self._max_completed_price_age_days = max_completed_price_age_days
        self._delivery_max_attempts = delivery_max_attempts
        self._delivery_recovery_timeout = delivery_recovery_timeout

    async def run(self) -> PositionMonitoringRuntimeResult:
        cycle_result = await self._run_monitoring_cycle()
        if self._delivery_adapter is None:
            return PositionMonitoringRuntimeResult(cycle_result, 0, 0, 0)

        created = delivered = failures = 0
        delivery = DurableNotificationDeliveryService(
            store=SqlAlchemyDurableNotificationDeliveryStore(self._database),
            adapter=self._delivery_adapter,
            new_id=uuid4,
            now=lambda: datetime.now(UTC),
            max_attempts=self._delivery_max_attempts,
            in_progress_timeout=self._delivery_recovery_timeout,
        )
        for created_alert in cycle_result.created_alerts:
            try:
                notification_id = await self._create_notification(created_alert)
                created += 1
                result = await delivery.deliver(notification_id)
                if result.status is DeliveryStatus.DELIVERED:
                    delivered += 1
                else:
                    failures += 1
            except Exception:
                failures += 1

        return PositionMonitoringRuntimeResult(
            cycle=cycle_result,
            notifications_created=created,
            notifications_delivered=delivered,
            notification_failures=failures,
        )

    async def _run_monitoring_cycle(self) -> MonitoringCycleResult:
        async with self._database.session_context() as session:
            service = PositionMonitoringCycleService(
                subjects=SqlAlchemyMonitoringSubjectReader(session),
                market_data=self._market_data,
                processor=SqlAlchemyMonitoringRuleProcessor(session),
                new_id=uuid4,
                max_completed_price_age_days=self._max_completed_price_age_days,
            )
            return await service.run()

    async def _create_notification(self, created_alert: CreatedPositionAlert) -> UUID:
        async with self._database.session_context() as session:
            service = AlertNotificationService(
                notifications=SqlAlchemyNotificationRepository(session),
                new_id=uuid4,
                now=lambda: datetime.now(UTC),
            )
            notification = await service.create_telegram(
                alert=created_alert.alert,
                symbol=created_alert.symbol,
            )
            await session.commit()
            return notification.id
