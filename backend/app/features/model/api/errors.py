"""Translate FT-013 failures into the central REST error contract."""

from fastapi import status

from app.core.exceptions import ApplicationError


def translate_model_governance_error(error: ValueError) -> ApplicationError:
    message = str(error)
    lowered = message.lower()
    if "not found" in lowered:
        return ApplicationError(
            code="MODEL_GOVERNANCE_NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if any(
        marker in lowered
        for marker in (
            "already approved",
            "only validated",
            "only initial",
            "stale",
            "cannot create proposal",
            "cannot be revalidated",
            "base version must be approved",
        )
    ):
        return ApplicationError(
            code="MODEL_GOVERNANCE_CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )
    return ApplicationError(
        code="MODEL_GOVERNANCE_VALIDATION_ERROR",
        message=message,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
