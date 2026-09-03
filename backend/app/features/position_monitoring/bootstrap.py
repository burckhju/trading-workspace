from __future__ import annotations

from datetime import timedelta

from app.core.config import Settings
from app.database import DatabaseManager
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.notification.providers.telegram import (
    TelegramDeliveryAdapter,
    TelegramDeliveryConfig,
)
from app.features.notification.service.delivery import NotificationDeliveryAdapter
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeService


def build_position_monitoring_runtime(
    *,
    settings: Settings,
    database: DatabaseManager,
    market_data: LatestCompletedDailyPriceProvider,
) -> PositionMonitoringRuntimeService:
    """Build the runtime without leaking provider details into monitoring services."""

    monitoring = settings.position_monitoring
    telegram = settings.notification.telegram
    delivery_adapter: NotificationDeliveryAdapter | None = None
    if telegram.enabled:
        if telegram.bot_token is None or telegram.chat_id is None:
            raise ValueError("Telegram is enabled but bot_token or chat_id is missing")
        delivery_adapter = TelegramDeliveryAdapter(
            config=TelegramDeliveryConfig(
                bot_token=telegram.bot_token,
                chat_id=telegram.chat_id,
                base_url=telegram.base_url,
                timeout_seconds=telegram.timeout_seconds,
            )
        )

    return PositionMonitoringRuntimeService(
        database=database,
        market_data=market_data,
        delivery_adapter=delivery_adapter,
        max_completed_price_age_days=monitoring.max_completed_price_age_days,
        delivery_max_attempts=telegram.max_attempts,
        delivery_recovery_timeout=timedelta(
            seconds=monitoring.delivery_recovery_timeout_seconds,
        ),
    )
