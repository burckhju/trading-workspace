"""Stable REST error translation for FT-012 Learning TradeLinks."""

from fastapi import status

from app.core.exceptions import ApplicationError
from app.features.learning.application.execute_as_trade_service import (
    ExecuteAsTradeError,
    ExecuteAsTradeErrorCode,
)
from app.features.learning.application.lesson_query_service import (
    LessonPageError,
)
from app.features.learning.application.lesson_review_service import (
    LessonReviewErrorCode,
    LessonReviewServiceError,
)
from app.features.learning.application.lesson_service import (
    LessonErrorCode,
    LessonServiceError,
)
from app.features.learning.application.lesson_suggestion_service import (
    LessonSuggestionErrorCode,
    LessonSuggestionServiceError,
)
from app.features.learning.application.trade_link_service import (
    TradeLinkErrorCode,
    TradeLinkServiceError,
)


def translate_trade_link_error(error: Exception) -> ApplicationError:
    if not isinstance(error, TradeLinkServiceError):
        return ApplicationError(
            code="TRADE_LINK_VALIDATION_ERROR",
            message=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    not_found = {
        TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
        TradeLinkErrorCode.TRADE_LINK_TARGET_NOT_FOUND,
    }
    conflict = {
        TradeLinkErrorCode.TRADE_LINK_ACTIVE_PAIR_ALREADY_EXISTS,
        TradeLinkErrorCode.TRADE_LINK_INVALID_TRANSITION,
        TradeLinkErrorCode.TRADE_LINK_SOURCE_NOT_CURRENT,
    }

    if error.code in not_found:
        http_status = status.HTTP_404_NOT_FOUND
    elif error.code in conflict:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT

    return ApplicationError(
        code=error.code.value,
        message=str(error),
        status_code=http_status,
    )


def translate_execute_as_trade_error(error: Exception) -> ApplicationError:
    if not isinstance(error, ExecuteAsTradeError):
        return ApplicationError(
            code="EXECUTE_AS_TRADE_VALIDATION_ERROR",
            message=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    conflict = {
        ExecuteAsTradeErrorCode.IDEMPOTENCY_KEY_REUSED,
        ExecuteAsTradeErrorCode.IDEMPOTENCY_IN_PROGRESS,
        ExecuteAsTradeErrorCode.IDEMPOTENCY_FAILED_FINAL,
    }
    not_found = {
        ExecuteAsTradeErrorCode.EXTERNAL_OBSERVATION_NOT_FOUND,
        ExecuteAsTradeErrorCode.EXTERNAL_OBSERVATION_SOURCE_NOT_FOUND,
    }
    if error.code in conflict:
        http_status = status.HTTP_409_CONFLICT
    elif error.code in not_found:
        http_status = status.HTTP_404_NOT_FOUND
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    return ApplicationError(
        code=error.code.value,
        message=str(error),
        status_code=http_status,
    )


class LearningEvidenceNotFoundError(Exception):
    pass


def translate_learning_evidence_error(error: Exception) -> ApplicationError:
    if isinstance(error, LearningEvidenceNotFoundError):
        return ApplicationError(
            code="LEARNING_EVIDENCE_NOT_FOUND",
            message=str(error),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    raise error


def translate_lesson_page_error(error: Exception) -> ApplicationError:
    if not isinstance(error, LessonPageError):
        raise error

    return ApplicationError(
        code=error.code.value,
        message=str(error),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def translate_lesson_error(error: Exception) -> ApplicationError:
    if not isinstance(error, LessonServiceError):
        raise error

    if error.code in {
        LessonErrorCode.LEARNING_EVIDENCE_NOT_FOUND,
        LessonErrorCode.LESSON_NOT_FOUND,
    }:
        http_status = status.HTTP_404_NOT_FOUND
    elif error.code is LessonErrorCode.CONCURRENT_MODIFICATION:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT

    return ApplicationError(
        code=error.code.value,
        message=str(error),
        status_code=http_status,
    )


def translate_lesson_review_error(error: Exception) -> ApplicationError:
    if not isinstance(error, LessonReviewServiceError):
        raise error

    if error.code in {
        LessonReviewErrorCode.LESSON_NOT_FOUND,
        LessonReviewErrorCode.REVIEW_SIGNAL_NOT_FOUND,
    }:
        http_status = status.HTTP_404_NOT_FOUND
    elif error.code in {
        LessonReviewErrorCode.REVIEW_SIGNAL_ALREADY_OPEN,
        LessonReviewErrorCode.REVIEW_SIGNAL_NOT_OPEN,
        LessonReviewErrorCode.CONCURRENT_MODIFICATION,
    }:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT

    return ApplicationError(
        code=error.code.value,
        message=str(error),
        status_code=http_status,
    )


def translate_lesson_suggestion_error(error: Exception) -> ApplicationError:
    if not isinstance(error, LessonSuggestionServiceError):
        raise error

    if error.code is LessonSuggestionErrorCode.LESSON_SUGGESTION_NOT_FOUND:
        http_status = status.HTTP_404_NOT_FOUND
    elif error.code is LessonSuggestionErrorCode.LESSON_SUGGESTION_ALREADY_DECIDED:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT

    return ApplicationError(
        code=error.code.value,
        message=str(error),
        status_code=http_status,
    )
