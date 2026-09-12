"""Intentional, actionable trade-capture conflicts (no broker operations)."""

from uuid import UUID

from app.core.exceptions.types import ApplicationError, ErrorDetail


class OpenTradeExists(ApplicationError):
    def __init__(self, trade_id: UUID) -> None:
        super().__init__(
            code="OPEN_TRADE_EXISTS",
            message=(
                "Für diesen Optionsschein besteht bereits ein offener Trade. Bitte einen "
                "Nachkauf beim bestehenden Trade erfassen."
            ),
            status_code=409,
            details=(
                ErrorDetail(
                    field="product_id",
                    message="Offener Trade vorhanden",
                    context={"existing_trade_id": str(trade_id)},
                ),
            ),
        )


def capture_conflict(code: str, message: str) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=409)
