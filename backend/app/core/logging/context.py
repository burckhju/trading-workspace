"""Context-local values enrich structured application logs."""

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def bind_request_id(request_id: str) -> Token[str | None]:
    """Bind a request ID to the current asynchronous execution context."""

    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the request context to its previous state."""

    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the request ID bound to the current execution context."""

    return _request_id.get()
