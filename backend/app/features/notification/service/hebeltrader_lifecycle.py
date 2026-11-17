"""Terminal B04 outbox decisions within the caller's existing trade transaction."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.domain.models import AlertType
from app.features.alert.persistence.models import AlertModel
from app.features.notification.domain.models import (
    DeliveryResult,
    DeliveryStatus,
    NotificationStatus,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)

_REASONS = {
    "B04_POSITION_CLOSED": (
        "Effektive Ausführungen belegen Vollverkauf; B04-Zustellung unterdrückt."
    ),
    "B04_ALERT_RESOLVED": (
        "B04-Verlustbedingung wurde beendet; ausstehende Zustellung unterdrückt."
    ),
    "B04_ALERT_INVALIDATED": (
        "B04-Verlusthinweis wurde durch neue Bewertung ungültig; Zustellung unterdrückt."
    ),
    "B04_TRADE_CANCELLED": "Trade wurde storniert; ausstehende B04-Zustellung unterdrückt.",
    "B04_TRADE_MISSING": "Wirtschaftlicher Trade fehlt; B04-Zustellung unterdrückt.",
}
B04_SUPPRESSION_CODES = tuple(_REASONS)


async def suppress_b04_notification(
    session: AsyncSession,
    *,
    notification: NotificationModel,
    now: datetime,
    reason: str,
    attempt_id: UUID | None = None,
) -> DeliveryResult:
    """Record one suppressed preparation, never an actual external send.

    Caller has locked the B04 trade and pending notification and commits the
    decision together with its business change. Earlier attempts are retained;
    an already in-flight external request cannot be recalled by this decision.
    """
    if notification.status != NotificationStatus.PENDING.value:
        raise ValueError("B04 suppression requires a locked pending notification")
    if reason not in _REASONS:
        raise ValueError("Unsupported B04 suppression reason")
    current = await session.scalar(
        select(func.max(NotificationDeliveryAttemptModel.attempt_number)).where(
            NotificationDeliveryAttemptModel.notification_id == notification.id
        )
    )
    result = DeliveryResult(
        status=DeliveryStatus.FAILED,
        retryable=False,
        error_code=reason,
        error_message=_REASONS[reason],
    )
    session.add(
        NotificationDeliveryAttemptModel(
            id=attempt_id or uuid4(),
            notification_id=notification.id,
            attempt_number=int(current or 0) + 1,
            status=DeliveryStatus.FAILED.value,
            attempted_at=now,
            completed_at=now,
            retryable=False,
            provider_message_id=None,
            error_code=result.error_code,
            error_message=result.error_message,
        )
    )
    notification.status = NotificationStatus.FAILED.value
    return result


async def suppress_pending_b04_notifications(
    session: AsyncSession, *, alert_id: UUID, now: datetime, reason: str
) -> int:
    """Suppress only pending B04 notifications; caller holds the trade lock.

    No commit, notification deletion, alert rewrite or provider invocation is
    performed. Repetition after the first suppression changes no history.
    """
    await session.flush()
    alert_type = await session.scalar(
        select(AlertModel.alert_type).where(AlertModel.id == alert_id)
    )
    if alert_type != AlertType.HEBELTRADER_B04_LOSS.value:
        raise ValueError("B04 notification lifecycle requires a B04 alert")
    if reason not in _REASONS:
        raise ValueError("Unsupported B04 suppression reason")
    pending = tuple(
        await session.scalars(
            select(NotificationModel)
            .where(
                NotificationModel.alert_id == alert_id,
                NotificationModel.status == NotificationStatus.PENDING.value,
            )
            .order_by(NotificationModel.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    for notification in pending:
        await suppress_b04_notification(session, notification=notification, now=now, reason=reason)
    return len(pending)
