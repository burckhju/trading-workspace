from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DatabaseManager
from app.features.alert.domain.models import AlertType
from app.features.alert.persistence.models import AlertModel
from app.features.notification.domain.models import (
    DeliveryAttempt,
    DeliveryPreparation,
    DeliveryResult,
    DeliveryStatus,
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)
from app.features.notification.service.hebeltrader_lifecycle import (
    B04_SUPPRESSION_CODES,
    suppress_b04_notification,
)
from app.features.trade_position.domain.projector import PositionProjector
from app.features.trade_position.persistence.models import TradeModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
    SqlAlchemyTradeRepository,
)


class SqlAlchemyDurableNotificationDeliveryStore:
    """Persist preparation and completion in separate database transactions."""

    def __init__(self, database: DatabaseManager) -> None:
        self._database = database

    async def list_pending_notification_ids(self, *, limit: int) -> tuple[UUID, ...]:
        async with self._database.session_context() as session:
            values = await session.scalars(
                select(NotificationModel.id)
                .join(AlertModel, AlertModel.id == NotificationModel.alert_id)
                .join(TradeModel, TradeModel.id == AlertModel.trade_id)
                .where(
                    NotificationModel.status == NotificationStatus.PENDING.value,
                    or_(
                        # B04 needs a durable suppression reason even when its
                        # alert was resolved/invalidated or its trade cancelled.
                        AlertModel.alert_type == AlertType.HEBELTRADER_B04_LOSS.value,
                        and_(
                            AlertModel.status != "INVALIDATED",
                            TradeModel.cancelled_at.is_(None),
                        ),
                    ),
                )
                .order_by(NotificationModel.created_at, NotificationModel.id)
                .limit(limit)
            )
            return tuple(values.all())

    async def prepare(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        now: datetime,
        stale_before: datetime,
        max_attempts: int,
    ) -> DeliveryPreparation:
        async with self._database.session_context() as session:
            trade_id = await session.scalar(
                select(AlertModel.trade_id)
                .join(NotificationModel, NotificationModel.alert_id == AlertModel.id)
                .where(NotificationModel.id == notification_id)
            )
            trade_model = await session.scalar(
                select(TradeModel)
                .where(TradeModel.id == trade_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            model = await session.scalar(
                select(NotificationModel)
                .where(NotificationModel.id == notification_id)
                .with_for_update()
            )
            if model is None:
                raise LookupError("notification not found")
            notification = self._notification(model)
            alert_model = await session.scalar(
                select(AlertModel).where(AlertModel.id == model.alert_id).with_for_update()
            )
            alert_status = alert_model.status if alert_model is not None else None
            if (
                alert_model is not None
                and alert_model.alert_type == AlertType.HEBELTRADER_B04_LOSS.value
            ):
                terminal = await self._prepare_b04_terminal(
                    session,
                    model=model,
                    alert=alert_model,
                    trade=trade_model,
                    attempt_id=attempt_id,
                    now=now,
                )
                if terminal is not None:
                    return terminal
            if alert_status == "INVALIDATED":
                model.status = NotificationStatus.FAILED.value
                await session.commit()
                return DeliveryPreparation(
                    notification=self._notification(model),
                    terminal_result=DeliveryResult(
                        status=DeliveryStatus.FAILED,
                        retryable=False,
                        error_code="ALERT_INVALIDATED",
                        error_message="Rule price basis was unconfirmed; delivery suppressed",
                    ),
                )
            if trade_model is not None and trade_model.cancelled_at is not None:
                return DeliveryPreparation(
                    notification=notification,
                    terminal_result=DeliveryResult(
                        status=DeliveryStatus.FAILED,
                        retryable=False,
                        error_code="TRADE_CANCELLED",
                        error_message=(
                            "Trade was cancelled as an entry mistake; delivery " "suppressed"
                        ),
                    ),
                )
            if notification.status is NotificationStatus.DELIVERED:
                return DeliveryPreparation(
                    notification=notification,
                    terminal_result=DeliveryResult(
                        status=DeliveryStatus.DELIVERED,
                        retryable=False,
                    ),
                )

            await session.execute(
                update(NotificationDeliveryAttemptModel)
                .where(
                    NotificationDeliveryAttemptModel.notification_id == notification_id,
                    NotificationDeliveryAttemptModel.status == DeliveryStatus.IN_PROGRESS.value,
                    NotificationDeliveryAttemptModel.attempted_at <= stale_before,
                )
                .values(
                    status=DeliveryStatus.FAILED.value,
                    completed_at=now,
                    retryable=True,
                    error_code="PROCESS_INTERRUPTED",
                    error_message=(
                        "Previous delivery attempt did not complete before recovery timeout"
                    ),
                )
            )
            active_attempt = await session.scalar(
                select(NotificationDeliveryAttemptModel.id).where(
                    NotificationDeliveryAttemptModel.notification_id == notification_id,
                    NotificationDeliveryAttemptModel.status == DeliveryStatus.IN_PROGRESS.value,
                )
            )
            if active_attempt is not None:
                await session.commit()
                return DeliveryPreparation(
                    notification=notification,
                    terminal_result=DeliveryResult(
                        status=DeliveryStatus.FAILED,
                        retryable=True,
                        error_code="DELIVERY_ALREADY_IN_PROGRESS",
                        error_message="notification delivery is already in progress",
                    ),
                )

            current = await session.scalar(
                select(func.max(NotificationDeliveryAttemptModel.attempt_number)).where(
                    NotificationDeliveryAttemptModel.notification_id == notification_id
                )
            )
            attempt_number = int(current or 0) + 1
            if attempt_number > max_attempts:
                model.status = NotificationStatus.FAILED.value
                await session.commit()
                return DeliveryPreparation(
                    notification=self._notification(model),
                    terminal_result=DeliveryResult(
                        status=DeliveryStatus.FAILED,
                        retryable=False,
                        error_code="MAX_ATTEMPTS_EXCEEDED",
                        error_message="notification delivery attempt limit exceeded",
                    ),
                )

            attempt = DeliveryAttempt(
                id=attempt_id,
                notification_id=notification_id,
                attempt_number=attempt_number,
                status=DeliveryStatus.IN_PROGRESS,
                attempted_at=now,
                completed_at=None,
                retryable=True,
            )
            session.add(
                NotificationDeliveryAttemptModel(
                    id=attempt.id,
                    notification_id=attempt.notification_id,
                    attempt_number=attempt.attempt_number,
                    status=attempt.status.value,
                    attempted_at=attempt.attempted_at,
                    completed_at=None,
                    retryable=True,
                    provider_message_id=None,
                    error_code=None,
                    error_message=None,
                )
            )
            model.status = NotificationStatus.PENDING.value
            await session.commit()
            return DeliveryPreparation(notification=notification, attempt=attempt)

    async def _prepare_b04_terminal(
        self,
        session: AsyncSession,
        *,
        model: NotificationModel,
        alert: AlertModel,
        trade: TradeModel | None,
        attempt_id: UUID,
        now: datetime,
    ) -> DeliveryPreparation | None:
        """Recheck B04 under the same trade lock used by execution writers.

        Position rows may lag effective execution corrections. Reuse the
        execution owner's projector, without a second quantity calculation.
        This is the existing pre-dispatch transaction boundary; an external
        request already in flight cannot be recalled by a later sale.
        """
        if model.status == NotificationStatus.DELIVERED.value:
            return DeliveryPreparation(
                notification=self._notification(model),
                terminal_result=DeliveryResult(status=DeliveryStatus.DELIVERED, retryable=False),
            )
        if model.status == NotificationStatus.FAILED.value:
            latest = await session.scalar(
                select(NotificationDeliveryAttemptModel)
                .where(NotificationDeliveryAttemptModel.notification_id == model.id)
                .order_by(NotificationDeliveryAttemptModel.attempt_number.desc())
                .limit(1)
            )
            return DeliveryPreparation(
                notification=self._notification(model),
                terminal_result=DeliveryResult(
                    status=DeliveryStatus.FAILED,
                    retryable=False,
                    error_code=(latest.error_code if latest is not None else "NOTIFICATION_FAILED"),
                    error_message=latest.error_message if latest is not None else None,
                ),
            )

        reason: str | None = None
        if alert.status != "OPEN":
            reason = f"B04_ALERT_{alert.status}"
        elif trade is None:
            reason = "B04_TRADE_MISSING"
        elif trade.cancelled_at is not None:
            reason = "B04_TRADE_CANCELLED"
        else:
            effective = await SqlAlchemyExecutionRecordRepository(session).list_effective_for_trade(
                trade.id
            )
            # Invalid/missing owner facts raise and leave the item pending;
            # they cannot be converted into an invented full sale or a send.
            position = PositionProjector.project(
                id=alert.position_id,
                trade=SqlAlchemyTradeRepository.to_domain(trade),
                executions=effective,
            )
            if position.open_quantity <= 0:
                reason = "B04_POSITION_CLOSED"
        if reason is None:
            return None

        result = await suppress_b04_notification(
            session,
            notification=model,
            now=now,
            reason=reason,
            attempt_id=attempt_id,
        )
        await session.commit()
        return DeliveryPreparation(notification=self._notification(model), terminal_result=result)

    async def complete(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        result: DeliveryResult,
        completed_at: datetime,
        max_attempts: int,
    ) -> None:
        if result.status is DeliveryStatus.IN_PROGRESS:
            raise ValueError("delivery result cannot remain in progress")
        async with self._database.session_context() as session:
            attempt = await session.scalar(
                select(NotificationDeliveryAttemptModel)
                .where(NotificationDeliveryAttemptModel.id == attempt_id)
                .with_for_update()
            )
            notification = await session.scalar(
                select(NotificationModel)
                .where(NotificationModel.id == notification_id)
                .with_for_update()
            )
            if attempt is None or attempt.notification_id != notification_id:
                raise LookupError("delivery attempt not found")
            if notification is None:
                raise LookupError("notification not found")
            if attempt.status != DeliveryStatus.IN_PROGRESS.value:
                return

            suppressed_b04 = None
            if notification.status == NotificationStatus.FAILED.value:
                suppressed_b04 = await session.scalar(
                    select(NotificationDeliveryAttemptModel.id)
                    .join(
                        NotificationModel,
                        NotificationModel.id == NotificationDeliveryAttemptModel.notification_id,
                    )
                    .join(AlertModel, AlertModel.id == NotificationModel.alert_id)
                    .where(
                        NotificationDeliveryAttemptModel.notification_id == notification_id,
                        NotificationDeliveryAttemptModel.attempt_number > attempt.attempt_number,
                        NotificationDeliveryAttemptModel.error_code.in_(B04_SUPPRESSION_CODES),
                        NotificationDeliveryAttemptModel.retryable.is_(False),
                        AlertModel.alert_type == AlertType.HEBELTRADER_B04_LOSS.value,
                    )
                    .limit(1)
                )

            attempt.status = result.status.value
            attempt.completed_at = completed_at
            attempt.retryable = result.retryable
            attempt.provider_message_id = result.provider_message_id
            attempt.error_code = result.error_code
            attempt.error_message = result.error_message
            if result.status is DeliveryStatus.DELIVERED:
                notification.status = NotificationStatus.DELIVERED.value
            elif suppressed_b04 is not None:
                # Preserve a real earlier in-flight result without resurrecting
                # its outbox item after a later B04 suppression decision.
                notification.status = NotificationStatus.FAILED.value
            elif not result.retryable or attempt.attempt_number >= max_attempts:
                notification.status = NotificationStatus.FAILED.value
            else:
                notification.status = NotificationStatus.PENDING.value
            await session.commit()

    @staticmethod
    def _notification(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            alert_id=model.alert_id,
            channel=NotificationChannel(model.channel),
            destination_key=model.destination_key,
            body=model.body,
            created_at=model.created_at,
            status=NotificationStatus(model.status),
        )
