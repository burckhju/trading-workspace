"""Stable REST error translation for FT-008."""

from fastapi import status

from app.core.exceptions import ApplicationError


def translate_product_selection_error(error: ValueError) -> ApplicationError:
    message = str(error)
    lowered = message.lower()
    if "not found" in lowered:
        return ApplicationError(
            code="PRODUCT_SELECTION_NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if (
        "requires an approved" in lowered
        or "does not belong" in lowered
        or "already has a user selection" in lowered
        or "requires an eligible" in lowered
    ):
        return ApplicationError(
            code="PRODUCT_SELECTION_CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )
    return ApplicationError(
        code="PRODUCT_SELECTION_VALIDATION_ERROR",
        message=message,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
