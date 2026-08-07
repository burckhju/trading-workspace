"""Translate FT-006 failures into the central API error contract."""

from fastapi import status

from app.core.exceptions import ApplicationError
from app.features.analysis.domain.errors import (
    AnalysisConflict,
    AnalysisDataUnavailable,
    AnalysisError,
    AnalysisExecutionFailed,
    AnalysisNotFound,
    InvalidAnalysisParameters,
)


def translate_analysis_error(error: AnalysisError) -> ApplicationError:
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    if isinstance(error, AnalysisNotFound):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, AnalysisConflict):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(error, AnalysisExecutionFailed):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif isinstance(error, (AnalysisDataUnavailable, InvalidAnalysisParameters)):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    return ApplicationError(
        code=error.code.upper(),
        message=str(error),
        status_code=status_code,
    )
