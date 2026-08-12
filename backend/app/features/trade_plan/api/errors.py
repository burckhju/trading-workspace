"""Translate FT-007 failures into the central REST error contract."""

from fastapi import status

from app.core.exceptions import ApplicationError


def translate_trade_plan_error(error: ValueError) -> ApplicationError:
    message = str(error)
    lowered = message.lower()
    if (
        "not found" in lowered
        or "does not exist" in lowered
        or "cannot be resolved" in lowered
    ):
        code = "TRADE_PLAN_NOT_FOUND"
        status_code = status.HTTP_404_NOT_FOUND
    elif any(
        marker in lowered
        for marker in (
            "only the latest",
            "requires an approved",
            "only draft",
            "only ready_for_review",
            "transition",
            "approval record",
            "multiple approved",
            "newer than",
        )
    ):
        code = "TRADE_PLAN_CONFLICT"
        status_code = status.HTTP_409_CONFLICT
    else:
        code = "TRADE_PLAN_VALIDATION_ERROR"
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    return ApplicationError(code=code, message=message, status_code=status_code)
