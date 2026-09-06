"""Context-local values enrich structured application logs."""

from contextvars import ContextVar, Token
from dataclasses import dataclass

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_database_query_stats: ContextVar["DatabaseQueryStats | None"] = ContextVar(
    "database_query_stats", default=None
)


@dataclass(frozen=True, slots=True)
class DatabaseQueryStats:
    """Database work accumulated in one request execution context."""

    count: int = 0
    duration_ms: float = 0.0


def bind_request_id(request_id: str) -> Token[str | None]:
    """Bind a request ID to the current asynchronous execution context."""

    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the request context to its previous state."""

    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the request ID bound to the current execution context."""

    return _request_id.get()


def bind_database_query_stats() -> Token[DatabaseQueryStats | None]:
    """Start request-scoped accumulation of database query metrics."""

    return _database_query_stats.set(DatabaseQueryStats())


def record_database_query(duration_ms: float) -> None:
    """Record one completed database statement when request metrics are active."""

    current = _database_query_stats.get()
    if current is None:
        return
    _database_query_stats.set(
        DatabaseQueryStats(
            count=current.count + 1,
            duration_ms=current.duration_ms + duration_ms,
        )
    )


def get_database_query_stats() -> DatabaseQueryStats:
    """Return accumulated request database metrics, or an empty snapshot."""

    return _database_query_stats.get() or DatabaseQueryStats()


def reset_database_query_stats(token: Token[DatabaseQueryStats | None]) -> None:
    """Restore database query metric context to its previous state."""

    _database_query_stats.reset(token)
