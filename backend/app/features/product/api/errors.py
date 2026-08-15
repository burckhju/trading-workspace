"""Translate FT-004 service failures into the central API error contract."""

from fastapi import status

from app.core.exceptions import ApplicationError, ErrorDetail
from app.features.product.service.errors import (
    DuplicateWarrantIsin,
    DuplicateWarrantListing,
    DuplicateWarrantWkn,
    InactiveWarrantReference,
    WarrantConcurrentModification,
    WarrantNotFound,
    WarrantServiceError,
)


def translate_product_error(error: Exception) -> ApplicationError:
    if isinstance(error, WarrantNotFound):
        return ApplicationError(
            code=error.code, message=str(error), status_code=status.HTTP_404_NOT_FOUND
        )
    if isinstance(
        error,
        (
            WarrantConcurrentModification,
            DuplicateWarrantIsin,
            DuplicateWarrantWkn,
            DuplicateWarrantListing,
        ),
    ):
        return ApplicationError(
            code=error.code,
            message=str(error),
            status_code=status.HTTP_409_CONFLICT,
            details=((ErrorDetail(field=error.field, message=str(error)),) if error.field else ()),
        )
    if isinstance(error, (InactiveWarrantReference, WarrantServiceError)):
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
