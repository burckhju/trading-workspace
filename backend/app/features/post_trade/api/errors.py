"""Stable REST error translation for FT-011."""

from fastapi import status

from app.core.exceptions import ApplicationError
from app.features.post_trade.application.exit_review_service import (
    ExitReviewAlreadyFinalizedError,
    ExitReviewIncompleteError,
    ExitReviewNotFoundError,
    ExitReviewObservationIncompleteError,
    ExitReviewServiceError,
)
from app.features.post_trade.application.observation_service import (
    PostTradeContextNotFoundError,
    PostTradeListingResolutionError,
    PostTradeNotEligibleError,
    PostTradeObservationError,
    PostTradeObservationExistsError,
)


def translate_post_trade_error(error: Exception) -> ApplicationError:
    message = str(error)

    if isinstance(error, PostTradeObservationExistsError):
        return ApplicationError(
            code="POST_TRADE_OBSERVATION_ALREADY_EXISTS",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )

    if isinstance(error, PostTradeNotEligibleError):
        return ApplicationError(
            code="POST_TRADE_NOT_ELIGIBLE",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    if isinstance(error, PostTradeListingResolutionError):
        code = (
            "UNDERLYING_LISTING_AMBIGUOUS"
            if "multiple" in message.lower() or "ambiguous" in message.lower()
            else "UNDERLYING_LISTING_NOT_RESOLVABLE"
        )
        return ApplicationError(
            code=code,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    if isinstance(error, PostTradeContextNotFoundError):
        code = (
            "POST_TRADE_OBSERVATION_NOT_FOUND"
            if "observation" in message.lower()
            else "TRADE_NOT_FOUND"
        )
        return ApplicationError(
            code=code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(error, ExitReviewNotFoundError):
        code = (
            "EXIT_REVIEW_VERSION_NOT_FOUND"
            if "version" in message.lower()
            else "EXIT_REVIEW_NOT_FOUND"
        )
        return ApplicationError(
            code=code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(error, ExitReviewObservationIncompleteError):
        return ApplicationError(
            code="OBSERVATION_HORIZON_NOT_COMPLETE",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    if isinstance(error, ExitReviewIncompleteError):
        return ApplicationError(
            code="EXIT_REVIEW_INCOMPLETE",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    if isinstance(error, ExitReviewAlreadyFinalizedError):
        return ApplicationError(
            code="EXIT_REVIEW_NOT_EDITABLE",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )

    if isinstance(
        error,
        (PostTradeObservationError, ExitReviewServiceError),
    ):
        return ApplicationError(
            code=error.code,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    return ApplicationError(
        code="POST_TRADE_VALIDATION_ERROR",
        message=message,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
