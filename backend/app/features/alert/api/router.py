from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.features.alert.api.dependencies import get_alert_read_repository
from app.features.alert.api.dtos import (
    AlertResponse,
    DeliveryAttemptResponse,
    NotificationResponse,
)
from app.features.alert.persistence.read_repository import SqlAlchemyAlertReadRepository
from app.features.alert.service.read_models import AlertView

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _response(value: AlertView) -> AlertResponse:
    return AlertResponse(
        id=value.id,
        position_id=value.position_id,
        trade_id=value.trade_id,
        alert_type=value.alert_type,
        severity=value.severity,
        rule_key=value.rule_key,
        reason=value.reason,
        observed_value=value.observed_value,
        threshold_value=value.threshold_value,
        market_data_observed_at=value.market_data_observed_at,
        detected_at=value.detected_at,
        status=value.status,
        resolved_at=value.resolved_at,
        notifications=[
            NotificationResponse(
                id=notification.id,
                channel=notification.channel,
                destination_key=notification.destination_key,
                status=notification.status,
                created_at=notification.created_at,
                last_delivery=(
                    None
                    if notification.last_delivery is None
                    else DeliveryAttemptResponse(
                        status=notification.last_delivery.status,
                        attempted_at=notification.last_delivery.attempted_at,
                        completed_at=notification.last_delivery.completed_at,
                        retryable=notification.last_delivery.retryable,
                        error_code=notification.last_delivery.error_code,
                        error_message=notification.last_delivery.error_message,
                    )
                ),
            )
            for notification in value.notifications
        ],
    )


@router.get("/trades/{trade_id}", response_model=list[AlertResponse])
async def list_trade_alerts(
    trade_id: UUID,
    repository: Annotated[
        SqlAlchemyAlertReadRepository,
        Depends(get_alert_read_repository),
    ],
) -> list[AlertResponse]:
    """Return persisted alerts and channel-neutral delivery state for one trade."""

    return [_response(item) for item in await repository.list_for_trade(trade_id)]
