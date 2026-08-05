"""Stable domain errors for FT-001."""

from __future__ import annotations


class DomainRuleViolation(ValueError):
    code = "DOMAIN_RULE_VIOLATION"

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class InvalidIsin(DomainRuleViolation):
    code = "UNDERLYING_INVALID_ISIN"


class InvalidWkn(DomainRuleViolation):
    code = "UNDERLYING_INVALID_WKN"


class UnsupportedUnderlyingType(DomainRuleViolation):
    code = "UNDERLYING_TYPE_NOT_SUPPORTED"


class PrimaryListingRequired(DomainRuleViolation):
    code = "UNDERLYING_PRIMARY_LISTING_REQUIRED"


class MultiplePrimaryListings(DomainRuleViolation):
    code = "UNDERLYING_MULTIPLE_PRIMARY_LISTINGS"


class NotOperationallyComplete(DomainRuleViolation):
    code = "UNDERLYING_NOT_OPERATIONALLY_COMPLETE"


class ConcurrentModification(DomainRuleViolation):
    code = "UNDERLYING_CONCURRENT_MODIFICATION"
