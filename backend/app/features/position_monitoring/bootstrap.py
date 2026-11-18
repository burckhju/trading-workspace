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
from app.features.position_monitoring.service.hebeltrader_loss_runtime import HebeltraderLossRuntime
from app.features.position_monitoring.service.indicative_entry_runtime import IndicativeEntryRuntime
from app.features.position_monitoring.service.product_deadline_review_runtime import (
    ProductDeadlineReviewRuntime,
)
from app.features.position_monitoring.service.risk_runtime import RiskRuntimeService
from app.features.position_monitoring.service.rule_prices import ProductValuationReader
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeService
from app.features.product.service.review_acquisition import ProductReviewReadiness


def build_position_monitoring_runtime(
    *,
    settings: Settings,
    database: DatabaseManager,
    market_data: LatestCompletedDailyPriceProvider | None,
    products: ProductValuationReader | None = None,
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
        risk=RiskRuntimeService(database),
        hebeltrader_loss=HebeltraderLossRuntime(
            database,
            scope=monitoring.hebeltrader_scope,
            products=products,
            notifications_enabled=delivery_adapter is not None,
        ),
        indicative_entry=IndicativeEntryRuntime(
            database,
            scope=monitoring.review_scope,
            products=products,
            readiness=ProductReviewReadiness(database),
            notifications_enabled=(
                monitoring.review_notifications_enabled and delivery_adapter is not None
            ),
        ),
        product_deadline=ProductDeadlineReviewRuntime(
            database,
            scope=monitoring.review_scope,
            notifications_enabled=(
                monitoring.review_scope == "INDICATIVE_ENTRY_V2"
                and monitoring.review_notifications_enabled
                and delivery_adapter is not None
            ),
        ),
        market_data=market_data,
        review_notifications_enabled=(
            monitoring.review_notifications_enabled and monitoring.review_scope != "DISABLED"
        ),
        deadline_notifications_enabled=(
            monitoring.review_notifications_enabled
            and monitoring.review_scope == "INDICATIVE_ENTRY_V2"
        ),
        products=products,
        parallel_positions=monitoring.parallel_positions,
        delivery_adapter=delivery_adapter,
        max_completed_price_age_days=monitoring.max_completed_price_age_days,
        delivery_max_attempts=telegram.max_attempts,
        delivery_recovery_timeout=timedelta(
            seconds=monitoring.delivery_recovery_timeout_seconds,
        ),
    )
