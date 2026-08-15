"""Stable FT-004 application-service errors."""


class WarrantServiceError(RuntimeError):
    code = "WARRANT_SERVICE_ERROR"

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class WarrantNotFound(WarrantServiceError):
    code = "WARRANT_NOT_FOUND"


class WarrantConcurrentModification(WarrantServiceError):
    code = "WARRANT_CONCURRENT_MODIFICATION"


class DuplicateWarrantIsin(WarrantServiceError):
    code = "WARRANT_DUPLICATE_ISIN"


class DuplicateWarrantWkn(WarrantServiceError):
    code = "WARRANT_DUPLICATE_WKN"


class DuplicateWarrantListing(WarrantServiceError):
    code = "WARRANT_LISTING_DUPLICATE"


class InactiveWarrantReference(WarrantServiceError):
    code = "WARRANT_REFERENCE_INACTIVE"
