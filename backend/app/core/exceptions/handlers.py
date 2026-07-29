"""FastAPI exception handlers with a consistent response contract."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions.types import ApplicationError

logger = logging.getLogger(__name__)


def _error_payload(
    *, code: str, message: str, details: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def application_error_handler(
    request: Request, exception: ApplicationError
) -> JSONResponse:
    logger.warning(
        "application_error",
        extra={
            "error_code": exception.code,
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return JSONResponse(
        status_code=exception.status_code,
        content=_error_payload(
            code=exception.code,
            message=exception.message,
            details=[
                {
                    "field": detail.field,
                    "message": detail.message,
                    "context": detail.context,
                }
                for detail in exception.details
            ],
        ),
    )


async def http_error_handler(request: Request, exception: StarletteHTTPException) -> JSONResponse:
    logger.info(
        "http_error",
        extra={
            "status_code": exception.status_code,
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    message = exception.detail if isinstance(exception.detail, str) else "HTTP request failed."
    return JSONResponse(
        status_code=exception.status_code,
        headers=exception.headers,
        content=_error_payload(
            code=f"HTTP_{exception.status_code}",
            message=message,
            details=[],
        ),
    )


async def validation_error_handler(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    logger.info(
        "request_validation_failed",
        extra={
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "context": error.get("ctx"),
        }
        for error in exception.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            code="REQUEST_VALIDATION_ERROR",
            message="The request is invalid.",
            details=details,
        ),
    )


async def unexpected_error_handler(request: Request, exception: Exception) -> JSONResponse:
    logger.exception(
        "unexpected_error",
        extra={
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            details=[],
        ),
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register all central exception handlers on the application."""

    application.add_exception_handler(ApplicationError, application_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, unexpected_error_handler)
