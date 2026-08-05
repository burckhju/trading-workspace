"""Business enum values fixed by the accepted FT-001 architecture."""

from enum import StrEnum


class UnderlyingType(StrEnum):
    STOCK = "STOCK"


class LifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class QualityStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPLETE = "COMPLETE"
    VERIFIED = "VERIFIED"


class DataOrigin(StrEnum):
    MANUAL = "MANUAL"


class AggregateType(StrEnum):
    UNDERLYING = "UNDERLYING"
    LISTING = "LISTING"
    PROVIDER_MAPPING = "PROVIDER_MAPPING"


class ActorType(StrEnum):
    SYSTEM_USER = "SYSTEM_USER"


class ChangeType(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"
    REACTIVATED = "REACTIVATED"
    PRIMARY_CHANGED = "PRIMARY_CHANGED"
    DELETED = "DELETED"
