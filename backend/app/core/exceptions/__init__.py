"""Central application exception handling."""

from app.core.exceptions.handlers import register_exception_handlers
from app.core.exceptions.types import ApplicationError, ErrorDetail

__all__ = ["ApplicationError", "ErrorDetail", "register_exception_handlers"]
