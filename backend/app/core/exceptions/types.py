"""Framework-independent application exception types."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    """A machine-readable detail attached to an application error."""

    field: str | None
    message: str
    context: dict[str, Any] | None = None


class ApplicationError(Exception):
    """Base exception for errors intentionally exposed through the API."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: tuple[ErrorDetail, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
