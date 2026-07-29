"""Request correlation and access logging middleware."""

import logging
from time import perf_counter
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging.context import bind_request_id, reset_request_id

logger = logging.getLogger(__name__)
_REQUEST_ID_HEADER = b"x-request-id"


def _valid_request_id(raw_value: bytes | None) -> str:
    if raw_value is None:
        return str(uuid4())

    try:
        return str(UUID(raw_value.decode("ascii")))
    except (UnicodeDecodeError, ValueError):
        return str(uuid4())


class RequestContextMiddleware:
    """Attach a request ID and emit one structured access log per HTTP request."""

    def __init__(self, application: ASGIApp) -> None:
        self.application = application

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.application(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        request_id = _valid_request_id(headers.get(_REQUEST_ID_HEADER))
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = perf_counter()
        status_code = 500
        request_id_token = bind_request_id(request_id)

        async def send_with_context(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers.append((_REQUEST_ID_HEADER, request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.application(scope, receive, send_with_context)
        finally:
            try:
                logger.info(
                    "http_request_completed",
                    extra={
                        "request_id": request_id,
                        "method": scope["method"],
                        "path": scope["path"],
                        "status_code": status_code,
                        "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                    },
                )
            finally:
                reset_request_id(request_id_token)
