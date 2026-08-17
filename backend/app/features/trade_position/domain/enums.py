"""Trade & Position domain enumerations."""

from enum import StrEnum


class TradeOrigin(StrEnum):
    WORKSPACE_SELECTION = "WORKSPACE_SELECTION"
    EXTERNAL = "EXTERNAL"


class ExecutionSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class TradeManagementEventType(StrEnum):
    STOP_CHANGED = "STOP_CHANGED"
    TARGET_CHANGED = "TARGET_CHANGED"
    THESIS_UPDATED = "THESIS_UPDATED"
    MANAGEMENT_NOTE = "MANAGEMENT_NOTE"
