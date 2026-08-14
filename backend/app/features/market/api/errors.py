"""Translation of FT-001 domain/service failures into the central API contract."""

from fastapi import status

from app.core.exceptions import ApplicationError, ErrorDetail
from app.features.market.domain.errors import (
    ConcurrentModification,
    DomainRuleViolation,
)
from app.features.market.service.errors import (
    ListingNotFound,
    ServiceError,
    TradingVenueNotFound,
    UnderlyingDeleteReferenced,
    UnderlyingNotFound,
)


def translate_market_error(error: Exception) -> ApplicationError:
    if isinstance(error, UnderlyingDeleteReferenced):
        details = tuple(
            ErrorDetail(
                field=None,
                message="Underlying is referenced.",
                context={
                    "reference_type": item.reference_type,
                    "object_id": str(item.object_id),
                },
            )
            for item in error.references
        )
        return ApplicationError(
            code=error.code,
            message=str(error),
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )
    if isinstance(error, (UnderlyingNotFound, ListingNotFound, TradingVenueNotFound)):
        return ApplicationError(
            code=error.code,
            message=str(error),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(error, ConcurrentModification):
        return ApplicationError(
            code=error.code,
            message=str(error),
            status_code=status.HTTP_409_CONFLICT,
            details=(ErrorDetail(field=error.field, message=str(error)),),
        )
    if isinstance(error, ServiceError):
        return ApplicationError(
            code=error.code,
            message=str(error),
            status_code=status.HTTP_409_CONFLICT,
            details=((ErrorDetail(field=error.field, message=str(error)),) if error.field else ()),
        )
    if isinstance(error, DomainRuleViolation):
        return ApplicationError(
            code=error.code,
            message=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=((ErrorDetail(field=error.field, message=str(error)),) if error.field else ()),
        )
    if isinstance(error, ValueError):
        return ApplicationError(
            code="REQUEST_VALIDATION_ERROR",
            message=str(error),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    raise error
