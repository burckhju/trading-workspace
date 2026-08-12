"""FT-007 TradePlan enumerations."""

from enum import StrEnum


class TradePlanOriginType(StrEnum):
    CANDIDATE_EVALUATION = "CANDIDATE_EVALUATION"
    MANUAL = "MANUAL"


class TradeDirection(StrEnum):
    LONG = "LONG"


class EntryType(StrEnum):
    PRICE = "PRICE"
    PRICE_RANGE = "PRICE_RANGE"
    TRIGGER = "TRIGGER"


class TradePlanStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    ABANDONED = "ABANDONED"
    SUPERSEDED = "SUPERSEDED"
